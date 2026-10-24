import copy
import json
from pathlib import Path

import httpx
import jsonschema
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import InvestigationRequest
from backend.sources import SourceError, companyfacts_evidence
from backend.zetaris import query, result_rows

ROOT = Path(__file__).parents[2]
REQUEST = json.loads((ROOT / 'shared/example.request.json').read_text())
client = TestClient(app)


def test_health():
    assert client.get('/api/health').json()['inference_enabled'] is False


def test_authentic_snapshot_request_response_and_provenance():
    request_schema = json.loads((ROOT / 'shared/request.schema.json').read_text())
    response_schema = json.loads((ROOT / 'shared/response.schema.json').read_text())
    jsonschema.validate(REQUEST, request_schema)
    response = client.post('/api/investigations', json=REQUEST)
    assert response.status_code == 200
    payload = response.json()
    jsonschema.validate(payload, response_schema)
    assert payload['status'] == 'partial'
    assert len(payload['evidence']) == 5
    revenue = next(e for e in payload['evidence'] if e['concept'].startswith('Revenue'))
    assert revenue['value'] == 2892300000
    assert revenue['source_mode'] == 'cached_sec'
    assert revenue['published_at'] == '2026-07-21'
    assert revenue['period_start'] == '2026-04-01'
    assert '#f-' in revenue['url'] and len(revenue['source_sha256']) == 64
    assert payload['calculations'][0]['evidence_ids']
    assert payload['claims'] == [] and payload['findings'] == []


@pytest.mark.parametrize('change', [
    {'period':'six_months'}, {'as_of':'2026-02-30'}, {'as_of':'20261023'},
    {'fiscal_year':'2026'}, {'company':{'name':'','ticker':'ISRG','cik':'0001035267'}},
    {'company':{'name':'Intuitive','ticker':'ISRG','cik':"1' OR 1=1"}},
    {'evidence_backend':'fixture'}, {'unexpected':'value'},
])
def test_malformed_request(change):
    assert client.post('/api/investigations', json={**REQUEST, **change}).status_code == 422


def test_missing_company():
    request = dict(REQUEST)
    del request['company']
    assert client.post('/api/investigations', json=request).status_code == 422


def test_as_of_excludes_later_filing():
    response = client.post('/api/investigations', json={**REQUEST, 'as_of':'2026-07-20'}).json()
    assert response['evidence'] == [] and response['status'] == 'blocked'


def test_zetaris_is_blocked_without_financial_table(monkeypatch):
    monkeypatch.delenv('CLAIMTRACE_ZETARIS_TABLE', raising=False)
    response = client.post('/api/investigations', json={**REQUEST, 'evidence_backend':'zetaris'}).json()
    assert response['status'] == 'blocked' and response['evidence'] == []
    assert 'approval' in ' '.join(response['limitations'])


def test_no_live_sec_without_identifying_agent(monkeypatch,tmp_path):
    monkeypatch.setattr('backend.sources.LOCAL_CONFIG_PATH',tmp_path/'.env.local')
    monkeypatch.delenv('SEC_CONTACT_EMAIL', raising=False)
    response = client.post('/api/investigations', json={**REQUEST, 'period':'Q1'})
    assert response.status_code == 503 and 'SEC_CONTACT_EMAIL' in response.json()['detail']


def fact(start='2026-04-01', end='2026-06-30', **kwargs):
    return dict(start=start,end=end,filed='2026-07-21',fy=2026,fp='Q2',form='10-Q',val=123,accn='0001035267-26-000058',**kwargs)


def test_live_selector_exact_duration_asof_and_comparatives():
    rows = [fact(),fact(start='2026-01-01'),fact(start='2025-04-01',end='2025-06-30')]
    payload = {'cik':1035267,'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':rows}}}}}
    request = InvestigationRequest.model_validate(REQUEST)
    result = companyfacts_evidence(request,payload,'a'*64, {'0001035267-26-000058':'2026-06-30'})
    assert len(result) == 1 and result[0].period_start.isoformat() == '2026-04-01'
    assert result[0].source_mode == 'live_sec'
    request = InvestigationRequest.model_validate({**REQUEST,'as_of':'2026-07-20'})
    assert companyfacts_evidence(request,payload,'a'*64, {'0001035267-26-000058':'2026-06-30'}) == []


def test_annual_not_quarter():
    row = fact(start='2026-01-01', end='2026-12-31')
    row.update(fp='FY', form='10-K', filed='2027-02-01')
    payload = {'cik':1035267,'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[row]}}}}}
    assert companyfacts_evidence(InvestigationRequest.model_validate(REQUEST),payload,'a'*64) == []
    request = InvestigationRequest.model_validate({**REQUEST,'period':'FY','as_of':'2027-03-01'})
    assert len(companyfacts_evidence(request,payload,'a'*64, {'0001035267-26-000058':'2026-12-31'})) == 1


def test_filing_report_date_prevents_comparative_mislabel():
    old = fact(start='2025-04-01',end='2025-06-30')
    payload = {'cik':1035267,'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[old]}}}}}
    report_dates = {'0001035267-26-000058':'2026-06-30'}
    assert companyfacts_evidence(InvestigationRequest.model_validate(REQUEST),payload,'a'*64,report_dates) == []


def test_sec_network_failure_is_sanitized(monkeypatch):
    monkeypatch.setenv('SEC_CONTACT_EMAIL','qa@claimtrace-team.org')
    def fail(*args,**kwargs):
        raise httpx.ConnectError('secret connection details')
    monkeypatch.setattr(httpx,'stream',fail)
    response = client.post('/api/investigations',json={**REQUEST,'period':'Q1'})
    assert response.status_code == 503 and 'secret' not in response.text


@pytest.mark.parametrize('sql',['DELETE FROM secret','SELECT * FROM x; DELETE FROM x'])
def test_sql_write_rejected(sql):
    with pytest.raises(SourceError):
        query(sql)


def test_actual_zetaris_result_shape():
    assert result_rows({'headers':['name'],'data':[['CLAIMTRACE']]}) == [{'name':'CLAIMTRACE'}]


def test_snapshot_canonicalizes_company_identity():
    response = client.post('/api/investigations', json={**REQUEST,'company':{'name':'Wrong Company','ticker':'WRONG','cik':'0001035267'}}).json()
    assert response['company']['name'] == 'Intuitive Surgical, Inc.'
    assert response['company']['ticker'] == 'ISRG'


@pytest.mark.parametrize('malformed',[[], {'cik':1035267,'facts':[]}, {'cik':1035267,'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':None}}}}}])
def test_malformed_sec_data_is_sanitized(monkeypatch, malformed):
    monkeypatch.setenv('CLAIMTRACE_SEC_MODE','live')
    submissions={'cik':1035267,'name':'Intuitive Surgical, Inc.','tickers':['ISRG'],'filings':{'recent':{'accessionNumber':['0001035267-26-000058'],'reportDate':['2026-06-30']}}}
    responses=iter([(malformed,'a'*64),(submissions,'b'*64)])
    monkeypatch.setattr('backend.sources.get_json', lambda url:next(responses))
    response=client.post('/api/investigations',json=REQUEST)
    assert response.status_code == 503
    assert 'invalid' in response.json()['detail']


@pytest.mark.parametrize('change',[{'source_url':'javascript:alert(1)'},{'period_start':'2026-07-01','period_end':'2026-01-01'},{'period_start':'2026-01-01'}])
def test_invalid_zetaris_row_is_blocked(monkeypatch,change):
    monkeypatch.setenv('CLAIMTRACE_ZETARIS_TABLE','claimtrace.sec_financial_evidence')
    row={'evidence_id':'test','cik':'0001035267','company_name':'Intuitive Surgical, Inc.','ticker':'ISRG','fiscal_year':2026,'fiscal_period':'Q2','reporting_period_end':'2026-06-30','document':'SEC 10-Q','source_url':'https://www.sec.gov/Archives/a.htm','published_at':'2026-07-21','period_start':'2026-04-01','period_end':'2026-06-30','unit':'USD','value':123,'concept':'NetIncomeLoss','locator':'a'}
    monkeypatch.setattr('backend.zetaris.query',lambda sql:{'data':[{**row,**change}]})
    response=client.post('/api/investigations',json={**REQUEST,'evidence_backend':'zetaris'}).json()
    assert response['status']=='blocked' and response['evidence']==[]


def test_runtime_factory_disabled_by_default(monkeypatch):
    from backend.providers.nightshift import configured_runtime
    monkeypatch.delenv('NIGHTSHIFT_INFERENCE_ENABLED',raising=False)
    with pytest.raises(ValueError,match='disabled'):
        configured_runtime()


@pytest.mark.parametrize('classification',['supported','contradicted','incomplete','unresolved'])
def test_structured_claim_and_finding_schema(classification):
    schema=json.loads((ROOT/'shared/response.schema.json').read_text())
    response=json.loads((ROOT/'shared/example.response.json').read_text())
    evidence=response['evidence'][0]
    response['claims']=[{'id':'claim-1','text':'Schema-validation example only','source_url':evidence['url']}]
    response['findings']=[{'id':'finding-1','claim_id':'claim-1','classification':classification,
                           'evidence_ids':[evidence['id']],'explanation':'Schema fixture; no investigation result is claimed.'}]
    jsonschema.validate(response,schema)
    from backend.models import InvestigationResponse
    assert InvestigationResponse.model_validate(response).findings[0].classification==classification


@pytest.mark.parametrize('change',[{'classification':'verified'}, {'evidence_ids':None}, {'claim_id':None}])
def test_finding_schema_rejects_invalid_classification_or_citation_types(change):
    schema=json.loads((ROOT/'shared/response.schema.json').read_text())
    response=json.loads((ROOT/'shared/example.response.json').read_text())
    response['findings']=[{'id':'f1','claim_id':'c1','classification':'supported','evidence_ids':[],
                           'explanation':'Schema fixture',**change}]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(response,schema)


def test_finding_schema_requires_citation_field():
    schema=json.loads((ROOT/'shared/response.schema.json').read_text())
    response=json.loads((ROOT/'shared/example.response.json').read_text())
    response['findings']=[{'id':'f1','claim_id':'c1','classification':'unresolved','explanation':'No evidence resolved yet'}]
    with pytest.raises(jsonschema.ValidationError,match='evidence_ids'):
        jsonschema.validate(response,schema)


@pytest.mark.parametrize('contact',['owner@example.com','owner@example.org','owner@example.net','owner@host.invalid','owner@host.test','placeholder@claimtrace-team.org','YOUR_EMAIL@claimtrace-team.org','123+owner@users.noreply.github.com','noreply@claimtrace-team.org','ClaimTrace owner@claimtrace-team.org','owner@claimtrace-team.org extra'])
def test_placeholder_sec_contact_never_makes_request(monkeypatch,contact):
    from backend.sources import get_json
    monkeypatch.setenv('SEC_CONTACT_EMAIL',contact)
    def forbidden(*args,**kwargs):
        pytest.fail('Placeholder SEC contact must not make a network request')
    monkeypatch.setattr(httpx,'stream',forbidden)
    with pytest.raises(SourceError,match='owner-approved'):
        get_json('https://data.sec.gov/test')


def test_private_local_sec_config_and_environment_precedence(monkeypatch,tmp_path,capsys):
    from backend.sources import sec_user_agent
    private_config=tmp_path/'.env.local'
    private_config.write_text('SEC_CONTACT_EMAIL="owner@claimtrace-team.org"\nUNRELATED_SECRET=never-load-this\n')
    monkeypatch.setattr('backend.sources.LOCAL_CONFIG_PATH',private_config)
    monkeypatch.delenv('SEC_CONTACT_EMAIL',raising=False)
    assert sec_user_agent()=='ClaimTrace Hackathon Team owner@claimtrace-team.org'
    monkeypatch.setenv('SEC_CONTACT_EMAIL','override@claimtrace-team.org')
    assert sec_user_agent().endswith('override@claimtrace-team.org')
    assert capsys.readouterr().out=='' and capsys.readouterr().err==''


def test_real_shaped_sec_identity_injected_mock_request(monkeypatch,tmp_path):
    from backend.sources import get_json
    monkeypatch.setattr('backend.sources.LOCAL_CONFIG_PATH',tmp_path/'.env.local')
    monkeypatch.setenv('SEC_CONTACT_EMAIL','qa@claimtrace-team.org')
    calls=[]
    class Response:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def raise_for_status(self): pass
        def iter_bytes(self): yield b'{"verified_mock":true}'
    def stream(*args,**kwargs):
        calls.append(kwargs)
        return Response()
    monkeypatch.setattr(httpx,'stream',stream)
    payload,digest=get_json('https://data.sec.gov/test')
    assert payload=={'verified_mock':True} and len(digest)==64
    assert calls[0]['headers']['User-Agent']=='ClaimTrace Hackathon Team qa@claimtrace-team.org'
    assert len(calls)==1


def test_raw_user_agent_cannot_bypass_missing_private_contact(monkeypatch,tmp_path):
    from backend.sources import sec_user_agent
    monkeypatch.setattr('backend.sources.LOCAL_CONFIG_PATH',tmp_path/'.env.local')
    monkeypatch.delenv('SEC_CONTACT_EMAIL',raising=False)
    monkeypatch.setenv('SEC_USER_AGENT','ClaimTrace Hackathon Team qa@claimtrace-team.org')
    with pytest.raises(SourceError,match='SEC_CONTACT_EMAIL'):
        sec_user_agent()
