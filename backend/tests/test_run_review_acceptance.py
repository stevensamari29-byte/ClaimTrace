"""Independent run/review acceptance using authentic cached SEC evidence.

API fixtures replace transport/storage dependencies only. No live inference or
human approval is established by these isolated automated review transitions.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.investigation import run_investigation
from backend.investigation.models import InvestigationInput
from backend.run_api import router, get_store, get_runner, get_memory
from backend.run_store import RunStore, ReviewConflict, report_digest
from backend.sources import cached_evidence

ROOT = Path(__file__).parents[2]
BASE = json.loads((ROOT / 'shared/example.investigation-input.json').read_text())


def authentic_retriever(request, timeout):
    rows = cached_evidence(request)
    assert rows is not None, 'This evaluation is restricted to the authentic ISRG snapshot'
    return rows


def actual_cached_runner(data, memory=None):
    return run_investigation(data, retriever=authentic_retriever, memory=memory)


@pytest.fixture
def local_api(tmp_path):
    app = FastAPI()
    app.include_router(router)
    store = RunStore(tmp_path / 'isolated-investigations.sqlite3')
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_runner] = lambda: actual_cached_runner
    app.dependency_overrides[get_memory] = lambda: None
    with TestClient(app) as client:
        yield app, client, store


def new_run(client, payload=None):
    response = client.post('/api/investigation-runs', json=payload or deepcopy(BASE))
    assert response.status_code == 200, response.text
    return response.json()


def review(run, **patch):
    return {'report_digest': run['report_digest'], 'expected_review_version': run['review']['version'],
            'decision': 'approved', 'comment': 'Isolated automated review transition; not human acceptance.'} | patch


def test_real_controller_report_is_immutable_and_review_survives_fresh_app(local_api):
    app, client, store = local_api
    run = new_run(client)
    report = run['report']
    assert report['model_inference_performed'] is False
    assert report['execution_mode'] == 'incomplete_no_live_model'
    assert report['human_review_status'] == 'required'
    assert report['findings'][0]['classification'] == 'supported'
    assert all(e['source_mode'] == 'cached_sec' for e in report['evidence'])
    assert {'validate', 'retrieve', 'verify', 'challenge', 'conclude'} <= {e['state'] for e in report['trace']}
    assert report_digest(report) == run['report_digest']
    saved = client.post(f"/api/investigation-runs/{run['run_id']}/review", json=review(run)).json()
    assert saved['review']['status'] == 'approved'
    assert saved['review']['history'][0]['reviewer'] == 'local-human'
    assert saved['report'] == report
    assert saved['report']['human_review_status'] == 'required'
    second = FastAPI()
    second.include_router(router)
    second.dependency_overrides[get_store] = lambda: RunStore(store.path)
    with TestClient(second) as restarted:
        assert restarted.get(f"/api/investigation-runs/{run['run_id']}").json() == saved
    rejection = client.post(f"/api/investigation-runs/{run['run_id']}/review", json=review(saved, decision='rejected')).json()
    assert [item['decision'] for item in rejection['review']['history']] == ['approved', 'rejected']
    assert rejection['report_digest'] == run['report_digest']
    assert rejection['report'] == report


def test_wrong_digest_wrong_run_and_replay_never_change_saved_decision(local_api):
    _, client, _ = local_api
    one, two = new_run(client), new_run(client)
    route = f"/api/investigation-runs/{one['run_id']}/review"
    for body in [review(one, report_digest='0' * 64), review(two), review(one, expected_review_version=1)]:
        assert client.post(route, json=body).status_code == 409
    assert client.post(route, json=review(one)).status_code == 200
    assert client.post(route, json=review(one, decision='rejected')).status_code == 409
    current = client.get(f"/api/investigation-runs/{one['run_id']}").json()
    assert current['review']['status'] == 'approved'
    assert current['review']['version'] == 1
    assert client.get(f"/api/investigation-runs/{two['run_id']}").json()['review']['version'] == 0


def test_separate_store_instances_concurrently_compare_and_set(local_api):
    _, client, store = local_api
    run = new_run(client)
    def save(decision):
        try:
            RunStore(store.path).review(run['run_id'], run['report_digest'], 0, decision)
            return 'saved'
        except ReviewConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ['approved', 'rejected'])) == ['conflict', 'saved']
    final = RunStore(store.path).get(run['run_id'])
    assert final['review']['version'] == 1
    assert len(final['review']['history']) == 1


def test_tampered_report_or_history_fails_closed(local_api):
    _, client, store = local_api
    run = new_run(client)
    with sqlite3.connect(store.path) as connection:
        raw = connection.execute('SELECT report_json FROM investigation_runs WHERE run_id=?', (run['run_id'],)).fetchone()[0]
        changed = json.loads(raw)
        changed['findings'][0]['classification'] = 'unresolved'
        connection.execute('UPDATE investigation_runs SET report_json=? WHERE run_id=?', (json.dumps(changed), run['run_id']))
    assert client.get(f"/api/investigation-runs/{run['run_id']}").status_code == 503
    assert client.post(f"/api/investigation-runs/{run['run_id']}/review", json=review(run)).status_code == 503
    other = new_run(client)
    saved = client.post(f"/api/investigation-runs/{other['run_id']}/review", json=review(other)).json()
    with sqlite3.connect(store.path) as connection:
        connection.execute('UPDATE investigation_reviews SET version=3 WHERE run_id=?', (other['run_id'],))
    assert client.get(f"/api/investigation-runs/{other['run_id']}").status_code == 503


@pytest.mark.parametrize('headers', [
    {'Origin': 'https://untrusted.example'}, {'Origin': 'null'}, {'Origin': 'http://localhost:5173.evil.example'},
    {'Origin': 'http://localhost:5173/path'}, {'Host': 'localhost.evil.example'}, {'Host': 'localhost:9000'},
])
def test_local_boundary_prevents_reader_or_review_execution(local_api, headers):
    app, client, _ = local_api
    app.dependency_overrides[get_runner] = lambda: lambda *args, **kwargs: pytest.fail('Origin/host reached reader')
    assert client.post('/api/investigation-runs', json=BASE, headers=headers).status_code == 403


@pytest.mark.parametrize('patch', [
    {'provider': 'nightshift'}, {'sql': 'SELECT 1'}, {'actor': 'admin'}, {'memory_dir': 'private-path'},
])
def test_browser_cannot_select_privileged_execution_settings(local_api, patch):
    _, client, _ = local_api
    response = client.post('/api/investigation-runs', json=BASE | patch)
    assert response.status_code == 422
    assert 'private-path' not in response.text


def test_validation_and_runtime_errors_are_sanitized(local_api):
    app, client, _ = local_api
    assert client.post('/api/investigation-runs', content='{}', headers={'Content-Type': 'text/plain'}).status_code == 415
    assert client.post('/api/investigation-runs', content='{"request":{},"request":{}}', headers={'Content-Type': 'application/json'}).status_code == 422
    assert client.post('/api/investigation-runs', content='x' * 65537, headers={'Content-Type': 'application/json'}).status_code == 413
    def bad(*args, **kwargs):
        raise RuntimeError('PRIVATE_TEST_SENTINEL')
    app.dependency_overrides[get_runner] = lambda: bad
    response = client.post('/api/investigation-runs', json=BASE)
    assert response.status_code == 503
    assert 'PRIVATE_TEST_SENTINEL' not in response.text
    assert client.get('/api/investigation-runs/not-a-uuid').status_code == 422
    assert client.get(f'/api/investigation-runs/{uuid4()}').status_code == 404


CASES = [
    ('supported_eps', {}, {}, 'supported'),
    ('wrong_eps', {'expected_value_decimal': '9.99'}, {}, 'contradicted'),
    ('non_gaap', {'accounting_basis': 'non-GAAP'}, {}, 'incomplete'),
    ('wrong_period', {'period_start': '2026-01-01', 'period_end': '2026-03-31'}, {}, 'incomplete'),
    ('wrong_unit', {'unit': 'EUR'}, {}, 'incomplete'),
    ('unsupported_causal', {'metric': 'unsupported', 'expected_value_decimal': None, 'text': 'Human challenge: performance was caused by an acquisition.'}, {}, 'unresolved'),
    ('before_publication', {}, {'as_of': '2026-07-20'}, 'incomplete'),
    ('wrong_margin', {'metric': 'net_margin', 'expected_value_decimal': '50', 'unit': '%'}, {}, 'contradicted'),
]


def evaluate_cached_cases():
    results = []
    for name, claim_patch, request_patch, expected in CASES:
        payload = deepcopy(BASE)
        payload['claim_inputs'][0].update(claim_patch)
        payload['request'].update(request_patch)
        report = run_investigation(payload, retriever=authentic_retriever)
        finding = report['findings'][0]
        cited_ids = {item['evidence_id'] for item in report['citations']}
        eligible = all(item['published_at'] <= payload['request']['as_of'] for item in report['evidence'])
        resolved = set(finding['evidence_ids']) <= cited_ids
        results.append({'case': name, 'expected': expected, 'observed': finding['classification'],
                        'classification_matched': finding['classification'] == expected,
                        'report_status': report['status'], 'evidence_count': len(report['evidence']),
                        'citation_ids_resolve': resolved, 'publication_cutoff_met': eligible,
                        'source_modes': sorted({e['source_mode'] for e in report['evidence']}),
                        'trace_states': [event['state'] for event in report['trace']],
                        'model_inference_performed': report['model_inference_performed']})
    return results


@pytest.mark.parametrize('case', CASES, ids=[case[0] for case in CASES])
def test_authentic_cached_financial_evaluation(case):
    name, claim_patch, request_patch, expected = case
    payload = deepcopy(BASE)
    payload['claim_inputs'][0].update(claim_patch)
    payload['request'].update(request_patch)
    report = run_investigation(payload, retriever=authentic_retriever)
    assert report['findings'][0]['classification'] == expected
    assert report['model_inference_performed'] is False
    assert set(report['findings'][0]['evidence_ids']) <= {c['evidence_id'] for c in report['citations']}
    assert all(e['source_mode'] == 'cached_sec' for e in report['evidence'])
    if name == 'before_publication':
        assert report['evidence'] == [] and report['status'] == 'blocked'
    if expected != 'supported':
        assert 'recheck' in {event['state'] for event in report['trace']}


def test_deep_json_is_sanitized_before_execution(local_api):
    app, client, _ = local_api
    app.dependency_overrides[get_runner] = lambda: lambda *args, **kwargs: pytest.fail('Nested invalid JSON reached runner')
    response = client.post('/api/investigation-runs', content='[' * 2000 + '0' + ']' * 2000, headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert 'RecursionError' not in response.text


def test_real_hmem_recall_runs_inside_cached_controller_api(local_api, tmp_path):
    from backend.investigation.memory import HMemMemory
    app, client, _ = local_api
    app.dependency_overrides[get_memory] = lambda: HMemMemory(root=tmp_path / 'isolated-real-hmem', scope_id='local-cli', actor='local-human')
    run = new_run(client)
    recalls = [event for event in run['report']['trace'] if event['state'] == 'recall']
    assert recalls and recalls[0]['ok'] is True
    assert recalls[0]['count'] == 0
    assert run['report']['reviewed_memory'] == []
    assert run['report']['findings'][0]['classification'] == 'supported'


@pytest.mark.parametrize('mutation,expected_reason', [('blank_locator', 'missing_source_locator'), ('wrong_issuer', 'issuer_not_verified_in_document_url')])
def test_ineligible_citations_cannot_support_claims(local_api, mutation, expected_reason):
    app, client, _ = local_api
    def rejected_source_runner(data, memory=None):
        def altered(request, timeout):
            rows = [row.model_dump(mode='json') for row in authentic_retriever(request, timeout)]
            for row in rows:
                if mutation == 'blank_locator':
                    row['locator'] = ' '
                else:
                    row['url'] = row['url'].replace('/1035267/', '/789019/')
            return rows
        return run_investigation(data, retriever=altered)
    app.dependency_overrides[get_runner] = lambda: rejected_source_runner
    run = new_run(client)
    assert run['report']['evidence'] == []
    assert run['report']['citations'] == []
    assert run['report']['findings'][0]['classification'] == 'incomplete'
    assert expected_reason in {item['reason'] for item in run['report']['rejected_evidence']}
