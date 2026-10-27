// Independent actual-source UI tests. Explicit protocol fixtures are not live approval or inference.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import vm from 'node:vm';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { transform } from 'esbuild';
import * as api from '../src/investigation-api.js';
const form = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-25', evidence_backend: 'zetaris' };
const id = 'e19b71ae-924e-4829-bc6f-7f60b2dbbd9d';
const run = () => ({ schema_version: 'claimtrace.run.v1', run_id: id, report_digest: 'b'.repeat(64), report: {
  schema_version: 'claimtrace.investigation.v1', run_id: id, request: api.buildEvidenceRequest(form), execution_mode: 'incomplete_no_live_model', model_inference_performed: false, human_review_status: 'required', status: 'partial', evidence: [],
  original_claims: [{ id: 'claim', text: 'Human assertion: EPS was9.99.' }], findings: [{ claim_id: 'claim', classification: 'contradicted', explanation: 'Source EPS2.29 disagrees.' }], trace: [{ state: 'challenge', decision: 'Request additional SEC evidence.' }, { state: 'recheck', tool: 'retrieve_financial_evidence' }], citations: [], calculations: [], limitations: ['No model reasoning.'], reviewed_memory: [], challenge_findings: [], rejected_evidence: [] },
  review: { status: 'approved', version: 1, history: [{ version: 1, decision: 'approved', comment: '<script>fixture</script>', reviewer: 'local-human', reviewed_at: '2026-10-25T14:00:00Z' }] } });
const source = await fs.readFile(new URL('../src/main.jsx', import.meta.url), 'utf8');
const compiled = await transform(source.replace("import './styles.css';", '') + '\nexport { App };', { loader: 'jsx', format: 'cjs' });
function render(result, reviewPending = false, message = '') {
  const states = [form, result, false, '', undefined, reviewPending, '', message];
  const module = { exports: {} };
  vm.runInNewContext(compiled.code, { module, exports: module.exports, URL, document: { getElementById: () => ({}) }, require: name => {
    if (name === 'react') return { ...React, useState: () => [states.shift(), () => {}] };
    if (name === 'react-dom/client') return { createRoot: () => ({ render() {} }) };
    if (name === './investigation-api.js') return api;
    throw new Error('Unexpected UI dependency');
  } });
  return renderToStaticMarkup(React.createElement(module.exports.App));
}
test('server review status does not promote a contradicted claim or hide model limitations', () => {
  const html = render(api.normalizeRunEnvelope(run()));
  for (const text of ['Saved human review: approved', 'Review version 1', 'contradicted', 'Human assertion: EPS was9.99.', 'Request additional SEC evidence.', 'recheck', 'No live model inference is verified', 'report approval does not approve H-MEM corrections or certify financial accuracy.']) assert.ok(html.includes(text), text);
  assert.ok(html.includes(`href="?run=${id}"`));
  assert.ok(html.includes('&lt;script&gt;fixture&lt;/script&gt;'));
  assert.ok(!html.includes('<script>fixture</script>'));
});
test('review storage wait disables duplicate decisions and announces backend work', () => {
  const html = render(api.normalizeRunEnvelope(run()), true);
  for (const button of ['Approve report', 'Reject report', 'Reload saved review']) assert.match(html, new RegExp('<button[^>]*disabled=""[^>]*>' + button));
  assert.ok(html.includes('Checking backend review storage'));
});
test('unconfirmed decision retains last known saved review and recovery control', () => {
  const data = run(); data.review = { status: 'required', version: 0, history: [] };
  const html = render(api.normalizeRunEnvelope(data), false, 'The decision is not confirmed. Reload saved review.');
  assert.ok(html.includes('Saved human review: required'));
  assert.ok(!html.includes('Saved human review: approved'));
  assert.ok(html.includes('decision is not confirmed') && html.includes('Reload saved review'));
});
test('raw dispatcher diagnostics and substituted run identity cannot become final conclusions', () => {
  const data = run(); data.report.schema_version = 'claimtrace.dispatcher.v1'; data.report.diagnostic_findings = [{ classification: 'supported' }];
  assert.throws(() => api.normalizeRunEnvelope(data), /invalid or incompatible/);
  const replaced = run(); replaced.report.run_id = 'b7b75a49-1533-4ff7-8c60-dd9b07656f00';
  assert.throws(() => api.normalizeRunEnvelope(replaced), /invalid or incompatible/);
});

test('backend decimal normalization preserves exact submitted meaning without floating-point comparison', async () => {
  const base = { text: 'Human assertion for decimal compatibility.', metric: 'diluted_eps', expected_value_decimal: '2.29', unit: 'USD/shares', accounting_basis: 'GAAP', period_start: '2026-04-01', period_end: '2026-06-30', tolerance_decimal: '0' };
  for (const [submitted, returned] of [['+2.29', '2.29'], ['002.2900', '2.2900'], ['2.29e0', '2.29'], ['-.000', '-0.000'], ['1234567890123456789012345678901234', '1.234567890123456789012345678901234E+33']]) {
    const claim = { ...base, expected_value_decimal: submitted };
    const data = run(); data.review = { status: 'required', version: 0, history: [] };
    data.report.original_claims = api.buildInvestigationInput(form, claim).claim_inputs;
    data.report.original_claims[0].expected_value_decimal = returned;
    const result = await api.startInvestigation(form, claim, async () => ({ ok: true, json: async () => data }));
    assert.equal(result.original_claims[0].expected_value_decimal, returned);
  }
  const precise = { ...base, expected_value_decimal: '1234567890123456789012345678901234' };
  const wrong = run(); wrong.review = { status: 'required', version: 0, history: [] };
  wrong.report.original_claims = api.buildInvestigationInput(form, precise).claim_inputs;
  wrong.report.original_claims[0].expected_value_decimal = '1234567890123456789012345678901235';
  await assert.rejects(api.startInvestigation(form, precise, async () => ({ ok: true, json: async () => wrong })), /does not match/);
});
