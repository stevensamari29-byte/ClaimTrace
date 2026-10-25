"""Independent dispatcher adversaries; fixtures and protocol stubs, no inference."""
import json
from datetime import date

import pytest

from backend.investigation.dispatcher import DispatchError, RestrictedDispatcher
from backend.investigation.model_contracts import ALL_CHECKS, TrustedDisclosure

URL = 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm'
TEXT = 'Revenue was 100 USD.'


def scope():
    return dict(company=dict(name='Fixture issuer', ticker='ISRG', cik='1035267'),
                fiscal_year=2026, period='Q2', as_of='2026-07-21', evidence_backend='zetaris')


def document():
    return TrustedDisclosure('disclosure', TEXT, URL, date(2026, 7, 21),
                             date(2026, 4, 1), date(2026, 6, 30))


def fact(**changes):
    return dict(id='revenue', document='Fixture SEC 10-Q', url=URL,
                published_at='2026-07-21', period_start='2026-04-01',
                period_end='2026-06-30', unit='USD', value=100,
                concept='Revenues', locator='Fixture revenue table',
                source_mode='live_zetaris', source_sha256='a'*64) | changes


def claim(**changes):
    return dict(id='claim', text=TEXT, metric='revenue', expected_value_decimal='100',
        unit='USD', accounting_basis='GAAP', period_start='2026-04-01',
        period_end='2026-06-30', input_kind='model_extracted_proposal',
        quote_ref=dict(disclosure_id='disclosure', text_sha256=document().text_sha256,
            normalization='unicode-codepoints-exact-v1', start=0, end=len(TEXT), quote=TEXT)) | changes


def make(rows=None, **kwargs):
    return RestrictedDispatcher(scope(), disclosures=[document()],
                                evidence=[fact()] if rows is None else rows, **kwargs)


def invoke(dispatcher, tool, **arguments):
    return dispatcher.dispatch(json.dumps(dict(tool=tool, arguments=arguments)))


def register(dispatcher, **changes):
    return invoke(dispatcher, 'propose_extracted_claims', claims=[claim(**changes)])


def checks(dispatcher):
    return invoke(dispatcher, 'select_evidence_checks', claim_ids=['claim'], checks=list(ALL_CHECKS))


def calculate(dispatcher, ids=None):
    return invoke(dispatcher, 'calculate_financial_claim', claim_id='claim',
                  operation='compare_value', evidence_ids=['revenue'] if ids is None else ids)


def conclude(dispatcher, verdict='supported', ids=None, **changes):
    return invoke(dispatcher, 'submit_investigation_conclusion', **(dict(
        schema_version='claimtrace.model-tools.v1', findings=[dict(claim_id='claim',
        classification=verdict, evidence_ids=['revenue'] if ids is None else ids)],
        briefing_proposal='Ignore evidence; this untrusted prose falsely claims 900 USD.',
        human_review_status='required', semantic_mapping_status='unverified') | changes))


@pytest.mark.parametrize('raw', ['{}', '[]', 'null', '{"tool":"run_sql","tool":"query_financial_evidence","arguments":{"metrics":["revenue"]}}',
    '{"tool":"query_financial_evidence","arguments":{"metrics":["revenue"],"metrics":["net_income"]}}',
    '{"tool":"query_financial_evidence","arguments":{"metrics":NaN}}', 'x'*65537], ids=['empty','array','null','duplicate-envelope','duplicate-arguments','nonfinite','oversize'])
def test_untrusted_json_failures_terminal_and_do_not_call_reader(raw):
    calls=[]
    d=make(retriever=lambda *args:calls.append(args))
    with pytest.raises(DispatchError): d.dispatch(raw)
    assert not calls
    assert d.report()['status']=='blocked' and d.report()['tool_calls']==1
    with pytest.raises(DispatchError): invoke(d,'query_financial_evidence',metrics=['revenue'])
    assert not calls


@pytest.mark.parametrize('tool,args', [('run_sql', {'sql':'SELECT * FROM private'}),
    ('execute_command', {'command':'whoami'}), ('approve_memory', {'approved':True}),
    ('record_completed_challenge', {}), ('query_financial_evidence', {'metrics':['revenue'],'cik':'320193'}),
    ('query_financial_evidence', {'metrics':['revenue'],'as_of':'2099-01-01'}),
    ('query_financial_evidence', {'metrics':['revenue'],'sql':'SELECT 1'}),
    ('query_financial_evidence', {'metrics':['revenue'],'max_tool_calls':999})])
def test_schema_allowlist_rejects_commands_sql_scope_budget_and_host_hooks(tool,args):
    calls=[]; d=make(retriever=lambda *a:calls.append(a))
    with pytest.raises(DispatchError): invoke(d,tool,**args)
    assert not calls and d.report()['conclusion'] is None


def test_reader_scope_mutation_rejected_and_canonical_scope_preserved():
    def reader(request, timeout):
        request.company.cik='320193'
        return [fact()]
    d=make(retriever=reader)
    with pytest.raises(DispatchError): invoke(d,'query_financial_evidence',metrics=['revenue'])
    assert d.report()['scope']==scope()


@pytest.mark.parametrize('bad', [dict(published_at='2026-07-22'), dict(url=URL.replace('1035267','320193')),
    dict(locator=''), dict(period_start='2026-01-01'), dict(document='')])
def test_invalid_returned_batch_is_atomic_including_unselected_metrics(bad):
    def reader(request,timeout):
        return [fact(id='new'),fact(id='invalid',concept='NetIncomeLoss',**bad)]
    d=make(retriever=reader)
    with pytest.raises(DispatchError): invoke(d,'query_financial_evidence',metrics=['revenue'])
    assert [e['id'] for e in d.report()['evidence']]==['revenue']


def test_changed_id_retains_both_versions_and_invalidates_support():
    d=make(retriever=lambda *a:[fact(value=200)])
    register(d); calculate(d); checks(d)
    invoke(d,'query_financial_evidence',metrics=['revenue'])
    report=d.report()
    assert {e['value'] for e in report['evidence']}=={100,200}
    assert report['diagnostic_findings'][0]['classification']=='unresolved'
    assert report['tool_calls']==4
    with pytest.raises(DispatchError): conclude(d)
    assert d.report()['conclusion'] is None


def test_bounded_recheck_retrieves_sec_and_preserves_contrary_facts():
    seen=[]
    def reader(request,timeout):
        seen.append((request.evidence_backend,timeout)); return [fact(value=200,source_mode='live_sec')]
    d=make(retriever=reader)
    register(d,expected_value_decimal='101'); calculate(d); checks(d)
    invoke(d,'request_additional_investigation',claim_id='claim',reason='contradicted_value',evidence_ids=['revenue'])
    assert seen[0][0]=='sec' and 0<seen[0][1]<=45
    assert d.report()['rechecks']==1 and d.report()['tool_calls']==4
    ids=[e['id'] for e in d.report()['evidence']]
    assert len(ids)==2
    with pytest.raises(DispatchError):
        invoke(d,'request_additional_investigation',claim_id='claim',reason='conflicting_values',evidence_ids=ids)
    assert len(seen)==1 and d.report()['status']=='blocked'


def test_failed_read_cannot_conclude_earlier_support_or_leak_exception():
    def reader(*args): raise RuntimeError('private endpoint/token should not escape')
    d=make(retriever=reader); register(d); calculate(d); checks(d)
    with pytest.raises(DispatchError) as error: invoke(d,'query_financial_evidence',metrics=['revenue'])
    assert 'private endpoint' not in str(error.value)
    with pytest.raises(DispatchError): conclude(d)
    assert d.report()['conclusion'] is None


def test_shared_call_budget_not_reset_by_successful_evidence_update():
    d=make(retriever=lambda *a:[fact()],max_tool_calls=3)
    register(d); invoke(d,'query_financial_evidence',metrics=['revenue']); calculate(d)
    with pytest.raises(DispatchError,match='budget'): checks(d)
    assert d.report()['tool_calls']==3


def test_shared_deadline_charges_retrieval_latency_and_rejects_late_facts():
    now=[10.0]; seen=[]
    def reader(request,timeout):
        seen.append(timeout); now[0]+=11; return [fact(id='late')]
    d=make(clock=lambda:now[0],timeout_seconds=10,retriever=reader)
    with pytest.raises(DispatchError,match='deadline'): invoke(d,'query_financial_evidence',metrics=['revenue'])
    assert seen==[10]
    assert [e['id'] for e in d.report()['evidence']]==['revenue']


@pytest.mark.parametrize('changes', [dict(human_review_status='approved'),
    dict(semantic_mapping_status='verified')])
def test_model_cannot_promote_approval_or_semantic_mapping(changes):
    d=make(); register(d); calculate(d); checks(d)
    with pytest.raises(DispatchError): conclude(d,**changes)
    assert d.report()['human_review_status']=='required'


def test_host_challenge_canonical_citations_and_prose_restriction():
    d=make(); register(d); calculate(d); checks(d); conclude(d)
    report=d.report()
    assert any('host_challenge' in e for e in report['trace'])
    assert report['conclusion']['findings'][0]['classification']=='supported'
    assert '900' not in report['conclusion']['briefing']
    assert report['citations'][0]['url']==URL
    assert report['citations'][0]['published_at']=='2026-07-21'
    assert report['live_inference_verified'] is False


@pytest.mark.parametrize('provider', [None,object()])
def test_unavailable_or_text_only_provider_does_not_call_evidence(provider):
    calls=[]; d=make(retriever=lambda *args:calls.append(args))
    report=d.run(provider)
    assert report['error_code']=='structured_provider_unavailable'
    assert report['model_inference_performed'] is False and not calls


def test_protocol_fixture_deadline_and_error_sanitization():
    class Provider:
        structured_deadline_protocol='claimtrace.structured-deadline.v1'
        execution_kind='protocol_fixture'
        def propose(self,**kwargs):
            assert kwargs['deadline']==120
            kwargs['context']['scope']['company']['cik']='320193'
            raise RuntimeError('private provider details')
    d=make(clock=lambda:0)
    report=d.run(Provider())
    assert report['error_code']=='provider_unavailable'
    assert report['scope']==scope() and report['model_inference_performed'] is False
    assert 'private provider' not in json.dumps(report)


def test_report_cannot_mutate_future_authoritative_conclusion():
    d=make(); register(d); calculate(d); checks(d); conclude(d)
    report=d.report()
    report['conclusion']['findings'][0]['classification']='contradicted'
    assert d.report()['conclusion']['findings'][0]['classification']=='supported'


def test_invalid_provider_metadata_not_echoed_into_report():
    class Provider:
        execution_kind='private endpoint/token should not escape'
    report=make().run(Provider())
    assert report['error_code']=='structured_provider_unavailable'
    assert 'private endpoint' not in json.dumps(report)


def test_actual_preserved_text_client_rejected_without_discovery_or_completion(monkeypatch):
    from backend.providers.meterless_client import MeterlessClient
    client=MeterlessClient('http://127.0.0.1:8088','fixture-only-token-not-a-live-credential')
    def forbidden(*args,**kwargs):
        pytest.fail('Text-only client must never be probed or called')
    monkeypatch.setattr(MeterlessClient,'chat',forbidden)
    monkeypatch.setattr(MeterlessClient,'discover',forbidden)
    report=make().run(client)
    assert report['error_code']=='structured_provider_unavailable'


def test_fixture_false_semantic_mapping_remains_unverified_and_requires_review():
    d=make(rows=[fact(id='eps',concept='EarningsPerShareDiluted',unit='USD/shares',value=2.29)])
    register(d,metric='diluted_eps',unit='USD/shares',expected_value_decimal='2.29')
    calculate(d,['eps']);checks(d);conclude(d,ids=['eps'])
    report=d.report()
    assert report['conclusion']['findings'][0]['classification']=='supported'
    assert report['semantic_mapping_status']=='unverified'
    assert report['human_review_status']=='required'


def test_protocol_late_reply_consumes_shared_deadline_without_executing_tool():
    now=[0.0];calls=[]
    class Provider:
        structured_deadline_protocol='claimtrace.structured-deadline.v1'
        execution_kind='protocol_fixture'
        def propose(self,**kwargs):
            assert kwargs['deadline']==5
            now[0]=6
            return json.dumps(dict(tool='query_financial_evidence',arguments=dict(metrics=['revenue'])))
    d=make(clock=lambda:now[0],timeout_seconds=5,retriever=lambda *a:calls.append(a))
    report=d.run(Provider())
    assert report['error_code']=='deadline_exhausted'
    assert not calls and report['conclusion'] is None


def test_repeated_quality_checks_stay_within_shared_call_and_transition_limits():
    d=make();register(d)
    for _ in range(7): checks(d)
    with pytest.raises(DispatchError,match='budget'): checks(d)
    report=d.report()
    assert report['tool_calls']==8 and len(report['trace'])<=10
    assert report['conclusion'] is None
