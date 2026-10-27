"""Bounded rejection metadata. Never copy model values or exception messages."""
from pydantic import ValidationError

from .model_contracts import TOOLS


_FIELDS = frozenset(('claims', 'id', 'text', 'metric', 'expected_value_decimal',
    'unit', 'accounting_basis', 'period_start', 'period_end', 'input_kind',
    'quote_ref', 'disclosure_id', 'text_sha256', 'normalization', 'start', 'end',
    'quote', 'claim_ids', 'checks', 'metrics', 'claim_id', 'operation',
    'evidence_ids', 'reason', 'schema_version', 'findings', 'classification',
    'briefing_proposal', 'human_review_status', 'semantic_mapping_status'))
_ERROR_TYPES = frozenset(('missing', 'extra_forbidden', 'string_type',
    'string_pattern_mismatch', 'string_too_long', 'string_too_short', 'int_type',
    'greater_than', 'greater_than_equal', 'less_than_equal', 'literal_error',
    'list_type', 'too_short', 'too_long', 'model_type', 'value_error'))
_RULES = {
    'Shared tool/time budget exhausted': 'gate_budget_exhausted',
    'Tool is not permitted': 'tool_not_permitted',
    'Claims are immutable after registration': 'claims_already_registered',
    'Duplicate claim IDs': 'duplicate_claim_ids',
    'Quote, period, source hash or offsets are not trusted': 'source_binding_invalid',
    'Calculation operation does not match claim metric': 'calculation_metric_mismatch',
    'Calculation must include all comparable known evidence': 'incomplete_calculation_evidence',
    'One recheck requires a recorded non-supported finding': 'recheck_prerequisite_unsatisfied',
    'Recheck reason must match recorded finding': 'recheck_reason_mismatch',
    'Recheck must retain recorded evidence references': 'recheck_evidence_mismatch',
    'Every claim requires host verification and completed challenge': 'conclusion_prerequisite_unsatisfied',
    'Conclusion cannot forge verdicts or citations': 'conclusion_verdict_or_citations_mismatch',
    'Unknown or duplicate claim reference': 'unknown_or_duplicate_claim',
    'Unknown or duplicate evidence reference': 'unknown_or_duplicate_evidence',
}


def rejection_diagnostic(tool, error, *, validation_phase):
    """Return constants only; even unknown keys/locations/types become constants.

    This describes a newly observed rejection, not the unretained original live
    proposal. Values, exception text, raw arguments and private reasoning are
    deliberately unavailable here.
    """
    result = {'tool': tool if type(tool) is str and tool in TOOLS else 'unknown',
              'phase': 'gate' if validation_phase is True else 'execution',
              'rule': 'unclassified_rejection', 'schema_issues': []}
    if validation_phase is not True:
        return result
    if type(error) is ValidationError:
        result.update(phase='schema', rule='canonical_schema_invalid')
        for issue in error.errors(include_input=False, include_context=False, include_url=False)[:8]:
            path = [part if type(part) is str and part in _FIELDS else
                    '*' if type(part) is int else 'unknown_field'
                    for part in issue.get('loc', ())[:8]]
            kind = issue.get('type')
            result['schema_issues'].append({'path': path,
                'type': kind if type(kind) is str and kind in _ERROR_TYPES else 'other'})
    elif type(error) is ValueError and len(error.args) == 1 and type(error.args[0]) is str:
        result['rule'] = _RULES.get(error.args[0], 'unclassified_rejection')
    return result
