import test from 'node:test';
import assert from 'node:assert/strict';
import { buildEvidenceRequest, normalizeInvestigationResponse, requestEvidence, safeSourceUrl } from '../src/investigation-api.js';

const form = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '1035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-23', evidence_backend: 'zetaris' };
const request = buildEvidenceRequest(form);
const evidenceResponse = () => ({ ...structuredClone(request), evidence: [{ id: 'sec-1', value: 1 }], limitations: ['No model inference.'], status: 'partial' });

test('uses only the existing route and immutable submitted scope', async () => {
  let sent;
  const pendingForm = { ...form };
  const result = await requestEvidence(pendingForm, async (url, options) => {
    sent = { url, options };
    pendingForm.ticker = 'MSFT'; pendingForm.period = 'Q3';
    return { ok: true, json: async () => evidenceResponse() };
  });
  assert.equal(sent.url, '/api/investigations');
  assert.deepEqual(JSON.parse(sent.options.body), request);
  assert.equal(result.company.ticker, 'ISRG');
  assert.equal(result.period, 'Q2');
  assert.equal(result.isControllerReport, false);
  assert.deepEqual(result.trace, []);
});

test('retains actual controller activity, original assertions and provenance', () => {
  const source = { evidence_id: 'sec-1', url: 'https://www.sec.gov/Archives/a', published_at: '2026-07-21', locator: 'Revenue' };
  const data = { schema_version: 'claimtrace.investigation.v1', request, evidence: [], execution_mode: 'incomplete_no_live_model', trace: [{ state: 'retrieve', tool_calls: 1 }], original_claims: [{ text: 'Human assertion' }], citations: [source] };
  const result = normalizeInvestigationResponse(data, request);
  assert.equal(result.isControllerReport, true);
  assert.deepEqual(result.trace, data.trace);
  assert.deepEqual(result.citations, [source]);
  assert.deepEqual(result.original_claims, data.original_claims);
  assert.equal(result.model_inference_performed, undefined);
});

test('rejects wrong result scope rather than relabeling another investigation', () => {
  for (const patch of [{ period: 'Q3' }, { as_of: '2026-10-24' }, { fiscal_year: 2025 }, { evidence_backend: 'sec' }, { company: { ...request.company, cik: '789019' } }]) {
    assert.throws(() => normalizeInvestigationResponse({ ...evidenceResponse(), ...patch }, request), /different company/);
  }
});

test('rejects malformed arrays and null records', () => {
  for (const data of [null, {}, { ...evidenceResponse(), evidence: [null] }, { ...evidenceResponse(), trace: {} }, { ...evidenceResponse(), findings: [null] }]) {
    assert.throws(() => normalizeInvestigationResponse(data, request), /unexpected|invalid/);
  }
});

test('permits primary-source HTTPS links and rejects unsafe link schemes or credentials', () => {
  assert.equal(safeSourceUrl('https://data.sec.gov/api/x'), 'https://data.sec.gov/api/x');
  assert.equal(safeSourceUrl('https://isrg.gcs-web.com/news-releases'), 'https://isrg.gcs-web.com/news-releases');
  for (const url of ['javascript:alert(1)', 'http://www.sec.gov/a', 'https://name:password@sec.gov/a', 'data:text/html,unsafe', null]) assert.equal(safeSourceUrl(url), null);
});

test('returns explicit provider/network/validation errors without substituted results', async () => {
  await assert.rejects(requestEvidence(form, async () => { throw new TypeError('offline'); }), /backend is unavailable/);
  await assert.rejects(requestEvidence(form, async () => ({ ok: false, status: 422, json: async () => ({ detail: [] }) })), /did not pass validation/);
  await assert.rejects(requestEvidence(form, async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Provider unavailable' }) })), /Provider unavailable/);
  await assert.rejects(requestEvidence(form, async () => ({ ok: true, json: async () => { throw new Error('not JSON'); } })), /unexpected response/);
});
