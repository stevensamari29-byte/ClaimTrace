// Independent fixture/SSR tests of actual UI source. These are not live inference.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { transform } from 'esbuild';
import * as api from '../src/investigation-api.js';

const form = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-07-21', evidence_backend: 'zetaris' };
const request = api.buildEvidenceRequest(form);
const fact = { id: 'revenue', concept: 'Revenues', value: 2892300000, unit: 'USD', url: 'https://www.sec.gov/Archives/edgar/data/1035267/filing.htm', document: 'SEC 10-Q', published_at: '2026-07-21', period_start: '2026-04-01', period_end: '2026-06-30', locator: 'Revenue table', source_mode: 'live_zetaris' };
const response = () => ({ ...structuredClone(request), status: 'partial', evidence: [structuredClone(fact)], claims: [], calculations: [], findings: [], limitations: ['No model inference.'], unresolved_questions: ['Review evidence.'] });
const source = await fs.readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const compiled = await transform(source.replace("import './styles.css';", '') + '\nexport { App, Evidence, RecordList, CitationList };', { loader: 'jsx', format: 'cjs' });
function components(result = null, activeForm = form, pending = false) {
  const states = [activeForm, result, pending, ''];
  const module = { exports: {} };
  const react = { ...React, useState: () => [states.shift(), () => {}] };
  vm.runInNewContext(compiled.code, { module, exports: module.exports, URL, document: { getElementById: () => ({}) }, require: name => {
    if (name === 'react') return react;
    if (name === 'react-dom/client') return { createRoot: () => ({ render() {} }) };
    if (name === './investigation-api.js') return api;
    throw new Error(`Unexpected dependency ${name}`);
  } });
  return module.exports;
}
const render = (component, props = {}) => renderToStaticMarkup(React.createElement(component, props));

test('actual page renders foundation evidence with original dates and honest missing run/review interface', () => {
  const result = api.normalizeInvestigationResponse(response(), request);
  const html = render(components(result).App);
  for (const text of ['2,892,300,000', '2026-07-21', '2026-04-01 to 2026-06-30', 'Revenue table', 'live zetaris', 'Evidence-only result.', 'does not run the investigation controller', 'Review decisions cannot be saved', 'Human review required']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('Investigation activity - returned by backend'));
  assert.ok(!html.includes('Approve'));
  assert.ok(!html.includes('Reject'));
  assert.ok(html.includes('href="https://www.sec.gov/Archives/edgar/data/1035267/filing.htm"'));
});

test('actual components render controller claim text, findings, real returned events and citations as escaped text', () => {
  const data = { schema_version: 'claimtrace.investigation.v1', request, evidence: [fact], status: 'partial', execution_mode: 'incomplete_no_live_model', original_claims: [{ id: 'c', text: '<script>original human claim</script>', metric: 'revenue' }], findings: [{ claim_id: 'c', classification: 'contradicted', explanation: 'Actual numerical mismatch.', evidence_ids: ['revenue'] }], trace: [{ state: 'challenge', decision: 'Requested additional SEC evidence.', step: 4 }], calculations: [{ label: 'GAAP net margin', formula: 'income / revenue × 100', value: '28.285448', evidence_ids: ['revenue'] }], citations: [{ evidence_id: fact.id, ...fact }], challenge_findings: [{ claim_id: 'c', additional_evidence_needed: true }], limitations: ['Unverified semantics.'] };
  const html = render(components(api.normalizeInvestigationResponse(data, request)).App);
  for (const text of ['Claims under review', '&lt;script&gt;original human claim&lt;/script&gt;', 'Actual numerical mismatch.', 'Requested additional SEC evidence.', 'Investigation activity - returned by backend', '28.285448', 'Report citations', 'Published 2026-07-21', 'Unverified semantics.', 'No live model inference is verified']) assert.ok(html.includes(text), text);
  assert.ok(!html.includes('<script>'));
});

test('result identity stays at submitted scope when editable form changes', () => {
  const changed = { ...form, name: 'Microsoft', ticker: 'MSFT', period: 'Q3', as_of: '2026-10-24' };
  const html = render(components(api.normalizeInvestigationResponse(response(), request), changed).App);
  assert.ok(html.includes('ISRG · Q2 2026'));
  assert.ok(html.includes('Information cutoff · 2026-07-21'));
  assert.ok(!html.includes('MSFT · Q3'));
});

test('cutoff-blocked response never invents evidence, claims, trace or approval', () => {
  const data = { ...response(), evidence: [], status: 'blocked', calculations: [], claims: [], findings: [] };
  const html = render(components(api.normalizeInvestigationResponse(data, request)).App);
  assert.ok(html.includes('No evidence matched this company, reporting period, and cutoff.'));
  assert.ok(!html.includes('Claims under review'));
  assert.ok(!html.includes('Investigation activity - returned by backend'));
  assert.ok(!html.includes('Report citations'));
  assert.ok(html.includes('Human review required'));
});

test('unsafe protocols and credential-bearing URLs remain nonclickable; HTTPS does not itself imply source authenticity', () => {
  const { Evidence } = components();
  for (const url of ['javascript:alert(1)', 'data:text/html,secret', 'http://sec.gov/a', 'https://secret@www.sec.gov/a', '/relative', null]) {
    assert.equal(api.safeSourceUrl(url), null);
    assert.ok(!render(Evidence, { item: { ...fact, url } }).includes('<a '), String(url));
  }
  assert.equal(api.safeSourceUrl('https://issuer.example/earnings'), 'https://issuer.example/earnings');
});

test('rejects wrong response identity and malformed optional records before display', () => {
  for (const patch of [{ company: { ...request.company, cik: '0000789019' } }, { as_of: '2026-07-22' }, { period: 'Q3' }, { fiscal_year: '2026' }, { evidence_backend: 'sec' }]) assert.throws(() => api.normalizeInvestigationResponse({ ...response(), ...patch }, request));
  for (const key of ['trace', 'citations', 'original_claims', 'findings', 'reviewed_memory', 'limitations']) {
    for (const value of [{}, [null], [false], [[]]]) assert.throws(() => api.normalizeInvestigationResponse({ ...response(), [key]: value }, request), key);
  }
  assert.throws(() => api.normalizeInvestigationResponse({ schema_version: 'claimtrace.investigation.v1', evidence: [] }, request));
});

test('request preserves JSON scope and never sends review, SQL, commands or model settings', async () => {
  let sent;
  await api.requestEvidence({ ...form, sql: 'DROP', command: 'run', human_review_status: 'approved', runtime_token: 'do-not-send' }, async (url, options) => {
    sent = { url, ...options };
    return { ok: true, json: async () => response() };
  });
  assert.equal(sent.url, '/api/investigations');
  assert.equal(sent.method, 'POST');
  assert.deepEqual(JSON.parse(sent.body), request);
});

test('malformed JSON, validation, unavailable service and network failures produce errors, not fallback results', async () => {
  for (const fake of [async () => { throw new Error('offline'); }, async () => ({ ok: true, json: async () => null }), async () => ({ ok: false, status: 422, json: async () => ({ detail: [] }) }), async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Evidence unavailable' }) })]) await assert.rejects(api.requestEvidence(form, fake));
});

test('existing form remains labeled and keyboard-operable; pending state announces actual waiting and prevents duplicate submission', () => {
  const html = render(components(null, form, true).App);
  assert.ok(html.includes('<form>'));
  assert.ok(html.includes('<label>Company name<input'));
  assert.ok(html.includes('<label>Period<select'));
  assert.ok(html.includes('type="submit" disabled=""'));
  assert.ok(html.includes('aria-busy="true"'));
  assert.ok(html.includes('aria-live="polite"'));
  assert.ok(html.includes('Waiting for the backend to retrieve and check the source records.'));
  assert.ok(!html.includes('Thinking'));
});
