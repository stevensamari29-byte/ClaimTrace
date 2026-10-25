// Independent fake-clock transport tests. No service calls or model inference.
import test from 'node:test';
import assert from 'node:assert/strict';
import { EVIDENCE_REQUEST_TIMEOUT_MS, requestEvidence } from '../src/investigation-api.js';

const form = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-25', evidence_backend: 'zetaris' };
const result = () => ({ company: { name: form.name, ticker: form.ticker, cik: form.cik }, fiscal_year: 2026, period: 'Q2', as_of: form.as_of, evidence_backend: 'zetaris', evidence: [], status: 'blocked', human_review_status: 'required' });
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };

async function clockCase(run) {
  const oldSet = globalThis.setTimeout;
  const oldClear = globalThis.clearTimeout;
  const oldPerformance = Object.getOwnPropertyDescriptor(globalThis, 'performance');
  let now = 1000, id = 0;
  const jobs = new Map(), delays = [];
  globalThis.setTimeout = (callback, delay) => { const token = ++id; jobs.set(token, { callback, at: now + delay }); delays.push(delay); return token; };
  globalThis.clearTimeout = token => jobs.delete(token);
  Object.defineProperty(globalThis, 'performance', { configurable: true, value: { now: () => now } });
  const clock = { jobs, delays, advance(ms, fire = true) { now += ms; if (fire) for (const [token, job] of [...jobs]) if (job.at <= now) { jobs.delete(token); job.callback(); } } };
  try { await run(clock); }
  finally { globalThis.setTimeout = oldSet; globalThis.clearTimeout = oldClear; Object.defineProperty(globalThis, 'performance', oldPerformance); }
}

test('default bound is exactly135seconds and aborts a noncooperative stalled fetch without retry', async () => clockCase(async clock => {
  assert.equal(EVIDENCE_REQUEST_TIMEOUT_MS, 135000);
  let calls = 0, signal;
  const pending = requestEvidence(form, async (_url, options) => { calls++; signal = options.signal; return new Promise(() => {}); });
  await flush();
  assert.deepEqual(clock.delays, [135000]);
  assert.equal(signal.aborted, false);
  clock.advance(135000);
  await assert.rejects(pending, /wait expired/i);
  assert.equal(signal.aborted, true);
  assert.equal(calls, 1);
  assert.equal(clock.jobs.size, 0);
}));

test('body parsing shares the original deadline and cannot hang past it', async () => clockCase(async clock => {
  let signal, bodyCalls = 0;
  const pending = requestEvidence(form, async (_url, options) => { signal = options.signal; clock.advance(90000, false); return { ok: true, json: () => { bodyCalls++; return new Promise(() => {}); } }; });
  await flush();
  assert.equal(bodyCalls, 1);
  assert.deepEqual(clock.delays, [135000]);
  clock.advance(45000);
  await assert.rejects(pending, /wait expired/i);
  assert.equal(signal.aborted, true);
  assert.equal(clock.jobs.size, 0);
}));

test('late fetch completion is rejected even when the deadline timer callback was delayed', async () => clockCase(async clock => {
  const network = deferred();
  const pending = requestEvidence(form, () => network.promise);
  clock.advance(135001, false);
  network.resolve({ ok: true, json: async () => result() });
  await assert.rejects(pending, /wait expired/i);
  assert.equal(clock.jobs.size, 0);
}));

test('late body completion cannot become displayed output when its timer callback was delayed', async () => clockCase(async clock => {
  const body = deferred();
  const pending = requestEvidence(form, async () => ({ ok: true, json: () => body.promise }));
  await flush();
  clock.advance(135001, false);
  body.resolve(result());
  await assert.rejects(pending, /wait expired/i);
  assert.equal(clock.jobs.size, 0);
}));

test('aborting cooperative fetch preserves the timeout explanation rather than replacing it with connection failure', async () => clockCase(async clock => {
  const pending = requestEvidence(form, (_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')), { once: true })));
  clock.advance(135000);
  await assert.rejects(pending, error => /wait expired/i.test(error.message) && /server may still be processing/i.test(error.message) && !/backend is unavailable/i.test(error.message));
  assert.equal(clock.jobs.size, 0);
}));

test('late rejected or successful work after timeout cannot resolve the already failed request', async () => clockCase(async clock => {
  for (const outcome of ['resolve', 'reject']) {
    const body = deferred();
    let successes = 0;
    const pending = requestEvidence(form, async () => ({ ok: true, json: () => body.promise }));
    pending.then(() => successes++, () => {});
    await flush(); clock.advance(135000);
    await assert.rejects(pending, /wait expired/i);
    if (outcome === 'resolve') body.resolve(result()); else body.reject(new Error('late body failure'));
    await flush();
    assert.equal(successes, 0);
    assert.equal(clock.jobs.size, 0);
  }
}));

test('fast success retains genuine scope and clears its timer without aborting the completed request', async () => clockCase(async clock => {
  let signal;
  const data = await requestEvidence(form, async (_url, options) => { signal = options.signal; return { ok: true, json: async () => result() }; });
  assert.equal(data.as_of, form.as_of);
  assert.equal(data.human_review_status, 'required');
  assert.deepEqual(data.trace, []);
  assert.equal(signal.aborted, false);
  assert.equal(clock.jobs.size, 0);
  clock.advance(135001);
  assert.equal(signal.aborted, false);
}));

test('fast connection/HTTP/JSON/scope failures all release the deadline timer without retries', async () => clockCase(async clock => {
  for (const fake of [async () => { throw new Error('offline'); }, async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Evidence service unavailable' }) }), async () => ({ ok: true, json: async () => { throw new Error('malformed JSON'); } }), async () => ({ ok: true, json: async () => ({ ...result(), period: 'Q3' }) })]) {
    let calls = 0;
    await assert.rejects(requestEvidence(form, (...args) => { calls++; return fake(...args); }));
    assert.equal(calls, 1);
    assert.equal(clock.jobs.size, 0);
  }
}));

test('test deadline override cannot increase or invalidate the production wall bound', async () => clockCase(async clock => {
  let calls = 0;
  for (const timeoutMs of [0, -1, 135001, Infinity, NaN, '20', null, 1.5]) await assert.rejects(requestEvidence(form, async () => { calls++; }, { timeoutMs }));
  assert.equal(calls, 0);
  assert.equal(clock.jobs.size, 0);
}));
