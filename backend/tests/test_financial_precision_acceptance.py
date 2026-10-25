"""Independent precision acceptance using explicit synthetic financial fixtures."""
from decimal import Decimal
import hashlib
import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from backend.models import Evidence, InvestigationRequest
from backend.investigation.models import ClaimInput
from backend.investigation.tools import verify
from backend.investigation.memory import HMemMemory
from backend.sources import get_json, exact_numeric_text
from backend import zetaris

class JsonResponse:
    def __init__(self, raw): self.raw = raw
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self): pass
    def iter_bytes(self): yield self.raw

class IndependentFinancialPrecisionAcceptance(unittest.TestCase):
    def evidence(self, number, *, exact=True, id='qa-fact'):
        row = dict(id=id, document='Synthetic precision fixture',
            url='https://www.sec.gov/Archives/edgar/data/1035267/qa-fixture.htm',
            published_at='2026-07-22', period_start='2026-04-01', period_end='2026-06-30',
            unit='USD', value=float(number), concept='Revenues', locator='synthetic-test-only',
            source_mode='cached_sec', source_sha256=None)
        if exact: row['value_decimal'] = number
        return Evidence(**row)

    def claim(self, number):
        return ClaimInput(id='qa-claim', text='Synthetic precision assertion', metric='revenue',
            expected_value_decimal=number, unit='USD', period_start='2026-04-01', period_end='2026-06-30')

    def request(self):
        return InvestigationRequest(company={'name':'Fixture issuer','ticker':'ISRG','cik':'1035267'},
            fiscal_year=2026, period='Q2', as_of='2026-07-31')

    def test_large_received_values_collapsing_to_same_float_still_contradict(self):
        actual, claimed = '9007199254740993', '9007199254740992'
        self.assertEqual(float(actual), float(claimed))
        finding, calculations = verify(self.claim(claimed), [self.evidence(actual)])
        self.assertEqual(finding['classification'], 'contradicted')
        self.assertEqual(Decimal(calculations[-1]['difference_decimal']), Decimal(1))

    def test_collapsed_conflicting_sources_are_unresolved(self):
        facts = [self.evidence('9007199254740992', id='first'), self.evidence('9007199254740993', id='second')]
        self.assertEqual(facts[0].value, facts[1].value)
        finding, calculations = verify(self.claim('9007199254740992'), facts)
        self.assertEqual(finding['classification'], 'unresolved')
        self.assertEqual(set(finding['evidence_ids']), {'first','second'})
        self.assertEqual(calculations, [])

    def test_exact_fractional_digits_survive_scaling_and_subtraction(self):
        number = '12345678901234567890.12345678901234'
        finding, calculations = verify(self.claim('12345678901234567890.12345678901233'), [self.evidence(number)])
        self.assertEqual(finding['classification'], 'contradicted')
        self.assertEqual(Decimal(calculations[-1]['difference_decimal']), Decimal('0.00000000000001'))

    def test_invalid_exact_values_cannot_override_legacy_value(self):
        for exact in ('NaN', 'Infinity', '1e31', '1e-31', '1.2345678901234567890123456789012345', '999'):
            with self.subTest(exact=exact), self.assertRaises(ValidationError):
                self.evidence('1').model_validate({**self.evidence('1').model_dump(), 'value_decimal':exact})

    def test_legacy_field_remains_numeric_and_precision_limitation_explicit(self):
        fact = self.evidence('2.29', exact=False)
        self.assertIsInstance(fact.model_dump(mode='json')['value'], float)
        self.assertIsNone(fact.value_decimal)
        result, calculations = verify(self.claim('2.29'), [fact])
        self.assertEqual(result['classification'], 'supported')
        self.assertIn('legacy float', calculations[-1]['precision'])
        self.assertIsNone(exact_numeric_text(2.29))

    def test_sec_json_transport_retains_received_decimal_token(self):
        raw = b'{"large":9007199254740993,"fraction":1.234567890123456789012345678901234}'
        with patch('backend.sources.sec_user_agent', return_value='fixture-identity'), patch('backend.sources.httpx.stream', return_value=JsonResponse(raw)), patch('backend.sources.time.sleep'):
            payload, digest = get_json('https://data.sec.gov/qa-fixture')
        self.assertEqual(str(payload['large']), '9007199254740993')
        self.assertIsInstance(payload['fraction'], Decimal)
        self.assertEqual(str(payload['fraction']), '1.234567890123456789012345678901234')
        self.assertEqual(digest, hashlib.sha256(raw).hexdigest())

    def test_zetaris_json_transport_retains_received_decimal_token(self):
        raw = b'{"rows":[{"value":9007199254740993.125}]}'
        class Client:
            def __init__(self, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def stream(self, *args, **kwargs): return JsonResponse(raw)
        with patch('backend.zetaris.configuration', return_value={'ZETARIS_BASE_URL':'https://fixture.invalid', 'ZETARIS_API_KEY':'fixture', 'ZETARIS_ORG_ID':'1'}), patch('backend.zetaris.httpx.Client', Client):
            value = zetaris.query('SELECT value FROM approved_fixture')['rows'][0]['value']
        self.assertIsInstance(value, Decimal)
        self.assertEqual(str(value), '9007199254740993.125')

    def test_old_memory_fingerprint_preserved_and_exact_changes_invalidate(self):
        memory = HMemMemory()
        old = self.evidence('9007199254740992', exact=False)
        source = memory._sources(self.request(), [old])[0]
        row = old.model_dump(mode='json')
        stable = {key:row.get(key) for key in ('id','url','published_at','period_start','period_end','unit','value','concept','locator','source_sha256')}
        expected = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(source['fingerprint'], expected)
        first = memory._sources(self.request(), [self.evidence('9007199254740992')])[0]
        second = memory._sources(self.request(), [self.evidence('9007199254740993')])[0]
        self.assertNotEqual(first['fingerprint'], second['fingerprint'])
        self.assertNotEqual(first['fingerprint'], source['fingerprint'])

    def test_gateway_numeric_strings_are_retained_without_promoting_unsafe_text(self):
        for text in ('9007199254740993.125', '2.29', '-1.25e6'):
            with self.subTest(text=text):
                self.assertEqual(exact_numeric_text(text), text)
        for text in ('NaN', 'Infinity', ' 2.29 ', 'SELECT 1', '', '1;DROP TABLE'):
            with self.subTest(unsafe=text):
                self.assertIsNone(exact_numeric_text(text))
