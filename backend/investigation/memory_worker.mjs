// ClaimTrace bridge; upstream service files in vendor/hmem are unchanged.
import fs from 'node:fs';
import path from 'node:path';
import { MemoryStoreService } from './vendor/hmem/memoryStore.ts';
import { MemoryRetrievalService } from './vendor/hmem/memoryRetrieval.ts';
import { TrustLedgerService } from './vendor/hmem/trustLedger.ts';

// Upgrade reference state persistence to atomic replacement without modifying it.
const write = fs.writeFileSync.bind(fs);
fs.writeFileSync = function(file, data, options) {
  if (String(file).endsWith('state.json')) {
    const temp = `${file}.tmp`;
    write(temp, data, options);
    fs.renameSync(temp, file);
  } else write(file, data, options);
};
let lock;
let ownsLock = false;
try {
  const raw = fs.readFileSync(0, 'utf8');
  if (raw.length > 128000) throw new Error('input_limit');
  const input = JSON.parse(raw);
  const dir = input.directory;
  fs.mkdirSync(dir, {recursive:true});
  lock = path.join(dir, '.worker-lock');
  if (fs.existsSync(lock)) {
    const pid = Number(fs.readFileSync(path.join(lock,'pid'), 'utf8'));
    if (!Number.isSafeInteger(pid) || pid <= 0) throw new Error('invalid_lock');
    try { process.kill(pid,0); } catch (e) {
      if (e.code !== 'ESRCH') throw e;
      fs.unlinkSync(path.join(lock,'pid'));
      fs.rmdirSync(lock);
    }
  }
  fs.mkdirSync(lock); // exclusive across Python processes; fail closed if busy
  ownsLock = true;
  write(path.join(lock,'pid'),String(process.pid));
  const journalPath = path.join(dir, 'operations.json');
  const journal = fs.existsSync(journalPath) ? JSON.parse(fs.readFileSync(journalPath, 'utf8')) : {};
  const persistJournal = () => {
    write(`${journalPath}.tmp`, JSON.stringify(journal));
    fs.renameSync(`${journalPath}.tmp`, journalPath);
  };
  const clock = Date.now;
  const ledger = new TrustLedgerService(clock, dir);
  const store = new MemoryStoreService(clock, ledger, input.actor, dir);
  const retrieval = new MemoryRetrievalService(store, ledger, clock, input.actor);
  const finish = entry => {
    const p = entry.proposal;
    let rec = store.all().find(r => r.tags.includes(`approval:${p.digest}`));
    const prior = p.supersedes ? store.get(p.supersedes) : undefined;
    if (p.supersedes && !prior) throw new Error('unknown_supersedes');
    if (prior?.supersededBy && prior.supersededBy !== rec?.id) throw new Error('already_superseded');
    if (!rec) rec = store.add({content:p.text, source:p.sources[0].url,
      type:'factual', layer:'long_term', confidence:0.85, chatId:p.scope_key,
      tags:[`approval:${p.digest}`],
      provenance:{origin:'user_correction',learnedAt:Date.now(),label:'explicit_local_human_review',
        refs:p.sources.map(s => `${s.id}:${s.fingerprint}`)}, supersedes:p.supersedes || undefined});
    // Reference automatic supersedes detection is not an approval decision.
    // Explicitly restore only the lineage that this exact reviewed payload names.
    if ((rec.supersedes || null) !== p.supersedes) store.update(rec.id,{supersedes:p.supersedes || undefined});
    if (prior && prior.supersededBy !== rec.id) store.update(prior.id,{supersededBy:rec.id});
    entry.memory_id = rec.id;
    entry.done = true;
    persistJournal();
    return rec;
  };
  // Replay incomplete approvals before serving any read. A process killed after
  // add/before old.supersededBy cannot expose a half-corrected active memory.
  for (const entry of Object.values(journal)) if (!entry.done) finish(entry);
  let result;
  if (input.op === 'approve') {
    const p = input.proposal;
    const previous = journal[p.correction_id];
    if (previous && previous.proposal.digest !== p.digest) throw new Error('idempotency_conflict');
    if (!previous) {
      if (Object.keys(journal).length >= 100) throw new Error('memory_limit');
      if (p.supersedes && !store.get(p.supersedes)) throw new Error('unknown_supersedes');
      if (p.supersedes && store.get(p.supersedes).supersededBy) throw new Error('already_superseded');
      journal[p.correction_id] = {proposal:p, reviewed_at:new Date().toISOString(), done:false};
      persistJournal();
    }
    const record = finish(journal[p.correction_id]);
    result = {status:'approved', memory_id:record.id, digest:p.digest};
  } else if (input.op === 'recall') {
    const queried = retrieval.query(input.query,{topN:100,threshold:0,chatId:input.scope_key});
    store.persist();
    result = {memories:queried.memories.filter(r => !r.memory.supersededBy && !r.memory.tags.includes('review')).map(r => {
      const entry = Object.values(journal).find(e => e.memory_id === r.memory.id && e.done);
      return {memory_id:r.memory.id, content:r.memory.content, relevance:r.relevance,
        proposal:entry?.proposal, reviewed_at:entry?.reviewed_at, supersedes:r.memory.supersedes || null};
    }), trace:queried.trace};
  } else if (input.op === 'feedback') {
    if (!Object.values(journal).some(e => e.memory_id === input.memory_id && e.done)) throw new Error('unknown_memory');
    retrieval.feedback(input.memory_id,input.kind);
    result = {status:'feedback_recorded', memory_id:input.memory_id};
  } else throw new Error('unknown_operation');
  process.stdout.write(JSON.stringify({ok:true,result}));
} catch {
  process.stdout.write(JSON.stringify({ok:false,error:'hmem_operation_failed'}));
  process.exitCode = 1;
} finally {
  if (ownsLock) { try { fs.unlinkSync(path.join(lock,'pid')); fs.rmdirSync(lock); } catch {} }
}
