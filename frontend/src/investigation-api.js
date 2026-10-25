// Fixed local evidence/run/review routes. A controller report is not inference proof.
const object = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
export const formatRecord = (value) => object(value) || Array.isArray(value) ? JSON.stringify(value) : String(value ?? 'Not provided');

export function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    // Link safety is separate from source authenticity, which the backend checks.
    return url.protocol === 'https:' && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function buildEvidenceRequest(form) {
  return { company: { name: form.name, ticker: form.ticker, cik: form.cik }, fiscal_year: Number(form.fiscal_year), period: form.period, as_of: form.as_of, evidence_backend: form.evidence_backend };
}

export function normalizeInvestigationResponse(data, request) {
  if (!object(data) || !Array.isArray(data.evidence) || data.evidence.some(item => !object(item))) throw new Error('The backend returned an unexpected response. Evidence could not be displayed.');
  const snapshot = JSON.parse(JSON.stringify(request));
  const scope = data.request ?? data;
  if (!object(scope) || !object(scope.company) || typeof scope.company.name !== 'string' || !scope.company.name.trim() || scope.company.name.length > 160 || typeof scope.company.ticker !== 'string' || !/^[A-Za-z0-9.\-]{1,12}$/.test(scope.company.ticker) || String(scope.company.cik).padStart(10, '0') !== String(snapshot.company.cik).padStart(10, '0') || scope.period !== snapshot.period || scope.fiscal_year !== snapshot.fiscal_year || scope.as_of !== snapshot.as_of || (scope.evidence_backend != null && scope.evidence_backend !== snapshot.evidence_backend)) throw new Error('The backend returned a different company, period, cutoff, or evidence connection. The result was not displayed.');
  const arrays = ['calculations', 'claims', 'original_claims', 'findings', 'unresolved_questions', 'limitations', 'trace', 'citations', 'challenge_findings', 'rejected_evidence', 'reviewed_memory'];
  for (const key of arrays) {
    if (data[key] != null && (!Array.isArray(data[key]) || data[key].some(item => !object(item) && typeof item !== 'string'))) throw new Error(`The backend returned invalid ${key.replaceAll('_', ' ')}. The result was not displayed.`);
  }
  // The reader's canonical name/ticker describe the CIK-matched issuer. Preserve
  // the analyst's submitted labels separately; never relabel source facts with them.
  return { ...data, ...snapshot, company: structuredClone(scope.company), submitted_request: snapshot, isControllerReport: data.schema_version === 'claimtrace.investigation.v1', ...Object.fromEntries(arrays.map(key => [key, data[key] ?? []])) };
}

export const EVIDENCE_REQUEST_TIMEOUT_MS = 135_000;

async function requestJson(path, method, body, fetchImpl = fetch, { timeoutMs = EVIDENCE_REQUEST_TIMEOUT_MS } = {}) {
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > EVIDENCE_REQUEST_TIMEOUT_MS) throw new Error('The browser request timeout must be between 1 and 135000 milliseconds.');
  const controller = new AbortController();
  const deadline = performance.now() + timeoutMs;
  const timeoutError = new Error('The browser wait expired before the server response completed. The server may still be processing; this does not confirm that it stopped. No result has been substituted.');
  let timer;
  function checkDeadline() {
    if (performance.now() >= deadline) { controller.abort(); throw timeoutError; }
  }
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => { reject(timeoutError); controller.abort(); }, timeoutMs);
  });
  async function retrieve() {
    let response;
    try { response = await fetchImpl(path, { method, ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }), signal: controller.signal }); }
    catch { checkDeadline(); throw new Error('The backend is unavailable. Start the ClaimTrace API and try again.'); }
    checkDeadline();
    const data = await response.json().catch(() => null);
    checkDeadline();
    if (!response.ok) {
      const detail = data?.error?.message ?? data?.detail?.message ?? (typeof data?.detail === 'string' ? data.detail : null);
      const error = new Error(typeof detail === 'string' ? detail : (response.status === 422 ? 'Check the company, period, and date. The request did not pass validation.' : `The request could not be completed (HTTP ${response.status}). Check the backend connection and try again.`));
      error.status = response.status;
      throw error;
    }
    return data;
  }
  // Racing the complete operation bounds browser waiting even if a transport
  // ignores abort. Late completions cannot replace this promise's rejection.
  try { return await Promise.race([timeout, retrieve()]); }
  finally { clearTimeout(timer); }
}

export async function requestEvidence(form, fetchImpl = fetch, options) {
  const request = buildEvidenceRequest(form);
  return normalizeInvestigationResponse(await requestJson('/api/investigations', 'POST', request, fetchImpl, options), request);
}

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export function validRunId(value) { return typeof value === 'string' && uuidPattern.test(value); }

export function buildInvestigationInput(form, claim) {
  if (claim.metric !== 'unsupported') canonicalDecimal(claim.expected_value_decimal);
  canonicalDecimal(claim.tolerance_decimal || '0');
  return { request: buildEvidenceRequest(form), claim_inputs: [{ id: 'analyst-claim-1', text: claim.text, metric: claim.metric,
    expected_value_decimal: claim.metric === 'unsupported' ? null : claim.expected_value_decimal,
    unit: claim.unit, accounting_basis: claim.accounting_basis, period_start: claim.period_start,
    period_end: claim.period_end, tolerance_decimal: claim.tolerance_decimal || '0', input_kind: 'human_assertion' }] };
}

// Exact decimal identity, not a financial calculation or recovery of source
// precision. Bounded text and BigInt exponents avoid Number rounding.
function canonicalDecimal(value) {
  if (typeof value !== 'string' || value.length > 80) throw new Error('Use a decimal string of at most 80 characters for the claim value and tolerance.');
  const match = /^([+-]?)(?:(\d+)(?:\.(\d*))?|\.(\d+))(?:[eE]([+-]?\d+))?$/.exec(value.trim());
  if (!match) throw new Error('Use a finite decimal value, optionally with a sign or exponent.');
  const fraction = match[3] ?? match[4] ?? '';
  const digits = `${match[2] ?? ''}${fraction}`.replace(/^0+/, '');
  if (!digits) return '0';
  const trailing = digits.match(/0+$/)?.[0].length ?? 0;
  const coefficient = trailing ? digits.slice(0, -trailing) : digits;
  const exponent = BigInt(match[5] ?? '0') - BigInt(fraction.length) + BigInt(trailing);
  return `${match[1] === '-' ? '-' : ''}${coefficient}e${exponent}`;
}

function matchingClaim(submitted, returned) {
  if (!object(returned)) return false;
  return Object.entries(submitted).every(([key, value]) => {
    if (!['expected_value_decimal', 'tolerance_decimal'].includes(key)) return returned[key] === value;
    if (value === null || returned[key] === null) return returned[key] === value;
    try { return canonicalDecimal(value) === canonicalDecimal(returned[key]); } catch { return false; }
  });
}

export function normalizeRunEnvelope(data, request = null, expectedRunId = null) {
  if (!object(data) || data.schema_version !== 'claimtrace.run.v1' || !validRunId(data.run_id) ||
      (expectedRunId !== null && data.run_id !== expectedRunId) || !/^[0-9a-f]{64}$/.test(data.report_digest ?? '') ||
      !object(data.report) || data.report.schema_version !== 'claimtrace.investigation.v1' || data.report.run_id !== data.run_id ||
      !object(data.report.request) || data.report.model_inference_performed !== false ||
      data.report.execution_mode !== 'incomplete_no_live_model' || data.report.human_review_status !== 'required' ||
      !['partial', 'blocked'].includes(data.report.status) ||
      ['original_claims', 'findings', 'trace', 'calculations', 'citations', 'limitations', 'reviewed_memory', 'challenge_findings', 'rejected_evidence'].some(key => !Array.isArray(data.report[key]))) {
    throw new Error('The backend returned an invalid or incompatible saved investigation. No report was substituted.');
  }
  const review = data.review;
  if (!object(review) || !['required', 'approved', 'rejected'].includes(review.status) || !Number.isSafeInteger(review.version) ||
      review.version < 0 || !Array.isArray(review.history) || review.history.length !== review.version ||
      review.history.some((entry, index) => !object(entry) || entry.version !== index + 1 || !['approved', 'rejected'].includes(entry.decision) ||
        typeof entry.comment !== 'string' || typeof entry.reviewer !== 'string' || !entry.reviewer || typeof entry.reviewed_at !== 'string' || !Number.isFinite(Date.parse(entry.reviewed_at))) ||
      review.status !== (review.history.at(-1)?.decision ?? 'required')) {
    throw new Error('The backend returned an invalid saved review. Reload the investigation before reviewing.');
  }
  return { ...normalizeInvestigationResponse(data.report, request ?? data.report.request), run_id: data.run_id,
    report_digest: data.report_digest, review: structuredClone(review), envelope_schema_version: data.schema_version };
}

export async function startInvestigation(form, claim, fetchImpl = fetch, options) {
  const input = buildInvestigationInput(form, claim);
  const data = await requestJson('/api/investigation-runs', 'POST', input, fetchImpl, options);
  const result = normalizeRunEnvelope(data, input.request);
  if (result.original_claims.length !== 1 || !matchingClaim(input.claim_inputs[0], result.original_claims[0])) throw new Error('The saved investigation does not match the submitted analyst assertion.');
  return result;
}

export async function readInvestigation(runId, fetchImpl = fetch, options) {
  if (!validRunId(runId)) throw new Error('Use a valid saved investigation ID.');
  return normalizeRunEnvelope(await requestJson(`/api/investigation-runs/${runId}`, 'GET', undefined, fetchImpl, options), null, runId);
}

export async function saveInvestigationReview(result, decision, comment = '', fetchImpl = fetch, options) {
  if (!validRunId(result?.run_id) || !/^[0-9a-f]{64}$/.test(result.report_digest ?? '') || !Number.isSafeInteger(result.review?.version) ||
      !['approved', 'rejected'].includes(decision) || typeof comment !== 'string' || comment.length > 2000) throw new Error('Reload the saved investigation before reviewing.');
  const updated = normalizeRunEnvelope(await requestJson(`/api/investigation-runs/${result.run_id}/review`, 'POST', {
    report_digest: result.report_digest, expected_review_version: result.review.version, decision, comment,
  }, fetchImpl, options), result.submitted_request, result.run_id);
  const persisted = await readInvestigation(result.run_id, fetchImpl, options);
  if (updated.report_digest !== result.report_digest || persisted.report_digest !== result.report_digest ||
      updated.review.version !== result.review.version + 1 || updated.review.status !== decision ||
      persisted.review.version !== updated.review.version || JSON.stringify(persisted.review) !== JSON.stringify(updated.review)) {
    throw new Error('The saved review could not be confirmed or changed while being checked. Reload the saved review; no approval has been assumed.');
  }
  return persisted;
}
