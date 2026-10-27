"""Eight selected diagnostic cases on authentic cached ISRG facts; no inference.

The value-only baseline is intentionally weak, not an external model or an
industry baseline. These cases measure the selected guardrail checks only.
"""
import argparse
import json
from decimal import localcontext
from pathlib import Path

from backend.models import InvestigationRequest
from backend.sources import cached_evidence
from .models import ClaimInput
from .tools import CONCEPTS, evidence_number, verify


def _request(as_of='2026-10-24'):
    return InvestigationRequest.model_validate({'company': {'name': 'Intuitive Surgical', 'ticker': 'ISRG', 'cik': '1035267'},
        'fiscal_year': 2026, 'period': 'Q2', 'as_of': as_of, 'evidence_backend': 'sec'})


def _claim(**changes):
    return ClaimInput.model_validate({'id': 'diagnostic-assertion', 'text': 'Diagnostic human assertion, not an issuer quotation: diluted EPS was 2.29 USD/shares.',
        'metric': 'diluted_eps', 'expected_value_decimal': '2.29', 'unit': 'USD/shares',
        'period_start': '2026-04-01', 'period_end': '2026-06-30'} | changes)


def _value_only_baseline(claim, original_facts):
    """Intentionally ignore cutoff, unit, period and accounting basis."""
    if claim.metric == 'unsupported':
        return 'unresolved'
    with localcontext() as context:
        context.prec = 100
        if claim.metric == 'net_margin':
            revenue = next(evidence_number(e) for e in original_facts if e.concept in CONCEPTS['revenue'])
            income = next(evidence_number(e) for e in original_facts if e.concept in CONCEPTS['net_income'])
            actual = income / revenue * 100
        else:
            actual = next(evidence_number(e) for e in original_facts if e.concept in CONCEPTS[claim.metric])
        return 'supported' if abs(actual - claim.expected_value_decimal) <= claim.tolerance_decimal else 'contradicted'


def evaluate():
    original_facts = cached_evidence(_request())
    if not original_facts:
        raise RuntimeError('Authentic cached ISRG evidence is required; no synthetic facts substituted.')
    specifications = [
        ('correct_eps', _claim(), '2026-10-24', 'supported'),
        ('wrong_eps', _claim(text='Diagnostic assertion: EPS was 9 USD/shares.', expected_value_decimal='9'), '2026-10-24', 'contradicted'),
        ('non_gaap', _claim(text='Diagnostic assertion: non-GAAP EPS was 2.29 USD/shares.', accounting_basis='non-GAAP'), '2026-10-24', 'incomplete'),
        ('wrong_period', _claim(text='Diagnostic assertion: Q1 EPS was 2.29 USD/shares.', period_start='2026-01-01', period_end='2026-03-31'), '2026-10-24', 'incomplete'),
        ('wrong_unit', _claim(text='Diagnostic assertion: EPS was 2.29 EUR/share.', unit='EUR/share'), '2026-10-24', 'incomplete'),
        ('unsupported_qualitative', _claim(text='Diagnostic assertion: management execution caused earnings growth.', metric='unsupported', expected_value_decimal=None), '2026-10-24', 'unresolved'),
        ('prepublication', _claim(), '2026-07-20', 'incomplete'),
        ('wrong_margin', _claim(text='Diagnostic assertion: GAAP net margin was 99 percent.', metric='net_margin', expected_value_decimal='99', unit='%'), '2026-10-24', 'contradicted'),
    ]
    cases = []
    for case_id, claim, cutoff, expected in specifications:
        eligible = cached_evidence(_request(cutoff))
        finding, calculations = verify(claim, eligible)
        cases.append({'case': case_id, 'claim': claim.model_dump(mode='json'), 'as_of': cutoff,
            'expected_classification': expected, 'guarded_classification': finding['classification'],
            'baseline_classification': _value_only_baseline(claim, original_facts),
            'eligible_evidence_count': len(eligible), 'finding': finding, 'calculations': calculations,
            'citations': [{'id': e.id, 'url': e.url, 'published_at': e.published_at.isoformat(),
                           'source_sha256': e.source_sha256, 'source_mode': e.source_mode} for e in eligible]})
    return {'evaluation_kind': 'deliberately_selected_guardrail_diagnostic',
        'baseline': 'Deliberately weak value-only ablation; not an external model or industry baseline.',
        'data': 'Authentic cached SEC-derived ISRG Q2 2026 evidence; no live requests.',
        'assumptions': ['Assertions are evaluator-authored human test inputs, never issuer quotations.',
            'Eight cases were deliberately selected to exercise existing deterministic safeguards.',
            'Baseline uses the same original postpublication numeric facts while deliberately ignoring cutoff, period, unit and accounting basis.',
            'No live AI inference, generalized accuracy, speed or impact claim follows from these results.',
            'Cached received numeric precision does not establish original filing rounding precision.'],
        'case_count': len(cases),
        'guarded_matches_declared_expectations': sum(c['guarded_classification'] == c['expected_classification'] for c in cases),
        'baseline_matches_declared_expectations': sum(c['baseline_classification'] == c['expected_classification'] for c in cases),
        'cases': cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional local UTF-8 JSON result file')
    args = parser.parse_args()
    serialized = json.dumps(evaluate(), indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.write_text(serialized, encoding='utf-8')
    print(serialized, end='')


if __name__ == '__main__':
    main()
