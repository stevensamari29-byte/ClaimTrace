import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import { startInvestigation, readInvestigation, saveInvestigationReview, validRunId, safeSourceUrl, formatRecord } from './investigation-api.js';

const initial = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-25', evidence_backend: 'sec' };
const initialClaim = { text: 'Diluted EPS was 2.29 USD per share.', metric: 'diluted_eps', expected_value_decimal: '2.29', unit: 'USD/shares', accounting_basis: 'GAAP', period_start: '2026-04-01', period_end: '2026-06-30', tolerance_decimal: '0' };
const emptyClaim = () => ({ ...initialClaim, text: '', expected_value_decimal: '', period_start: '', period_end: '' });
const label = (text) => String(text ?? '').replaceAll('_', ' ');
const readable = formatRecord;
function SourceLink({ url, children }) {
  const safeUrl = safeSourceUrl(url);
  if (safeUrl) return <a href={safeUrl} target="_blank" rel="noreferrer">{readable(children)} <span aria-hidden="true">&#8599;</span></a>;
  return <span>{readable(children)}</span>;
}

function App() {
  const [form, setForm] = useState(initial);
  const [result, setResult] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [claim, setClaim] = useState(initialClaim);
  const [reviewPending, setReviewPending] = useState(false);
  const [reviewNote, setReviewNote] = useState('');
  const [reviewMessage, setReviewMessage] = useState('');
  const activeClaim = claim ?? initialClaim;
  const update = (event) => {
    const { name, value } = event.target;
    setForm({ ...form, [name]: value });
    if (['name', 'ticker', 'cik', 'fiscal_year', 'period'].includes(name) && value !== form[name]) setClaim(emptyClaim());
  };
  const updateClaim = event => setClaim({ ...activeClaim, [event.target.name]: event.target.value });
  function showSaved(saved) {
    setResult(saved);
    const request = saved.submitted_request;
    setForm({ ...request.company, fiscal_year: String(request.fiscal_year), period: request.period, as_of: request.as_of, evidence_backend: request.evidence_backend });
    setClaim(emptyClaim());
  }
  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    if (!query.has('run')) return undefined;
    const runId = query.get('run');
    if (!validRunId(runId)) { setError('The saved investigation link has an invalid ID.'); return undefined; }
    let active = true;
    setPending(true);
    readInvestigation(runId).then(saved => { if (active) showSaved(saved); })
      .catch(failure => { if (active) setError(failure.message); }).finally(() => { if (active) setPending(false); });
    return () => { active = false; };
  }, []);
  async function investigate(event) {
    event.preventDefault(); setPending(true); setError(''); setResult(null); setReviewMessage(''); setReviewNote('');
    try {
      const saved = await startInvestigation(form, activeClaim);
      setResult(saved);
      window.history.replaceState(null, '', `?run=${saved.run_id}`);
    } catch (failure) {
      setError(failure instanceof TypeError ? 'The backend is unavailable. Start the ClaimTrace API and try again.' : failure.message);
    } finally { setPending(false); }
  }
  async function refreshReview() {
    setReviewPending(true); setReviewMessage('');
    try {
      const saved = await readInvestigation(result.run_id);
      if (saved.report_digest !== result.report_digest) throw new Error('The saved report changed unexpectedly. Reload this investigation.');
      setResult(saved); setReviewMessage('Saved review state reloaded from the backend.');
    } catch (failure) { setReviewMessage(failure.message); }
    finally { setReviewPending(false); }
  }
  async function review(decision) {
    setReviewPending(true); setReviewMessage('');
    try {
      const saved = await saveInvestigationReview(result, decision, reviewNote ?? '');
      setResult(saved); setReviewMessage(`Review ${decision} and confirmed from backend storage.`);
    } catch (failure) {
      setReviewMessage(`${failure.message} The decision is not confirmed on this page. Reload saved review before trying again.`);
      if (failure.status === 409) {
        try { setResult(await readInvestigation(result.run_id)); } catch { /* Keep the last known report; never invent a decision. */ }
      }
    } finally { setReviewPending(false); }
  }
  const evidence = result?.evidence ?? [];
  return <>
    <header className="topbar"><a className="brand" href="/" aria-label="ClaimTrace home"><span className="brand-mark" aria-hidden="true">C<span>✓</span></span>ClaimTrace</a><span className="build-badge">FOUNDATION BUILD</span></header>
    <main>
      <section className="intro"><p className="eyebrow">EARNINGS BRIEF GATEKEEPER</p><h1>Every claim needs<br />a paper trail.</h1><p className="lede">Retrieve financial evidence, inspect its source, and surface what still needs a human review before a brief moves forward.</p><div className="scope"><span className="dot" />Evidence retrieval + deterministic checks <span className="scope-divider">/</span><strong>No AI inference yet</strong></div></section>
      <div className="workspace">
        <section className="request-panel" aria-labelledby="request-title"><div className="section-head"><span className="step">01</span><h2 id="request-title">Define the investigation</h2></div><p className="muted">Choose the company, reporting period, cutoff and an analyst assertion. The deterministic controller retrieves evidence, verifies and challenges it. Live model reasoning is unavailable.</p>
          <form onSubmit={investigate}>
            <label>Company name<input name="name" value={form.name} onChange={update} required maxLength={160} /></label>
            <div className="form-row"><label>Ticker<input name="ticker" value={form.ticker} onChange={update} required maxLength={16} /></label><label>SEC CIK<input name="cik" value={form.cik} onChange={update} required pattern="[0-9]{1,10}" title="One to ten digits" inputMode="numeric" /></label></div>
            <div className="form-row"><label>Fiscal year<input name="fiscal_year" type="number" min="1990" max="2100" value={form.fiscal_year} onChange={update} required /></label><label>Period<select name="period" value={form.period} onChange={update}>{['Q1', 'Q2', 'Q3', 'Q4', 'FY'].map(period => <option key={period}>{period}</option>)}</select></label></div>
            <label>As-of date<input name="as_of" type="date" value={form.as_of} onChange={update} required /><span className="field-hint">Only evidence published on or before this date.</span></label>
            <label>Evidence connection<select name="evidence_backend" value={form.evidence_backend} onChange={update}><option value="sec">SEC · primary-source evidence</option><option value="zetaris">Zetaris · financial evidence SQL</option></select><span className="field-hint">Zetaris requires an approved cloud dataset and server configuration.</span></label>
            <label>Analyst assertion<input name="text" value={activeClaim.text} onChange={updateClaim} required maxLength={4000} /><span className="field-hint">Editable starting assertion, not an extracted issuer quote. Changing company or period clears its value and dates.</span></label>
            <div className="form-row"><label>Financial metric<select name="metric" value={activeClaim.metric} onChange={updateClaim}><option value="diluted_eps">Diluted EPS</option><option value="revenue">Revenue</option><option value="net_income">Net income</option><option value="net_margin">Net margin</option><option value="unsupported">Other / unsupported</option></select></label><label>Claimed value<input name="expected_value_decimal" value={activeClaim.expected_value_decimal} onChange={updateClaim} inputMode="decimal" required={activeClaim.metric !== 'unsupported'} disabled={activeClaim.metric === 'unsupported'} maxLength={80} /></label></div>
            <div className="form-row"><label>Units<input name="unit" value={activeClaim.unit} onChange={updateClaim} required maxLength={40} /></label><label>Accounting basis<select name="accounting_basis" value={activeClaim.accounting_basis} onChange={updateClaim}><option value="GAAP">GAAP</option><option value="non-GAAP">Non-GAAP</option><option value="unknown">Unknown</option></select></label></div>
            <div className="form-row"><label>Claim period start<input name="period_start" type="date" value={activeClaim.period_start} onChange={updateClaim} required /></label><label>Claim period end<input name="period_end" type="date" value={activeClaim.period_end} onChange={updateClaim} required min={activeClaim.period_start || undefined} /></label></div>
            <label>Declared tolerance<input name="tolerance_decimal" value={activeClaim.tolerance_decimal} onChange={updateClaim} inputMode="decimal" required maxLength={80} /><span className="field-hint">Absolute tolerance in the claimed units. The backend limits it; zero means exact comparison.</span></label>
            <button type="submit" disabled={pending || reviewPending}>{pending ? 'Investigating…' : 'Start investigation'}<span aria-hidden="true">{pending ? '◌' : '→'}</span></button>
          </form>
        </section>
        <section className="results-panel" aria-labelledby="results-title" aria-busy={pending}>
          <div className="section-head"><span className="step">02</span><h2 id="results-title">Evidence & review</h2></div>
          <div aria-live="polite" className="result-announcement">{pending ? 'Waiting for the backend investigation and saved report.' : result ? `${evidence.length} evidence records returned.` : ''}</div>
          {error && <div role="alert" className="error"><strong>Investigation unavailable</strong><p>{error}</p><span>No result has been substituted.</span></div>}
          {pending && <div className="empty"><span className="empty-icon loading" aria-hidden="true">◎</span><h3>Following the evidence</h3><p>Waiting for the backend to retrieve and check the source records.</p><p>Activity appears only when the actual controller report returns; no steps are simulated.</p></div>}
          {!pending && !error && !result && <div className="empty"><span className="empty-icon" aria-hidden="true">⌕</span><h3>A clear trail starts here</h3><p>Retrieve evidence to see actual financial evidence, its publication date, and the source behind it.</p><div className="empty-details"><span>Primary sources</span><span>Explicit limitations</span><span>Human review</span></div></div>}
          {result && <>
            <div className="result-summary"><div><p className="eyebrow">{result.company.ticker} · {result.period} {result.fiscal_year}</p><h3>{result.company.name}</h3><p className="muted">Information cutoff · {result.as_of}</p></div><span className="source-badge">{label(result.evidence_backend).toUpperCase()}</span></div>
            <div className="review-banner"><span className="dot amber" /><div><strong>{result.review ? `Saved human review: ${result.review.status}` : 'Human review required'}</strong><p>Investigation status: {label(result.status)}. A person must review the source evidence and unresolved items.</p>{!result.review && <p>Review decisions cannot be saved for this evidence-only result.</p>}</div></div>
            {result.review && <section className="record-section" aria-label="Human review"><p className="muted"><a href={`?run=${result.run_id}`}>Saved investigation link</a> · Review version {result.review.version}. Local trusted reviewer; report approval does not approve H-MEM corrections or certify financial accuracy.</p><label>Review note<input value={reviewNote ?? ''} onChange={event => setReviewNote(event.target.value)} maxLength={2000} disabled={reviewPending || pending} /></label><div className="form-row"><button type="button" disabled={reviewPending || pending} onClick={() => review('approved')}>Approve report</button><button type="button" disabled={reviewPending || pending} onClick={() => review('rejected')}>Reject report</button></div><button type="button" disabled={reviewPending || pending} onClick={refreshReview}>Reload saved review</button><p role="status" aria-live="polite">{reviewPending ? 'Checking backend review storage…' : reviewMessage}</p>{result.review.history.length > 0 && <details><summary>Saved review history</summary><RecordList title="Backend review decisions" records={result.review.history} /></details>}</section>}
            <p className="notice">{result.isControllerReport ? `Backend controller report - ${label(result.execution_mode)}. No live model inference is verified by this page.` : 'Evidence-only result. The current HTTP route does not run the investigation controller or return its activity trace. Nightshift/Nemotron remains unavailable.'}</p>
            <div className="metrics"><div><strong>{evidence.length}</strong><span>Evidence records</span></div><div><strong>{result.calculations?.length ?? 0}</strong><span>Calculations</span></div><div><strong>{result.unresolved_questions?.length ?? 0}</strong><span>Open questions</span></div></div>
            <RecordList title="Investigation activity - returned by backend" records={result.trace} />
            <h3 className="subheading">Source-backed evidence</h3>
            {evidence.length === 0 && <p className="notice">No evidence matched this company, reporting period, and cutoff. No financial claim can be supported from this result.</p>}
            <div className="evidence-list">{evidence.map((item, index) => <Evidence key={item.id ?? index} item={item} />)}</div>
            <RecordList title="Deterministic calculations" records={result.calculations} />
            <RecordList title="Claims under review" records={result.original_claims.length ? result.original_claims : result.claims} />
            <RecordList title="Findings" records={result.findings} />
            <RecordList title="Challenge checks" records={result.challenge_findings} />
            <CitationList records={result.citations} />
            <RecordList title="Rejected evidence" records={result.rejected_evidence} />
            <RecordList title="Reviewed memory - returned by backend" records={result.reviewed_memory} />
            <RecordList title="Unresolved questions" records={result.unresolved_questions} />
            <RecordList title="Limitations" records={result.limitations} tone="limitations" />
            {(result.integration_status || result.integrations) && <details className="integration-details"><summary>Integration status · reported by backend</summary><dl>{Object.entries(result.integration_status ?? result.integrations).map(([name, value]) => <React.Fragment key={name}><dt>{label(name)}</dt><dd>{readable(value)}</dd></React.Fragment>)}</dl></details>}
          </>}
        </section>
      </div>
      <footer>ClaimTrace <span>Evidence before confidence.</span><span>Foundation · Requires human review</span></footer>
    </main>
  </>;
}
function Evidence({ item }) {
  const source = item.source ?? {};
  const metric = item.metric ?? item.label ?? item.concept ?? item.name ?? 'Financial evidence';
  const url = item.source_url ?? item.url ?? source.url;
  return <article className="evidence-card"><div className="evidence-top"><h4>{label(metric)}</h4><span className="value">{item.value_decimal ?? (typeof item.value === 'number' ? item.value.toLocaleString('en-US', { maximumFractionDigits: 6 }) : readable(item.value))} <small>{readable(item.unit ?? '')}</small></span></div><p className="evidence-period">{readable(item.period ?? item.reporting_period ?? (item.period_start && item.period_end ? `${item.period_start} to ${item.period_end}` : ''))}{item.fiscal_year ? ` · ${item.fiscal_year}` : ''}</p><div className="citation"><SourceLink url={url}>{item.document ?? item.source_title ?? source.title ?? 'Primary-source document'}</SourceLink><span>Published {readable(item.publication_date ?? item.published_at ?? source.publication_date ?? 'date unavailable')}</span><span>{readable(item.locator ?? item.document_locator ?? source.locator ?? 'Locator unavailable')}</span><span>Retrieval: {label(item.source_mode ?? 'not reported')}</span></div>{item.notes && <p className="muted">{readable(item.notes)}</p>}</article>;
}
function CitationList({ records }) {
  if (!records.length) return null;
  return <section><h3 className="subheading">Report citations</h3><ul>{records.map((citation, index) => typeof citation === 'string' ? <li key={index}>{citation}</li> : <li className="citation" key={citation.evidence_id ?? index}><SourceLink url={citation.url}>{citation.document ?? citation.evidence_id ?? 'Source document'}</SourceLink><span>Published {readable(citation.published_at ?? 'date unavailable')}</span><span>{readable(citation.locator ?? 'Locator unavailable')}</span><span>Evidence ID: {readable(citation.evidence_id ?? 'not reported')}</span></li>)}</ul></section>;
}
function RecordList({ title, records, tone = '' }) {
  if (!records?.length) return null;
  const activityLabels = { validate: 'Check the analyst assertion', retrieve: 'Retrieve financial evidence', recall: 'Recall reviewed source-backed memory', verify: 'Verify the figures', challenge: 'Challenge the findings', recheck: 'Retrieve additional evidence', reverify: 'Recheck the figures', conclude: 'Return findings for human review' };
  return <section className={`record-section ${tone}`}><h3 className="subheading">{title}</h3><ul>{records.map((record, index) => {
    if (typeof record === 'string') return <li key={index}>{record}</li>;
    const titleKey = ['classification', 'title', 'label', 'metric', 'claim', 'name', 'state', 'status', 'tool'].find(key => record[key] != null);
    const textKey = ['message', 'text', 'description', 'statement', 'explanation', 'reason', 'decision'].find(key => record[key] != null);
    const heading = titleKey === 'state' ? activityLabels[record.state] ?? label(record.state) : label(record[titleKey]);
    const auxiliary = Object.entries(record).filter(([key]) => key !== textKey && (key !== titleKey || titleKey === 'state'));
    const nested = auxiliary.filter(([, value]) => value !== null && typeof value === 'object');
    const simple = auxiliary.filter(([, value]) => value === null || typeof value !== 'object');
    return <li key={record.id ?? index}><strong>{heading}</strong>{textKey && <p>{readable(record[textKey])}</p>}
      {simple.map(([key, value]) => <span className="record-detail" key={key}>{label(key)}: {readable(value)}</span>)}
      {nested.length > 0 && <details><summary>Details</summary>{nested.map(([key, value]) => <span className="record-detail" key={key}>{label(key)}: {readable(value)}</span>)}</details>}
    </li>;
  })}</ul></section>;
}
createRoot(document.getElementById('root')).render(<App />);
