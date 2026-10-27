"""Explicit NVIDIA span-selection tool; no repair of raw extraction proposals.

The model selects a source span and financial interpretation. Only exact source
binding metadata comes from the host. The canonical proposal still passes the
unchanged investigation gate and independent financial verification.
"""
from copy import deepcopy
from datetime import date
import hashlib
import json
from typing import Literal

from pydantic import Field

from backend.investigation.model_contracts import (
    Proposal, Identifier, DecimalText, Metric, ExtractClaims, ExtractedClaim,
    ALL_CHECKS, tool_definitions,
)

NATIVE_TOOL = 'propose_claim_from_span'
CANONICAL_TOOL = 'propose_extracted_claims'


class SpanClaim(Proposal):
    id: Identifier
    disclosure_id: Identifier
    span_index: int = Field(ge=0, le=127)
    metric: Metric
    expected_value_decimal: DecimalText | None = Field(description='Financial quantity as a plain decimal STRING, never a JSON number, comma-grouped number or currency symbol. Interpret the source quantity and its unit independently; do not guess or fill a value from tool metadata.')
    unit: Literal['USD', 'USD millions', 'USD billions', 'USD/shares', 'USD/share', '%', 'unknown']
    accounting_basis: Literal['GAAP', 'non-GAAP', 'unknown']


def compact_tool_definitions(host_tools):
    """A separate explicit wire contract, never a relaxed canonical contract."""
    if host_tools != tool_definitions():
        raise ValueError('Canonical host tool definitions required')
    result = deepcopy(host_tools)
    for definition in result:
        if definition['function']['name'] == CANONICAL_TOOL:
            definition['function'] = {
                'name': NATIVE_TOOL,
                'description': 'Select one registered disclosure span by its explicit span_index and propose a financial interpretation. Host supplies immutable quote, hash, offsets and source period; financial meaning remains a model proposal requiring independent host checks and human review.',
                'strict': True, 'parameters': SpanClaim.model_json_schema(),
            }
    return result


def inline_local_schema(schema):
    """Inline bounded trusted local definitions without changing constraints.

    Runtime callers only supply schemas copied from the exact canonical host
    tool contract. References outside that schema, cycles and ambiguous merges
    fail closed; no model-supplied schema is ever accepted by the provider.
    """
    if not isinstance(schema, dict):
        raise ValueError('Trusted object schema required')
    definitions = schema.get('$defs', {})
    if not isinstance(definitions, dict):
        raise ValueError('Local schema definitions required')
    visited = 0

    def expand(node, active=(), depth=0):
        nonlocal visited
        visited += 1
        if visited > 4096 or depth > 32:
            raise ValueError('Schema expansion exceeds bounds')
        if isinstance(node, dict):
            if '$ref' in node:
                reference = node['$ref']
                if not isinstance(reference, str) or not reference.startswith('#/$defs/'):
                    raise ValueError('Only trusted local definition references are supported')
                name = reference[len('#/$defs/'):]
                if not name or '/' in name or '~' in name or name not in definitions or name in active:
                    raise ValueError('Invalid, cyclic or missing local schema reference')
                target = expand(definitions[name], active + (name,), depth + 1)
                siblings = {key: expand(value, active, depth + 1) for key, value in node.items() if key not in ('$ref', '$defs')}
                if not isinstance(target, dict) or any(key in target and target[key] != value for key, value in siblings.items()):
                    raise ValueError('Ambiguous reference sibling constraints')
                return target | siblings
            return {key: expand(value, active, depth + 1) for key, value in node.items() if key != '$defs'}
        if isinstance(node, list):
            return [expand(value, active, depth + 1) for value in node]
        return deepcopy(node)

    return expand(schema)


def project_wire_constants(schema):
    """Project trusted copied NVIDIA schemas to a const-free grammar.

    Primitive literals retain identical enum validation. Array const is omitted
    while item/length constraints remain; the canonical host gate independently
    requires all comparable evidence and rejects duplicate/omitted/unknown IDs.
    """
    result = deepcopy(schema)

    def project(node):
        if isinstance(node, dict):
            if '$ref' in node or '$defs' in node:
                raise ValueError('Only inlined trusted wire schemas are supported')
            if 'const' in node:
                literal = node.pop('const')
                if not isinstance(literal, list):
                    if isinstance(literal, dict) or ('enum' in node and literal not in node['enum']):
                        raise ValueError('Unsupported trusted wire constant')
                    node['enum'] = [literal]
            for value in node.values():
                project(value)
        elif isinstance(node, list):
            for value in node:
                project(value)

    project(result)
    return result


def available_native_tools(host_tools, context):
    """Advertise only actions whose host-state prerequisites have completed.

    This is a usability restriction on the model's choices, not an authority to
    execute them. The unchanged canonical gate still checks every argument and
    effect. No source text, model prose or memory record selects availability.
    """
    native_tools = compact_tool_definitions(host_tools)
    required = {'claims', 'evidence', 'verified', 'selected_checks', 'tool_results'}
    if not isinstance(context, dict) or not required <= context.keys():
        raise ValueError('Complete host state required')
    claims, evidence = context['claims'], context['evidence']
    verified, selected, trace = context['verified'], context['selected_checks'], context['tool_results']
    if (not isinstance(claims, list) or len(claims) > 3 or not isinstance(evidence, list) or len(evidence) > 100 or
            not isinstance(verified, dict) or not isinstance(selected, dict) or
            not isinstance(trace, list) or len(trace) > 10):
        raise ValueError('Bounded host state required')
    claim_ids = [ExtractedClaim.model_validate(claim).id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)) or set(verified) - set(claim_ids) or set(selected) - set(claim_ids):
        raise ValueError('Known unique host claims required')
    fact_ids = [fact.get('id') for fact in evidence if isinstance(fact, dict)]
    if len(fact_ids) != len(evidence) or any(not isinstance(fid, str) for fid in fact_ids) or len(set(fact_ids)) != len(fact_ids):
        raise ValueError('Known unique host evidence required')
    for cid, checks in selected.items():
        if not isinstance(checks, list) or any(check not in ALL_CHECKS for check in checks):
            raise ValueError('Known host checks required')
    for cid, finding in verified.items():
        if (not isinstance(finding, dict) or finding.get('claim_id') != cid or
                finding.get('classification') not in ('supported', 'contradicted', 'incomplete', 'unresolved') or
                not isinstance(finding.get('evidence_ids'), list) or
                len(set(finding['evidence_ids'])) != len(finding['evidence_ids']) or
                set(finding['evidence_ids']) - set(fact_ids) or
                (finding['classification'] in ('supported', 'contradicted') and not finding['evidence_ids'])):
            raise ValueError('Current host verification required')
    states = []
    canonical_names = {tool['function']['name'] for tool in host_tools}
    for event in trace:
        if not isinstance(event, dict) or event.get('state') not in canonical_names:
            raise ValueError('Actual host tool trace required')
        states.append(event['state'])
    if (states.count('query_financial_evidence') > 1 or
            states.count('request_additional_investigation') > 1 or
            'submit_investigation_conclusion' in states):
        raise ValueError('Open bounded host investigation required')
    if not claims:
        if verified or selected:
            raise ValueError('Host state has no registered claims')
        if not any(d.get('quote_spans') for d in context.get('disclosures', []) if isinstance(d, dict)):
            raise ValueError('Registered source spans required before extraction')
        names = {NATIVE_TOOL}
    else:
        names = set()
        all_selected = all(set(selected.get(cid, [])) == set(ALL_CHECKS) for cid in claim_ids)
        queried = 'query_financial_evidence' in states
        if not all_selected:
            names.add('select_evidence_checks')
        if not queried:
            names.add('query_financial_evidence')
        else:
            latest_retrieval = max(index for index, state in enumerate(states)
                if state in ('query_financial_evidence', 'request_additional_investigation'))
            unchanged_single_calculation = (len(claim_ids) == 1 and
                'calculate_financial_claim' in states[latest_retrieval + 1:])
            # A second calculation on the same single-claim evidence snapshot
            # cannot add information. A real bounded recheck starts a new epoch;
            # the model must still propose its own conclusion or legal recheck.
            if not unchanged_single_calculation:
                names.add('calculate_financial_claim')
            if ('request_additional_investigation' not in states and
                    any(finding['classification'] != 'supported' for finding in verified.values())):
                names.add('request_additional_investigation')
        challenges = trace[-1].get('host_challenge') if trace else None
        challenge_matches = (isinstance(challenges, list) and len(challenges) == len(claim_ids) and
                             {c.get('claim_id') for c in challenges if isinstance(c, dict)} == set(claim_ids))
        if challenge_matches:
            for challenge in challenges:
                current = verified.get(challenge['claim_id'])
                if (current is None or set(challenge.get('checks_run', [])) != set(ALL_CHECKS) or
                        challenge.get('classification') != current['classification'] or
                        not isinstance(challenge.get('evidence_ids'), list) or
                        set(challenge['evidence_ids']) != set(current['evidence_ids'])):
                    challenge_matches = False
                    break
        if queried and all_selected and set(verified) == set(claim_ids) and challenge_matches:
            names.add('submit_investigation_conclusion')
    result = [tool for tool in native_tools if tool['function']['name'] in names]
    if not result:
        raise ValueError('No legal native action remains')
    return _known_argument_schemas(result, context, claim_ids, fact_ids)


def _known_argument_schemas(native_tools, context, claim_ids, fact_ids):
    """Constrain copied wire schemas to host-owned references and operations.

    These schemas describe already-enforced host prerequisites. They do not
    replace proposal validation, repair model arguments, set financial values,
    or infer claim meaning from source text or reviewed memory.
    """
    result = deepcopy(native_tools)

    def references(schema):
        if isinstance(schema, dict):
            properties = schema.get('properties', {})
            if 'claim_id' in properties:
                properties['claim_id']['enum'] = list(claim_ids)
            if 'claim_ids' in properties:
                properties['claim_ids']['items']['enum'] = list(claim_ids)
            if 'evidence_ids' in properties:
                if fact_ids:
                    properties['evidence_ids']['items']['enum'] = list(fact_ids)
                else:
                    properties['evidence_ids']['maxItems'] = 0
            for child in schema.values():
                references(child)
        elif isinstance(schema, list):
            for child in schema:
                references(child)

    for tool in result:
        parameters = tool['function']['parameters']
        references(parameters)
        if tool['function']['name'] == 'calculate_financial_claim' and len(claim_ids) == 1:
            cid = claim_ids[0]
            fields = parameters['properties']
            fields['claim_id']['const'] = cid
            operation = 'gaap_net_margin' if context['claims'][0]['metric'] == 'net_margin' else 'compare_value'
            fields['operation'].update(const=operation, enum=[operation])
            current = context['verified'].get(cid)
            if current is not None:
                ids = list(current['evidence_ids'])
                fields['evidence_ids'].update(const=ids, minItems=len(ids), maxItems=len(ids))
        tool['function']['parameters'] = project_wire_constants(inline_local_schema(parameters))
    return result


def compact_context(context):
    """Advertise explicit indexes without mutating any registered source data."""
    result = deepcopy(context)
    if not isinstance(result, dict):
        raise ValueError('Host context required')
    for disclosure in result.get('disclosures', []):
        spans = disclosure.get('quote_spans', [])
        if not isinstance(spans, list) or len(spans) > 128:
            raise ValueError('Bounded registered spans required')
        for index, span in enumerate(spans):
            if not isinstance(span, dict):
                raise ValueError('Registered source span required')
            span['span_index'] = index
    return result


def canonical_proposal(proposal, original_context):
    """Expand only the explicit compact tool, retaining the model's own values."""
    if not isinstance(proposal, dict) or set(proposal) != {'tool', 'arguments'}:
        raise ValueError('A single explicit native proposal is required')
    if proposal['tool'] != NATIVE_TOOL:
        if proposal['tool'] not in {tool['function']['name'] for tool in tool_definitions()} - {CANONICAL_TOOL}:
            raise ValueError('Unknown native tool')
        return deepcopy(proposal), False
    argument = SpanClaim.model_validate(proposal['arguments'])
    disclosures = original_context.get('disclosures', [])
    if not isinstance(disclosures, list) or len(disclosures) > 3:
        raise ValueError('Host-registered disclosure list required')
    registered = {}
    for disclosure in disclosures:
        if not isinstance(disclosure, dict) or disclosure.get('id') in registered:
            raise ValueError('Unique registered disclosure IDs required')
        registered[disclosure.get('id')] = disclosure
    claims = []
    for claim in [argument]:
        disclosure = registered.get(claim.disclosure_id)
        if disclosure is None:
            raise ValueError('Unknown registered disclosure')
        text, spans = disclosure.get('text'), disclosure.get('quote_spans')
        if (not isinstance(text, str) or len(text) > 12000 or not isinstance(spans, list) or
                len(spans) > 128 or claim.span_index >= len(spans) or
                disclosure.get('text_sha256') != hashlib.sha256(text.encode('utf-8')).hexdigest()):
            raise ValueError('Invalid immutable registered source')
        span = spans[claim.span_index]
        if (not isinstance(span, dict) or type(span.get('start')) is not int or type(span.get('end')) is not int or
                not 0 <= span['start'] < span['end'] <= len(text) or
                not isinstance(span.get('quote'), str) or text[span['start']:span['end']] != span['quote']):
            raise ValueError('Invalid host source span')
        start, end = date.fromisoformat(disclosure['period_start']), date.fromisoformat(disclosure['period_end'])
        publication = date.fromisoformat(disclosure['published_at'])
        if not start <= end <= publication:
            raise ValueError('Invalid registered source chronology')
        values = claim.model_dump(exclude={'disclosure_id', 'span_index'})
        values.update(text=span['quote'], period_start=disclosure['period_start'],
                      period_end=disclosure['period_end'], input_kind='model_extracted_proposal',
                      quote_ref={'disclosure_id': claim.disclosure_id,
                                 'text_sha256': disclosure['text_sha256'],
                                 'normalization': 'unicode-codepoints-exact-v1',
                                 'start': span['start'], 'end': span['end'], 'quote': span['quote']})
        claims.append(values)
    canonical = ExtractClaims.model_validate({'claims': claims})
    return {'tool': CANONICAL_TOOL, 'arguments': canonical.model_dump(mode='json')}, True
