// Explicit transport fixtures, not model execution or live review persistence.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { transform } from 'esbuild';
import * as api from '../src/investigation-api.js';
import { buildEvidenceRequest, buildInvestigationInput, normalizeRunEnvelope, validRunId, startInvestigation, readInvestigation, saveInvestigationReview } from '../src/investigation-api.js';

const form = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-25', evidence_backend: 'zetaris' };
const claim = { text: 'EPS was 2.29.', metric: 'diluted_eps', expected_value_decimal: '2.29', unit: 'USD/shares', accounting_basis: 'GAAP', period_start: '2026-04-01', period_end: '2026-06-30', tolerance_decimal: '0' };
const id = 'd0dd714d-70dd-4d80-a654-6da5c614cd98';
const envelope = () => ({ schema_version: 'claimtrace.run.v1', run_id: id, report_digest: 'a'.repeat(64),
  report: { schema_version: 'claimtrace.investigation.v1', run_id: id, request: buildEvidenceRequest(form), original_claims: buildInvestigationInput(form, claim).claim_inputs,
    model_inference_performed: false, execution_mode: 'incomplete_no_live_model', human_review_status: 'required', status: 'partial', evidence: [], findings: [], trace: [{ state: 'challenge', decision: 'Actual returned decision.' }], calculations: [], citations: [], limitations: ['No live model.'], reviewed_memory: [], challenge_findings: [], rejected_evidence: [] }, review: { status: 'required', version: 0, history: [] } });
const response = data => ({ ok: true, json: async () => data });
const reviewed = () => ({ ...envelope(), review: { status: 'approved', version: 1, history: [{ version: 1, decision: 'approved', comment: 'Reviewed sources.', reviewer: 'local-human', reviewed_at: '2026-10-25T12:00:00Z' }] } });

test('real run client sends fixed existing typed human-assertion inputs only', async () => {
  let sent;
  const result = await startInvestigation({ ...form, runtime_token: 'excluded', sql: 'excluded' }, { ...claim, actor: 'excluded' }, async (url, options) => {
    sent = { url, options }; return response(envelope());
  });
  assert.equal(sent.url, '/api/investigation-runs');
  assert.equal(sent.options.method, 'POST');
  assert.deepEqual(JSON.parse(sent.options.body), buildInvestigationInput(form, claim));
  assert.equal(result.isControllerReport, true);
  assert.equal(result.trace[0].state, 'challenge');
  assert.equal(result.review.status, 'required');
});

test('validates report identity, version, scope and incomplete-agent metadata', () => {
  assert.equal(normalizeRunEnvelope(envelope()).run_id, id);
  for (const mutate of [d => d.run_id = '../bad', d => d.report.run_id = '00000000-0000-0000-0000-000000000000', d => d.report_digest = 'invented',
    d => d.schema_version = 'claimtrace.run.v2', d => d.report.model_inference_performed = true, d => delete d.report.trace,
    d => d.report.schema_version = 'claimtrace.dispatcher.v1', d => d.report.request.period = 'Q3']) {
    const data = envelope(); mutate(data);
    assert.throws(() => normalizeRunEnvelope(data, buildEvidenceRequest(form)));
  }
});

test('invalid saved IDs cannot become arbitrary request paths', async () => {
  for (const runId of ['../secrets', id + '/review', id.toUpperCase(), '?run=' + id, '', null]) {
    assert.equal(validRunId(runId), false);
    await assert.rejects(readInvestigation(runId, () => assert.fail('No request for invalid ID')));
  }
  let sent;
  await readInvestigation(id, async (url, options) => { sent = { url, options }; return response(envelope()); });
  assert.equal(sent.url, `/api/investigation-runs/${id}`);
  assert.equal(sent.options.method, 'GET');
  assert.equal(sent.options.body, undefined);
});

test('review is exact-digest/version bound and confirmed with saved-state GET', async () => {
  const calls = [];
  const original = normalizeRunEnvelope(envelope());
  const result = await saveInvestigationReview(original, 'approved', 'Reviewed sources.', async (url, options) => {
    calls.push({ url, options }); return response(reviewed());
  });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, `/api/investigation-runs/${id}/review`);
  assert.deepEqual(JSON.parse(calls[0].options.body), { report_digest: 'a'.repeat(64), expected_review_version: 0, decision: 'approved', comment: 'Reviewed sources.' });
  assert.equal(calls[1].options.method, 'GET');
  assert.equal(original.review.status, 'required');
  assert.equal(result.review.status, 'approved');
  assert.equal(result.review.version, 1);
});

test('stale/replayed review errors do not retry or fabricate an approval', async () => {
  let calls = 0;
  const original = normalizeRunEnvelope(envelope());
  await assert.rejects(saveInvestigationReview(original, 'approved', '', async () => {
    calls++; return { ok: false, status: 409, json: async () => ({ detail: { code: 'review_conflict', message: 'Reload saved review.' } }) };
  }), error => error.status === 409 && /Reload saved review/.test(error.message));
  assert.equal(calls, 1);
  assert.equal(original.review.status, 'required');
});

test('ambiguous review failure and changed readback never become displayed success', async () => {
  const original = normalizeRunEnvelope(envelope());
  await assert.rejects(saveInvestigationReview(original, 'approved', '', async () => { throw new Error('offline'); }), /backend is unavailable/);
  let calls = 0;
  await assert.rejects(saveInvestigationReview(original, 'approved', 'Reviewed sources.', async () => {
    calls++; return response(calls === 1 ? reviewed() : envelope());
  }), /could not be confirmed/);
  assert.equal(original.review.version, 0);
});

test('rejects inconsistent review histories and substituted analyst assertions', async () => {
  for (const review of [{ status: 'approved', version: 0, history: [] }, { status: 'required', version: 1, history: [] },
    { ...reviewed().review, history: [{ ...reviewed().review.history[0], reviewed_at: 'invalid' }] }]) {
    assert.throws(() => normalizeRunEnvelope({ ...envelope(), review }), /invalid saved review/);
  }
  const changed = envelope(); changed.report.original_claims[0].expected_value_decimal = '8';
  await assert.rejects(startInvestigation(form, claim, async () => response(changed)), /does not match/);
});

test('exact decimal-equivalent assertions tolerate backend text normalization', async () => {
  for (const expected of ['+2.29', '2.290', '2.29e0', ' 002.2900 ', '.229e1']) {
    const input = { ...claim, expected_value_decimal: expected, tolerance_decimal: '+0.000e4' };
    const saved = envelope();
    saved.report.original_claims[0].expected_value_decimal = '2.29';
    saved.report.original_claims[0].tolerance_decimal = '0';
    const result = await startInvestigation(form, input, async () => response(saved));
    assert.equal(result.original_claims[0].expected_value_decimal, '2.29');
  }
  const zeroClaim = { ...claim, expected_value_decimal: '-0.000e25', tolerance_decimal: '0' };
  const zero = envelope(); zero.report.original_claims[0].expected_value_decimal = '0';
  assert.equal((await startInvestigation(form, zeroClaim, async () => response(zero))).original_claims[0].expected_value_decimal, '0');
});

test('decimal comparison preserves arbitrary precision and rejects numeric substitutions', async () => {
  const original = '123456789012345678901234567890.1234';
  const changed = envelope(); changed.report.original_claims[0].expected_value_decimal = '123456789012345678901234567890.1235';
  await assert.rejects(startInvestigation(form, { ...claim, expected_value_decimal: original }, async () => response(changed)), /does not match/);
  const equivalent = envelope(); equivalent.report.original_claims[0].expected_value_decimal = '1.234567890123456789012345678901234e29';
  await startInvestigation(form, { ...claim, expected_value_decimal: original }, async () => response(equivalent));
  for (const value of ['NaN', 'Infinity', '', '2..29', '1e+', '0'.repeat(81)]) await assert.rejects(startInvestigation(form, { ...claim, expected_value_decimal: value }, () => assert.fail('Invalid decimal must fail before network')));
});

test('canonical CIK-matched issuer labels describe the facts while submitted labels remain auditable', async () => {
  const submitted = { ...form, name: 'Microsoft', ticker: 'MSFT' };
  const canonical = envelope(); canonical.report.request.company.name = 'Intuitive Surgical Inc';
  const result = await startInvestigation(submitted, claim, async () => response(canonical));
  assert.equal(result.company.name, 'Intuitive Surgical Inc');
  assert.equal(result.company.ticker, 'ISRG');
  assert.equal(result.submitted_request.company.name, 'Microsoft');
  assert.equal(result.submitted_request.company.ticker, 'MSFT');
});

test('malformed canonical issuer labels fail before React display', () => {
  for (const fields of [{ name: {} }, { ticker: {} }, { name: ' ' }, { name: 'a'.repeat(161) }, { ticker: '' }, { ticker: 'A'.repeat(13) }, { ticker: '<script>' }]) {
    const data = envelope(); Object.assign(data.report.request.company, fields);
    assert.throws(() => normalizeRunEnvelope(data, buildEvidenceRequest(form)), /different company/);
  }
});

test('actual record rendering keeps verdict and calculation values visible while nesting auxiliary objects', async () => {
  const source = await fs.readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
  const compiled = await transform(source.replace("import './styles.css';", '') + '\nexport { RecordList };', { loader: 'jsx', format: 'cjs' });
  const module = { exports: {} };
  vm.runInNewContext(compiled.code, { module, exports: module.exports, URL, document: { getElementById: () => ({}) }, require: name => {
    if (name === 'react') return React;
    if (name === 'react-dom/client') return { createRoot: () => ({ render() {} }) };
    if (name === './investigation-api.js') return api;
    throw new Error(`Unexpected dependency ${name}`);
  } });
  const records = [{ classification: 'contradicted', explanation: 'Comparable evidence differs.', checks: { units: false } },
    { tool: 'compare_value', actual_decimal: '2.29', expected_decimal: '8', difference_decimal: '-5.71', evidence_ids: ['source-1'] },
    { state: 'recheck', decision: 'Read the additional source.' }];
  const html = renderToStaticMarkup(React.createElement(module.exports.RecordList, { title: 'Returned findings', records }));
  assert.ok(html.includes('<strong>contradicted</strong><p>Comparable evidence differs.</p>'));
  assert.ok(html.includes('<details><summary>Details</summary>'));
  assert.ok(html.includes('units'));
  assert.ok(html.includes('<strong>compare value</strong><span class="record-detail">actual decimal: 2.29</span>'));
  assert.ok(html.includes('expected decimal: 8'));
  assert.ok(html.includes('difference decimal: -5.71'));
  assert.ok(html.includes('source-1'));
  assert.ok(html.includes('<strong>Retrieve additional evidence</strong>'));
  assert.ok(html.includes('state: recheck'));
});

test('evidence rendering preserves received exact numeric text beyond JavaScript precision', async () => {
  const source = await fs.readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
  const compiled = await transform(source.replace("import './styles.css';", '') + '\nexport { Evidence };', { loader: 'jsx', format: 'cjs' });
  const module = { exports: {} };
  vm.runInNewContext(compiled.code, { module, exports: module.exports, URL, document: { getElementById: () => ({}) }, require: name => {
    if (name === 'react') return React;
    if (name === 'react-dom/client') return { createRoot: () => ({ render() {} }) };
    if (name === './investigation-api.js') return api;
    throw new Error(`Unexpected dependency ${name}`);
  } });
  const exact = '9007199254740993.123456789012345678';
  const html = renderToStaticMarkup(React.createElement(module.exports.Evidence, { item: { metric: 'revenue', value: Number(exact), value_decimal: exact, unit: 'USD', published_at: '2026-07-21' } }));
  assert.ok(html.includes(exact + ' <small>USD</small>'));
  assert.ok(html.includes('Published 2026-07-21'));
  const legacy = renderToStaticMarkup(React.createElement(module.exports.Evidence, { item: { metric: 'diluted_eps', value: 2.29, unit: 'USD/shares' } }));
  assert.ok(legacy.includes('2.29 <small>USD/shares</small>'));
});
