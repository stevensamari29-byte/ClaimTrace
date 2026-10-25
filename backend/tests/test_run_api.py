"""Local HTTP/storage tests. Injected runners are labeled fixtures, not inference."""
import copy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.investigation import run_investigation
from backend.run_api import router, get_store, get_runner, get_memory
from backend.run_store import RunStore, ReviewConflict, RunIntegrityError

ROOT = Path(__file__).parents[2]
INPUT = json.loads((ROOT / 'shared/example.investigation-input.json').read_text())


def fixture_report(data, **kwargs):
    return {'schema_version': 'claimtrace.investigation.v1', 'run_id': str(uuid4()),
            'request': data.request.model_dump(mode='json'),
            'original_claims': [claim.model_dump(mode='json') for claim in data.claim_inputs],
            'evidence': [], 'trace': [], 'findings': [], 'calculations': [],
            'status': 'blocked', 'human_review_status': 'required',
            'execution_mode': 'incomplete_no_live_model', 'model_inference_performed': False,
            'limitations': ['Labeled injected runner fixture; no service call.']}


@pytest.fixture
def setup(tmp_path):
    app = FastAPI()
    app.include_router(router)
    store = RunStore(tmp_path / 'runs.sqlite3')
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[get_runner] = lambda: fixture_report
    app.dependency_overrides[get_memory] = lambda: None
    return app, TestClient(app), store


def create(client):
    response = client.post('/api/investigation-runs', json=INPUT)
    assert response.status_code == 200, response.text
    return response.json()


def review_body(run, **changes):
    return {'report_digest': run['report_digest'], 'expected_review_version': run['review']['version'],
            'decision': 'approved', 'comment': 'Reviewed cited evidence.'} | changes


def test_create_read_restart_and_review_history(setup):
    _, client, store = setup
    run = create(client)
    assert run['schema_version'] == 'claimtrace.run.v1'
    assert run['run_id'] == run['report']['run_id']
    assert run['review'] == {'status': 'required', 'version': 0, 'history': []}
    assert len(run['report_digest']) == 64
    assert client.get('/api/investigation-runs/' + run['run_id']).json() == run
    response = client.post('/api/investigation-runs/' + run['run_id'] + '/review', json=review_body(run))
    assert response.status_code == 200
    reviewed = response.json()
    assert reviewed['report'] == run['report']
    assert reviewed['report']['human_review_status'] == 'required'  # no forged controller/memory approval
    assert reviewed['review']['status'] == 'approved'
    assert reviewed['review']['version'] == 1
    assert reviewed['review']['history'][0]['reviewer'] == 'local-human'
    assert RunStore(store.path).get(run['run_id']) == reviewed
    rejection = client.post('/api/investigation-runs/' + run['run_id'] + '/review', json=review_body(reviewed, decision='rejected')).json()
    assert rejection['review']['status'] == 'rejected'
    assert [item['decision'] for item in rejection['review']['history']] == ['approved', 'rejected']


def test_stale_replay_and_cross_report_fail_without_overwriting(setup):
    _, client, _ = setup
    first, second = create(client), create(client)
    route = '/api/investigation-runs/' + first['run_id'] + '/review'
    assert client.post(route, json=review_body(second)).status_code == 409
    assert client.post(route, json=review_body(first)).status_code == 200
    assert client.post(route, json=review_body(first, decision='rejected')).status_code == 409
    saved = client.get('/api/investigation-runs/' + first['run_id']).json()
    assert saved['review']['status'] == 'approved'
    assert len(saved['review']['history']) == 1


def test_concurrent_reviews_use_atomic_version_check(setup):
    _, client, store = setup
    run = create(client)
    def write(decision):
        try:
            store.review(run['run_id'], run['report_digest'], 0, decision)
            return 'saved'
        except ReviewConflict:
            return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ['approved', 'rejected']))
    assert sorted(results) == ['conflict', 'saved']
    assert store.get(run['run_id'])['review']['version'] == 1


@pytest.mark.parametrize('origin', ['https://evil.example', 'null', 'http://127.0.0.1.evil.example:5173', 'http://localhost:9000', 'http://user@localhost:5173', 'http://localhost:5173/path'])
def test_external_origin_rejected_before_execution(setup, origin):
    app, client, _ = setup
    app.dependency_overrides[get_runner] = lambda: lambda *a, **k: pytest.fail('Blocked origin executed')
    assert client.post('/api/investigation-runs', json=INPUT, headers={'Origin': origin}).status_code == 403


def test_host_guard_and_valid_development_origin(setup):
    _, client, _ = setup
    assert client.post('/api/investigation-runs', json=INPUT, headers={'Host': 'evil.example'}).status_code == 403
    assert client.post('/api/investigation-runs', json=INPUT, headers={'Origin': 'http://127.0.0.1:5173'}).status_code == 200


@pytest.mark.parametrize('patch', [{'sql': 'SELECT *'}, {'memory_dir': '/private'}, {'actor': 'admin'}, {'provider': 'invented'}])
def test_unknown_and_privileged_fields_rejected(setup, patch):
    _, client, _ = setup
    response = client.post('/api/investigation-runs', json=INPUT | patch)
    assert response.status_code == 422
    assert '/private' not in response.text


def test_json_limits_and_duplicate_keys(setup):
    _, client, _ = setup
    assert client.post('/api/investigation-runs', content='{}').status_code == 415
    assert client.post('/api/investigation-runs', content='x' * 65_537, headers={'Content-Type': 'application/json'}).status_code == 413
    assert client.post('/api/investigation-runs', content='{"request":{},"request":{}}', headers={'Content-Type': 'application/json'}).status_code == 422
    assert client.post('/api/investigation-runs', content='{"value":NaN}', headers={'Content-Type': 'application/json'}).status_code == 422
    assert client.post('/api/investigation-runs', content='[' * 1100 + '0' + ']' * 1100, headers={'Content-Type': 'application/json'}).status_code == 422


@pytest.mark.parametrize('patch', [{'expected_review_version': True}, {'expected_review_version': 0.0}, {'expected_review_version': -1}, {'decision': 'complete'}, {'reviewer': 'admin'}, {'comment': 'x' * 2001}])
def test_review_payload_strict_and_cannot_choose_actor(setup, patch):
    _, client, _ = setup
    run = create(client)
    response = client.post('/api/investigation-runs/' + run['run_id'] + '/review', json=review_body(run, **patch))
    assert response.status_code == 422
    assert client.get('/api/investigation-runs/' + run['run_id']).json()['review']['version'] == 0


def test_missing_malformed_and_tampered_runs(setup):
    _, client, store = setup
    assert client.get('/api/investigation-runs/' + str(uuid4())).status_code == 404
    assert client.get('/api/investigation-runs/not-a-uuid').status_code == 422
    run = create(client)
    with sqlite3.connect(store.path) as connection:
        connection.execute('UPDATE investigation_runs SET report_json=? WHERE run_id=?', ('{}', run['run_id']))
    assert client.get('/api/investigation-runs/' + run['run_id']).status_code == 503
    with pytest.raises(RunIntegrityError):
        store.get(run['run_id'])


def test_runner_errors_and_scope_mutation_fail_closed(setup):
    app, client, _ = setup
    def broken(*args, **kwargs):
        raise RuntimeError('private fixture detail')
    app.dependency_overrides[get_runner] = lambda: broken
    response = client.post('/api/investigation-runs', json=INPUT)
    assert response.status_code == 503
    assert 'private fixture detail' not in response.text
    def wrong_scope(data, **kwargs):
        report = fixture_report(data)
        report['request']['period'] = 'Q4'
        return report
    app.dependency_overrides[get_runner] = lambda: wrong_scope
    assert client.post('/api/investigation-runs', json=INPUT).status_code == 503


def test_real_controller_with_authentic_cached_sec(setup, monkeypatch):
    app, client, _ = setup
    monkeypatch.delenv('CLAIMTRACE_SEC_MODE', raising=False)
    app.dependency_overrides[get_runner] = lambda: run_investigation
    payload = copy.deepcopy(INPUT)
    payload['request']['evidence_backend'] = 'sec'
    response = client.post('/api/investigation-runs', json=payload)
    assert response.status_code == 200, response.text
    report = response.json()['report']
    assert report['execution_mode'] == 'incomplete_no_live_model'
    assert report['model_inference_performed'] is False
    assert report['findings'][0]['classification'] == 'supported'
    assert report['trace'] and report['citations']
    assert all(item['source_mode'] == 'cached_sec' for item in report['evidence'])
    assert all(item['published_at'] <= report['request']['as_of'] for item in report['evidence'])
