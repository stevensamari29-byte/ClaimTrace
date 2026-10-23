import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const initial = { name: 'Intuitive Surgical', ticker: 'ISRG', cik: '0001035267', fiscal_year: '2026', period: 'Q2', as_of: '2026-10-23', evidence_backend: 'sec' };
const label = (text) => String(text ?? '').replaceAll('_', ' ');
const readable = (value) => typeof value === 'object' ? JSON.stringify(value) : String(value ?? 'Not provided');
function SourceLink({ url, children }) {
  try { const parsed = new URL(url); if (parsed.protocol === 'https:' || parsed.protocol === 'http:') return <a href={parsed.href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>; } catch {}
  return <span>{children}</span>;
}

function App() {
  const [form, setForm] = useState(initial);
  const [result, setResult] = useState(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const update = (event) => setForm({ ...form, [event.target.name]: event.target.value });
  async function investigate(event) {
    event.preventDefault(); setPending(true); setError(''); setResult(null);
    try {
      const response = await fetch('/api/investigations', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company: { name: form.name, ticker: form.ticker, cik: form.cik }, fiscal_year: Number(form.fiscal_year), period: form.period, as_of: form.as_of, evidence_backend: form.evidence_backend }),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = data?.error?.message ?? data?.detail?.message ?? (typeof data?.detail === 'string' ? data.detail : null);
        throw new Error(detail || (response.status === 422 ? 'Check the company, period, and date. The request did not pass validation.' : `Evidence could not be retrieved (HTTP ${response.status}). Check the backend connection and try again.`));
      }
      if (!data || !Array.isArray(data.evidence)) throw new Error('The backend returned an unexpected response. Evidence could not be displayed.');
      setResult({ ...data, evidence_backend: data.evidence_backend ?? form.evidence_backend });
    } catch (failure) {
      setError(failure instanceof TypeError ? 'The backend is unavailable. Start the ClaimTrace API and try again.' : failure.message);
    } finally { setPending(false); }
  }
  const evidence = result?.evidence ?? [];
  return <>
    <header className="topbar"><a className="brand" href="/" aria-label="ClaimTrace home"><span className="brand-mark" aria-hidden="true">C<span>✓</span></span>ClaimTrace</a><span className="build-badge">FOUNDATION BUILD</span></header>
    <main>
      <section className="intro"><p className="eyebrow">EARNINGS BRIEF GATEKEEPER</p><h1>Every claim needs<br />a paper trail.</h1><p className="lede">Retrieve financial evidence, inspect its source, and surface what still needs a human review before a brief moves forward.</p><div className="scope"><span className="dot" />Evidence retrieval + deterministic checks <span className="scope-divider">/</span><strong>No AI inference yet</strong></div></section>
      <div className="workspace">
        <section className="request-panel" aria-labelledby="request-title"><div className="section-head"><span className="step">01</span><h2 id="request-title">Define the investigation</h2></div><p className="muted">Choose the company, reporting period, and information cutoff.</p>
          <form onSubmit={investigate}>
            <label>Company name<input name="name" value={form.name} onChange={update} required maxLength={160} /></label>
            <div className="form-row"><label>Ticker<input name="ticker" value={form.ticker} onChange={update} required maxLength={16} /></label><label>SEC CIK<input name="cik" value={form.cik} onChange={update} required pattern="[0-9]{1,10}" title="One to ten digits" inputMode="numeric" /></label></div>
            <div className="form-row"><label>Fiscal year<input name="fiscal_year" type="number" min="1990" max="2100" value={form.fiscal_year} onChange={update} required /></label><label>Period<select name="period" value={form.period} onChange={update}>{['Q1', 'Q2', 'Q3', 'Q4', 'FY'].map(period => <option key={period}>{period}</option>)}</select></label></div>
            <label>As-of date<input name="as_of" type="date" value={form.as_of} onChange={update} required /><span className="field-hint">Only evidence published on or before this date.</span></label>
            <label>Evidence connection<select name="evidence_backend" value={form.evidence_backend} onChange={update}><option value="sec">SEC · primary-source evidence</option><option value="zetaris">Zetaris · financial evidence SQL</option></select><span className="field-hint">Zetaris requires an approved cloud dataset and server configuration.</span></label>
            <button type="submit" disabled={pending}>{pending ? 'Retrieving evidence…' : 'Trace financial evidence'}<span aria-hidden="true">{pending ? '◌' : '→'}</span></button>
          </form>
        </section>
        <section className="results-panel" aria-labelledby="results-title" aria-busy={pending}>
          <div className="section-head"><span className="step">02</span><h2 id="results-title">Evidence & review</h2></div>
          <div aria-live="polite" className="result-announcement">{pending ? 'Retrieving source-backed financial evidence.' : result ? `${evidence.length} evidence records returned.` : ''}</div>
          {error && <div role="alert" className="error"><strong>Investigation unavailable</strong><p>{error}</p><span>No result has been substituted.</span></div>}
          {pending && <div className="empty"><span className="empty-icon loading" aria-hidden="true">◎</span><h3>Following the evidence</h3><p>Waiting for the backend to retrieve and check the source records.</p></div>}
          {!pending && !error && !result && <div className="empty"><span className="empty-icon" aria-hidden="true">⌕</span><h3>A clear trail starts here</h3><p>Run an investigation to see actual financial evidence, its publication date, and the source behind it.</p><div className="empty-details"><span>Primary sources</span><span>Explicit limitations</span><span>Human review</span></div></div>}
          {result && <>
            <div className="result-summary"><div><p className="eyebrow">{result.company?.ticker ?? form.ticker} · {result.period} {result.fiscal_year}</p><h3>{result.company?.name ?? form.name}</h3><p className="muted">Information cutoff · {result.as_of}</p></div><span className="source-badge">{label(result.evidence_backend ?? form.evidence_backend).toUpperCase()}</span></div>
            <div className="review-banner"><span className="dot amber" /><div><strong>{label(result.human_review_status ?? 'Human review required')}</strong><p>Investigation status: {label(result.status)}. A person must review the source evidence and unresolved items.</p></div></div>
            <div className="metrics"><div><strong>{evidence.length}</strong><span>Evidence records</span></div><div><strong>{result.calculations?.length ?? 0}</strong><span>Calculations</span></div><div><strong>{result.unresolved_questions?.length ?? 0}</strong><span>Open questions</span></div></div>
            <h3 className="subheading">Source-backed evidence</h3>
            {evidence.length === 0 && <p className="notice">No evidence matched this company, reporting period, and cutoff. No financial claim can be supported from this result.</p>}
            <div className="evidence-list">{evidence.map((item, index) => <Evidence key={item.id ?? index} item={item} />)}</div>
            <RecordList title="Deterministic calculations" records={result.calculations} />
            <RecordList title="Claims under review" records={result.claims} />
            <RecordList title="Findings" records={result.findings} />
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
  return <article className="evidence-card"><div className="evidence-top"><h4>{label(metric)}</h4><span className="value">{typeof item.value === 'number' ? item.value.toLocaleString('en-US', { maximumFractionDigits: 6 }) : readable(item.value)} <small>{item.unit ?? ''}</small></span></div><p className="evidence-period">{item.period ?? item.reporting_period ?? (item.period_start && item.period_end ? `${item.period_start} to ${item.period_end}` : '')}{item.fiscal_year ? ` · ${item.fiscal_year}` : ''}</p><div className="citation"><SourceLink url={url}>{item.document ?? item.source_title ?? source.title ?? 'Primary-source document'}</SourceLink><span>Published {item.publication_date ?? item.published_at ?? source.publication_date ?? 'date unavailable'}</span><span>{item.locator ?? item.document_locator ?? source.locator ?? 'Locator unavailable'}</span><span>Retrieval: {label(item.source_mode ?? 'not reported')}</span></div>{item.notes && <p className="muted">{readable(item.notes)}</p>}</article>;
}
function RecordList({ title, records, tone = '' }) {
  if (!records?.length) return null;
  return <section className={`record-section ${tone}`}><h3 className="subheading">{title}</h3><ul>{records.map((record, index) => <li key={record.id ?? index}>{typeof record === 'string' ? record : <><strong>{label(record.title ?? record.label ?? record.metric ?? record.claim ?? record.name ?? record.status ?? '')}</strong><p>{record.message ?? record.description ?? record.statement ?? record.explanation ?? record.reason ?? ''}</p>{Object.entries(record).filter(([key]) => !['id', 'title', 'label', 'metric', 'claim', 'name', 'message', 'description', 'statement', 'explanation', 'reason'].includes(key)).map(([key, value]) => <span className="record-detail" key={key}>{label(key)}: {readable(value)}</span>)}</>}</li>)}</ul></section>;
}
createRoot(document.getElementById('root')).render(<App />);
