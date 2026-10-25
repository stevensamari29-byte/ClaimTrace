"""Received JSON precision tests use mocked transport, never live services."""
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend import sources, zetaris
from backend.models import Evidence, InvestigationRequest
from backend.investigation.models import ClaimInput
from backend.investigation.tools import verify
from backend.investigation.memory import HMemMemory, _digest


def request():
    return InvestigationRequest.model_validate({'company': {'name': 'ISRG', 'ticker': 'ISRG', 'cik': '1035267'},
        'fiscal_year': 2026, 'period': 'Q2', 'as_of': '2026-10-24'})


def fact(number='9007199254740993', **changes):
    return Evidence.model_validate({'id': 'revenue', 'document': 'SEC 10-Q',
        'url': 'https://www.sec.gov/Archives/edgar/data/1035267/f.htm',
        'published_at': '2026-07-21', 'period_start': '2026-04-01', 'period_end': '2026-06-30',
        'unit': 'USD', 'value': float(number), 'value_decimal': number, 'concept': 'Revenues',
        'locator': 'Revenue', 'source_mode': 'live_zetaris'} | changes)


def claim(number='9007199254740993', **changes):
    return ClaimInput.model_validate({'id': 'claim', 'text': 'Revenue assertion', 'metric': 'revenue',
        'expected_value_decimal': number, 'unit': 'USD', 'period_start': '2026-04-01',
        'period_end': '2026-06-30'} | changes)


@pytest.mark.parametrize('number', ['9007199254740993', '1.0000000000000001', '0', '-0.00',
                                  '123456789012345678901234567890.1234', '1e-30'])
def test_exact_comparison_retains_received_value(number):
    finding, calculations = verify(claim(number), [fact(number)])
    assert finding['classification'] == 'supported'
    assert Decimal(calculations[-1]['actual_decimal']) == Decimal(number)
    assert Decimal(calculations[-1]['difference_decimal']) == 0
    assert 'exact received' in calculations[-1]['precision']


@pytest.mark.parametrize('a,b', [('9007199254740992', '9007199254740993'),
                               ('1.0000000000000001', '1.00000000000000009')])
def test_conflicts_do_not_collapse_to_float(a, b):
    assert float(a) == float(b)
    finding, _ = verify(claim(a), [fact(a), fact(b, id='other')])
    assert finding['classification'] == 'unresolved'


def test_exact_scaled_units_and_legacy_label():
    finding, calculations = verify(claim('1000000.0000000001'),
        [fact('1.0000000000000001', unit='USD millions'), fact('1000000.0000000001', id='usd')])
    assert finding['classification'] == 'supported'
    _, legacy = verify(claim('1'), [fact('1', value_decimal=None)])
    assert 'legacy float' in legacy[-1]['precision']


@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity', '1e31', '1e-31',
    '12345678901234567890123456789012345', '1_0', ' 1', '1;DROP TABLE x', '<script>'])
def test_invalid_numeric_metadata_rejected(number):
    with pytest.raises(ValidationError):
        fact('1', value_decimal=number)


def test_conflicting_compatible_numeric_value_rejected():
    with pytest.raises(ValidationError):
        fact('1', value=2)


def test_numeric_gateway_strings_are_retained_without_accepting_metadata():
    assert sources.exact_numeric_text('9007199254740993.125') == '9007199254740993.125'
    assert sources.exact_numeric_text('1e+9') == '1e+9'
    for value in ['NaN', '1;DROP TABLE x', ' 1', True, 1.2]:
        assert sources.exact_numeric_text(value) is None


def test_memory_fingerprint_binds_exact_value_and_preserves_legacy():
    memory = HMemMemory()
    first, second = fact(), fact('9007199254740992')
    assert first.value == second.value
    assert memory._sources(request(), [first]) != memory._sources(request(), [second])
    legacy = fact('1', value_decimal=None)
    stable = {k: legacy.model_dump(mode='json').get(k) for k in
              ('id', 'url', 'published_at', 'period_start', 'period_end', 'unit', 'value', 'concept', 'locator', 'source_sha256')}
    assert memory._sources(request(), [legacy])[0]['fingerprint'] == _digest(stable)


class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self): pass
    def iter_bytes(self): yield self.payload


def test_sec_transport_captures_decimal_without_live_request(monkeypatch):
    monkeypatch.setattr(sources, 'sec_user_agent', lambda: 'Mocked identity')
    monkeypatch.setattr(sources.time, 'sleep', lambda _: None)
    monkeypatch.setattr(sources.httpx, 'stream', lambda *a, **k: Response(b'{"val":1.0000000000000001}'))
    payload, _ = sources.get_json('https://data.sec.gov/mock')
    assert payload['val'] == Decimal('1.0000000000000001')


def test_zetaris_transport_and_evidence_keep_gateway_number(monkeypatch):
    row = {'evidence_id': 'revenue', 'cik': '0001035267', 'company_name': 'ISRG', 'ticker': 'ISRG',
        'fiscal_year': 2026, 'fiscal_period': 'Q2', 'reporting_period_end': '2026-06-30', 'document': '10-Q',
        'source_url': fact().url, 'published_at': '2026-07-21', 'period_start': '2026-04-01',
        'period_end': '2026-06-30', 'unit': 'USD', 'value': 'TOKEN', 'concept': 'Revenues', 'locator': 'Revenue'}
    raw = json.dumps({'rows': [row]}).replace('"TOKEN"', '1.0000000000000001').encode()
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def stream(self, *a, **k):
            assert k['json']['sql'].startswith('SELECT ')
            return Response(raw)
    monkeypatch.setattr(zetaris, 'configuration', lambda: {'ZETARIS_BASE_URL': 'https://mock.invalid', 'ZETARIS_API_KEY': 'mock', 'ZETARIS_ORG_ID': '1'})
    monkeypatch.setattr(zetaris.httpx, 'Client', Client)
    monkeypatch.setenv('CLAIMTRACE_ZETARIS_TABLE', 'claimtrace.evidence')
    evidence = zetaris.zetaris_evidence(request())
    assert evidence[0].value_decimal == '1.0000000000000001'


def test_cached_snapshot_retains_decimal_token(monkeypatch, tmp_path):
    snapshot = json.loads(sources.DATA.read_bytes())
    next(row for row in snapshot['records'] if row['duration'] == 'quarter' and row['period_end'] == '2026-06-30')['value'] = 'TOKEN'
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(snapshot).replace('"TOKEN"', '9007199254740993.125'), encoding='utf-8')
    monkeypatch.setattr(sources, 'DATA', path)
    evidence = sources.cached_evidence(request())
    assert any(e.value_decimal == '9007199254740993.125' for e in evidence)


def test_companyfacts_preserves_received_decimal():
    row = {'start': '2026-04-01', 'end': '2026-06-30', 'filed': '2026-07-21', 'fy': 2026,
           'fp': 'Q2', 'form': '10-Q', 'accn': '0001035267-26-000058', 'val': Decimal('1.0000000000000001')}
    payload = {'cik': 1035267, 'facts': {'us-gaap': {'Revenues': {'units': {'USD': [row]}}}}}
    evidence = sources.companyfacts_evidence(request(), payload, 'a'*64, {row['accn']: row['end']})
    assert evidence[0].value_decimal == '1.0000000000000001'
