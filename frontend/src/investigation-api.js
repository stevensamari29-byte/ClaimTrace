// This client uses the existing evidence route. Full runs and persisted review
// require an agreed server interface; a report-shaped response is never inference proof.
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
  if (!object(scope) || !object(scope.company) || String(scope.company.cik).padStart(10, '0') !== String(snapshot.company.cik).padStart(10, '0') || scope.period !== snapshot.period || scope.fiscal_year !== snapshot.fiscal_year || scope.as_of !== snapshot.as_of || (scope.evidence_backend != null && scope.evidence_backend !== snapshot.evidence_backend)) throw new Error('The backend returned a different company, period, cutoff, or evidence connection. The result was not displayed.');
  const arrays = ['calculations', 'claims', 'original_claims', 'findings', 'unresolved_questions', 'limitations', 'trace', 'citations', 'challenge_findings', 'rejected_evidence', 'reviewed_memory'];
  for (const key of arrays) {
    if (data[key] != null && (!Array.isArray(data[key]) || data[key].some(item => !object(item) && typeof item !== 'string'))) throw new Error(`The backend returned invalid ${key.replaceAll('_', ' ')}. The result was not displayed.`);
  }
  return { ...data, ...snapshot, submitted_request: snapshot, isControllerReport: data.schema_version === 'claimtrace.investigation.v1', ...Object.fromEntries(arrays.map(key => [key, data[key] ?? []])) };
}

export async function requestEvidence(form, fetchImpl = fetch) {
  const request = buildEvidenceRequest(form);
  let response;
  try { response = await fetchImpl('/api/investigations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) }); }
  catch { throw new Error('The backend is unavailable. Start the ClaimTrace API and try again.'); }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.error?.message ?? data?.detail?.message ?? (typeof data?.detail === 'string' ? data.detail : null);
    throw new Error(typeof detail === 'string' ? detail : (response.status === 422 ? 'Check the company, period, and date. The request did not pass validation.' : `Evidence could not be retrieved (HTTP ${response.status}). Check the backend connection and try again.`));
  }
  return normalizeInvestigationResponse(data, request);
}
