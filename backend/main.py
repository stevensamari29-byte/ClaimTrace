from fastapi import FastAPI, HTTPException
from .models import InvestigationRequest, InvestigationResponse, Calculation
from .sources import SourceError, sec_evidence
from .zetaris import zetaris_evidence

app = FastAPI(title='ClaimTrace', version='0.1.0')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'application': 'claimtrace', 'inference_enabled': False}


@app.post('/api/investigations', response_model=InvestigationResponse)
def investigate(request: InvestigationRequest):
    limitations = ['Deterministic evidence foundation; no model inference or autonomous investigation has run.',
                    'Source publication dates are day-level. Human review is required.',
                    'Live SEC selection verifies report dates against recent submissions; older unindexed filings may be unavailable.',
                    'No non-GAAP normalization, guidance analysis, or independent issuer corroboration is implemented.']
    integrations = {'sec': 'not_requested', 'zetaris': 'not_requested', 'nightshift': 'not_connected', 'hmem': 'interface_only'}
    try:
        if request.evidence_backend == 'zetaris':
            evidence = zetaris_evidence(request)
        else:
            evidence = sec_evidence(request)
    except SourceError as error:
        if request.evidence_backend == 'sec':
            raise HTTPException(503, str(error)) from None
        evidence = []
        limitations.append(str(error))
    integrations[request.evidence_backend] = ('live_queries' if request.evidence_backend == 'zetaris' else evidence[0].source_mode) if evidence else 'no_eligible_evidence'
    if any(e.source_mode == 'cached_sec' for e in evidence):
        limitations.append('Authentic checked-in SEC snapshot, retrieved 2026-10-23; this response did not make a live SEC or Zetaris request.')
    calculations = []
    by_concept = {e.concept: e for e in evidence}
    revenue = by_concept.get('RevenueFromContractWithCustomerExcludingAssessedTax') or by_concept.get('Revenues')
    income = by_concept.get('NetIncomeLoss')
    if revenue and income and revenue.value and revenue.unit == income.unit == 'USD' and (revenue.period_start, revenue.period_end) == (income.period_start, income.period_end):
        calculations.append(Calculation(id='gaap-net-margin', label='GAAP net margin', formula='NetIncomeLoss / Revenue × 100',
            value=round(income.value / revenue.value * 100, 6), unit='percent', evidence_ids=[income.id, revenue.id]))
    questions = ['Review the primary documents and identify the earnings claims to investigate.']
    if not evidence:
        questions.append('No matching evidence published by the requested as-of date was available; confirm fiscal period and source access.')
    return InvestigationResponse(**request.model_dump(), status='partial' if evidence else 'blocked', evidence=evidence,
        claims=[], calculations=calculations, findings=[], limitations=limitations, unresolved_questions=questions,
        integration_status=integrations)
