"""Future model proposals and a server-side gate. No inference or network execution.

Model text is untrusted. Only the host registers disclosures/evidence, retrieves
data, records a completed challenge, and grants human approval outside this gate.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import hashlib
import json
import time
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from backend.models import Evidence, InvestigationRequest, StrictModel
from .models import ClaimInput
from .tools import verify

VERSION = 'claimtrace.model-tools.v1'
Identifier = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9_-]{1,80}$')]
FactIdentifier = Annotated[str, StringConstraints(pattern=r'^[A-Za-z0-9_.:-]{1,200}$')]
DateText = Annotated[str, StringConstraints(pattern=r'^\d{4}-\d{2}-\d{2}$')]
DecimalText = Annotated[str, StringConstraints(pattern=r'^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$', max_length=80)]
Metric = Literal['revenue', 'diluted_eps', 'net_income', 'net_margin', 'unsupported']
Check = Literal['source_dates', 'exact_period', 'units', 'accounting_basis', 'conflicting_values', 'missing_context']
ALL_CHECKS = ('source_dates', 'exact_period', 'units', 'accounting_basis', 'conflicting_values', 'missing_context')


class Proposal(StrictModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class QuoteReference(Proposal):
    disclosure_id: Identifier
    text_sha256: Annotated[str, StringConstraints(pattern=r'^[a-f0-9]{64}$')]
    normalization: Literal['unicode-codepoints-exact-v1']
    start: int = Field(ge=0, le=12000)
    end: int = Field(gt=0, le=12000)
    quote: str = Field(min_length=1, max_length=4000)


class ExtractedClaim(Proposal):
    id: Identifier
    text: str = Field(min_length=1, max_length=4000)
    metric: Metric
    expected_value_decimal: DecimalText | None
    unit: Literal['USD', 'USD millions', 'USD billions', 'USD/shares', 'USD/share', '%', 'unknown']
    accounting_basis: Literal['GAAP', 'non-GAAP', 'unknown']
    period_start: DateText
    period_end: DateText
    input_kind: Literal['model_extracted_proposal']
    quote_ref: QuoteReference

    def verification_input(self):
        # Conversion does not establish human authorship or semantic extraction.
        # The legacy verifier consumes this private arithmetic-only adaptation.
        values = self.model_dump(exclude={'quote_ref', 'input_kind'})
        return ClaimInput.model_validate(values | {'input_kind': 'human_assertion', 'tolerance_decimal': '0'})

    @model_validator(mode='after')
    def bounded_values(self):
        if self.expected_value_decimal is not None and abs(Decimal(self.expected_value_decimal).as_tuple().exponent) > 64:
            raise ValueError('Decimal scale exceeds the bounded calculation contract')
        self.verification_input()
        return self


class ExtractClaims(Proposal):
    claims: list[ExtractedClaim] = Field(min_length=1, max_length=3)


class SelectChecks(Proposal):
    claim_ids: list[Identifier] = Field(min_length=1, max_length=3)
    checks: list[Check] = Field(min_length=1, max_length=6)


class QueryEvidence(Proposal):
    metrics: list[Literal['revenue', 'diluted_eps', 'net_income']] = Field(min_length=1, max_length=3)


class CalculateClaim(Proposal):
    claim_id: Identifier
    operation: Literal['compare_value', 'gaap_net_margin']
    evidence_ids: list[FactIdentifier] = Field(max_length=25)


class AdditionalInvestigation(Proposal):
    claim_id: Identifier
    reason: Literal['conflicting_values', 'missing_evidence', 'contradicted_value', 'missing_context']
    evidence_ids: list[FactIdentifier] = Field(max_length=25)


class ConclusionFinding(Proposal):
    claim_id: Identifier
    classification: Literal['supported', 'contradicted', 'incomplete', 'unresolved']
    evidence_ids: list[FactIdentifier] = Field(max_length=25)


class ModelConclusion(Proposal):
    schema_version: Literal['claimtrace.model-tools.v1']
    findings: list[ConclusionFinding] = Field(min_length=1, max_length=3)
    # Prose is a proposal, not validated financial reasoning. The host renders
    # authoritative findings/citations and retains limitations independently.
    briefing_proposal: str = Field(min_length=1, max_length=4000)
    human_review_status: Literal['required']
    semantic_mapping_status: Literal['unverified']


TOOLS = {
    'propose_extracted_claims': (ExtractClaims, 'Propose at most three exact-quote claims from host-registered disclosure text; no factual verdict or human approval.'),
    'select_evidence_checks': (SelectChecks, 'Select permitted checks for known claims. Selection does not establish that a check ran.'),
    'query_financial_evidence': (QueryEvidence, 'Request approved financial metrics through the host Zetaris reader in the immutable company/period/as-of scope. No SQL or scope overrides.'),
    'calculate_financial_claim': (CalculateClaim, 'Request deterministic comparison or GAAP margin against known eligible facts. Host computes the verdict.'),
    'request_additional_investigation': (AdditionalInvestigation, 'Request the one permitted bounded recheck for a recorded non-supported finding; host selects approved reader.'),
    'submit_investigation_conclusion': (ModelConclusion, 'Propose a briefing with classifications and citations identical to host verification, after a host-recorded challenge. Human review remains required.'),
}


def tool_definitions():
    """Chat Completions function-tool shape, not proof of Runtime support."""
    return [{'type': 'function', 'function': {'name': name, 'description': description,
             'strict': True, 'parameters': model.model_json_schema()}}
            for name, (model, description) in TOOLS.items()]


@dataclass(frozen=True)
class TrustedDisclosure:
    """Registered only by host ingestion; source text is untrusted content."""
    id: str
    text: str
    url: str
    published_at: date
    period_start: date
    period_end: date

    @property
    def text_sha256(self):
        return hashlib.sha256(self.text.encode('utf-8')).hexdigest()


class ModelProposalGate:
    """Preparation seam for a future host dispatcher; never executes retrieval.

    Every attempted proposal consumes a shared call slot. The caller must also
    charge inference/retrieval latency to this same deadline and enforce the
    10-transition controller bound; this module is not a runtime controller.
    """
    def __init__(self, request, evidence=(), disclosures=(), *, clock=time.monotonic):
        request = request if isinstance(request, InvestigationRequest) else InvestigationRequest.model_validate(request)
        self._request_json = request.model_dump_json()
        self._as_of = request.as_of
        self._cik = str(int(request.company.cik))
        self._facts = {}
        for item in evidence:
            fact = Evidence.model_validate(item.model_dump() if isinstance(item, Evidence) else item)
            self._eligible(fact)
            if fact.id in self._facts:
                raise ValueError('Duplicate evidence ID')
            self._facts[fact.id] = fact.model_dump_json()
        self._disclosures = {}
        for disclosure in disclosures:
            parsed = urlsplit(disclosure.url)
            if (disclosure.id in self._disclosures or len(disclosure.text) > 12000 or
                    not disclosure.period_start <= disclosure.period_end <= disclosure.published_at <= self._as_of or
                    parsed.scheme != 'https' or parsed.hostname != 'www.sec.gov' or parsed.username or parsed.password or
                    not parsed.path.startswith(f'/Archives/edgar/data/{self._cik}/')):
                raise ValueError('Invalid registered disclosure scope or chronology')
            self._disclosures[disclosure.id] = disclosure
        self._clock, self._deadline, self._calls = clock, clock() + 120, 0
        self._claims, self._verified, self._selected = {}, {}, {}
        self._challenge_completed = False
        self._rechecks = 0

    def _eligible(self, fact):
        parsed = urlsplit(fact.url)
        if (fact.published_at > self._as_of or fact.period_end > self._as_of or
                not parsed.path.startswith(f'/Archives/edgar/data/{self._cik}/') or not fact.locator.strip()):
            raise ValueError('Unknown issuer, future evidence or missing locator')

    @property
    def scope(self):
        """Defensive copy; the model cannot change retrieval scope."""
        return json.loads(self._request_json)

    def record_completed_challenge(self):
        """Host-only hook AFTER independently running challenger checks."""
        if not self._verified or any(set(self._selected.get(c, ())) != set(ALL_CHECKS) for c in self._claims):
            raise ValueError('All selected quality checks and verifications are required')
        self._challenge_completed = True

    def validate(self, tool_name, arguments):
        if self._calls >= 8 or self._clock() >= self._deadline:
            raise ValueError('Shared tool/time budget exhausted')
        self._calls += 1
        if tool_name not in TOOLS:
            raise ValueError('Tool is not permitted')
        model = TOOLS[tool_name][0]
        # Strict Python validation rejects coercion; JSON decoding remains caller
        # owned and duplicate JSON keys must be rejected before this boundary.
        proposal = model.model_validate(arguments)
        if isinstance(proposal, ExtractClaims):
            if self._claims:
                raise ValueError('Claims are immutable after registration')
            if len({c.id for c in proposal.claims}) != len(proposal.claims):
                raise ValueError('Duplicate claim IDs')
            for claim in proposal.claims:
                ref = claim.quote_ref
                document = self._disclosures.get(ref.disclosure_id)
                if (document is None or ref.text_sha256 != document.text_sha256 or
                        not ref.start < ref.end <= len(document.text) or document.text[ref.start:ref.end] != ref.quote or claim.text != ref.quote or
                        claim.period_start != document.period_start.isoformat() or claim.period_end != document.period_end.isoformat()):
                    raise ValueError('Quote, period, source hash or offsets are not trusted')
            self._claims = {c.id: c.model_dump_json() for c in proposal.claims}
        elif isinstance(proposal, SelectChecks):
            self._known_claims(proposal.claim_ids)
            for cid in proposal.claim_ids:
                self._selected[cid] = tuple(proposal.checks)
        elif isinstance(proposal, CalculateClaim):
            claim = self._known_claims([proposal.claim_id])[0]
            if proposal.operation != ('gaap_net_margin' if claim.metric == 'net_margin' else 'compare_value'):
                raise ValueError('Calculation operation does not match claim metric')
            self._known_facts(proposal.evidence_ids)
            # Never let a model omit contrary registered facts to forge support.
            all_facts = [Evidence.model_validate_json(raw) for raw in self._facts.values()]
            result, calculations = verify(claim.verification_input(), all_facts)
            if set(proposal.evidence_ids) != set(result['evidence_ids']):
                raise ValueError('Calculation must include all comparable known evidence')
            self._verified[claim.id] = result
            self._challenge_completed = False
            return {'proposal': proposal.model_dump(), 'host_finding': result, 'calculations': calculations,
                    'semantic_mapping_status': 'unverified', 'human_review_status': 'required'}
        elif isinstance(proposal, AdditionalInvestigation):
            self._known_claims([proposal.claim_id])
            self._known_facts(proposal.evidence_ids)
            finding = self._verified.get(proposal.claim_id)
            if self._rechecks or finding is None or finding['classification'] == 'supported':
                raise ValueError('One recheck requires a recorded non-supported finding')
            expected_reason = {'contradicted': 'contradicted_value', 'incomplete': 'missing_evidence', 'unresolved': 'missing_context'}[finding['classification']]
            if proposal.reason not in (expected_reason, 'conflicting_values' if finding['classification'] == 'unresolved' and finding['evidence_ids'] else expected_reason):
                raise ValueError('Recheck reason must match recorded finding')
            if set(proposal.evidence_ids) != set(finding['evidence_ids']):
                raise ValueError('Recheck must retain recorded evidence references')
            self._rechecks += 1
            self._challenge_completed = False
        elif isinstance(proposal, ModelConclusion):
            if not self._challenge_completed or {f.claim_id for f in proposal.findings} != set(self._claims) or len(proposal.findings) != len(self._claims):
                raise ValueError('Every claim requires host verification and completed challenge')
            for finding in proposal.findings:
                actual = self._verified.get(finding.claim_id)
                if (actual is None or actual['classification'] != finding.classification or
                        set(actual['evidence_ids']) != set(finding.evidence_ids)):
                    raise ValueError('Conclusion cannot forge verdicts or citations')
                self._known_facts(finding.evidence_ids)
        return proposal.model_dump()

    def _known_claims(self, ids):
        if len(set(ids)) != len(ids) or any(cid not in self._claims for cid in ids):
            raise ValueError('Unknown or duplicate claim reference')
        return [ExtractedClaim.model_validate_json(self._claims[cid]) for cid in ids]

    def _known_facts(self, ids):
        if len(set(ids)) != len(ids) or any(eid not in self._facts for eid in ids):
            raise ValueError('Unknown or duplicate evidence reference')
        return [Evidence.model_validate_json(self._facts[eid]) for eid in ids]
