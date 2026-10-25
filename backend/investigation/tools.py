"""Restricted deterministic calculations with explicit received-value precision."""
from decimal import Decimal, localcontext

CONCEPTS = {
    'revenue': {'RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues'},
    'diluted_eps': {'EarningsPerShareDiluted'},
    'net_income': {'NetIncomeLoss'},
}
SCALES = {'USD': ('USD', Decimal(1)), 'USD millions': ('USD', Decimal(1000000)),
          'USD billions': ('USD', Decimal(1000000000)),
          'USD/shares': ('USD/shares', Decimal(1)), 'USD/share': ('USD/shares', Decimal(1)),
          '%': ('%', Decimal(1))}


def comparable(claim, evidence):
    return [e for e in evidence if e.period_start == claim.period_start and e.period_end == claim.period_end]


def verify(claim, evidence):
    # Inputs have at most 34 digits and adjusted exponent +/-30. This context
    # preserves exact scaling/subtraction across that range; division is bounded
    # separately below and can still require rounding.
    with localcontext() as ctx:
        ctx.prec = 100
        return _verify(claim, evidence)


def evidence_number(evidence):
    return Decimal(evidence.value_decimal) if evidence.value_decimal is not None else Decimal(str(evidence.value))


def _verify(claim, evidence):
    finding = {'claim_id': claim.id, 'classification': 'incomplete', 'evidence_ids': [],
               'explanation': '', 'supporting_findings': [], 'challenging_findings': []}
    if claim.metric == 'unsupported':
        finding.update(classification='unresolved', explanation='Unsupported qualitative/causal assertion; no model inference or suitable tool is available.')
        return finding, []
    if claim.accounting_basis != 'GAAP':
        finding['explanation'] = 'GAAP evidence cannot verify a non-GAAP or unknown-basis assertion without a reconciliation.'
        return finding, []
    if claim.unit not in SCALES:
        finding['explanation'] = 'Unit is unsupported; no implicit currency or per-share conversion is permitted.'
        return finding, []
    unit, scale = SCALES[claim.unit]
    candidates = comparable(claim, evidence)
    calculations = []
    if claim.metric == 'net_margin':
        revenues = [e for e in candidates if e.concept in CONCEPTS['revenue'] and e.unit == 'USD']
        incomes = [e for e in candidates if e.concept in CONCEPTS['net_income'] and e.unit == 'USD']
        facts = revenues + incomes
        if not revenues or not incomes or unit != '%':
            finding['explanation'] = 'Net margin requires same-period GAAP net income and revenue in USD, with a percentage claim.'
            return finding, []
        if len({evidence_number(e) for e in revenues}) != 1 or len({evidence_number(e) for e in incomes}) != 1:
            finding.update(classification='unresolved', explanation='Conflicting eligible financial facts; no value was silently selected.', evidence_ids=[e.id for e in facts])
            return finding, []
        revenue, income = evidence_number(revenues[0]), evidence_number(incomes[0])
        if revenue == 0:
            finding.update(classification='unresolved', explanation='Cannot calculate margin with a zero revenue denominator.', evidence_ids=[e.id for e in facts])
            return finding, []
        with localcontext() as ctx:
            ctx.prec = 34
            actual = income / revenue * 100
        calculations = [{'tool': 'gaap_net_margin', 'formula': 'net_income / revenue * 100',
                         'value_decimal': str(actual), 'unit': '%', 'evidence_ids': [e.id for e in facts]}]
    else:
        facts = [e for e in candidates if e.concept in CONCEPTS[claim.metric] and SCALES.get(e.unit, (e.unit,))[0] == unit]
        if not facts:
            finding['explanation'] = 'No eligible evidence matches the metric, exact period and unit; YTD is never substituted for a quarter.'
            return finding, []
        actuals = {evidence_number(e) * SCALES[e.unit][1] for e in facts}
        if len(actuals) != 1:
            finding.update(classification='unresolved', explanation='Conflicting eligible source values; human reconciliation is required.', evidence_ids=[e.id for e in facts])
            return finding, []
        actual = actuals.pop()
    expected = claim.expected_value_decimal * scale
    tolerance = claim.tolerance_decimal * scale
    difference = actual - expected
    finding.update(classification='supported' if abs(difference) <= tolerance else 'contradicted',
                   evidence_ids=[e.id for e in facts],
                   explanation='Comparable GAAP evidence agrees within the declared tolerance.' if abs(difference) <= tolerance else 'Comparable GAAP evidence disagrees beyond the declared tolerance.')
    calculations.append({'tool': 'compare_value', 'actual_decimal': str(actual), 'expected_decimal': str(expected),
                         'difference_decimal': str(difference), 'tolerance_decimal': str(tolerance),
                         'unit': unit, 'evidence_ids': finding['evidence_ids'],
                         'precision': ('Decimal arithmetic on exact received numeric representations; original filing rounding precision and any upstream Zetaris DOUBLE loss are not established. Margin division is rounded to 34 significant digits.'
                                       if all(e.value_decimal is not None for e in facts) else
                                       'Decimal arithmetic includes legacy float representations; original source precision is unavailable')})
    return finding, calculations
