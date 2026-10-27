"""Diagnostic expectations are declared independently of evaluation execution."""
import json
import subprocess
import sys
from pathlib import Path

from backend.investigation.evaluate import evaluate


def test_guardrails_on_authentic_cached_cases_without_network(monkeypatch):
    def forbidden(*a, **k):
        raise AssertionError('This evaluation must never use the network')
    monkeypatch.setattr('backend.sources.get_json', forbidden)
    report = evaluate()
    cases = {case['case']: case for case in report['cases']}
    expected = {'correct_eps': 'supported', 'wrong_eps': 'contradicted', 'non_gaap': 'incomplete',
                'wrong_period': 'incomplete', 'wrong_unit': 'incomplete',
                'unsupported_qualitative': 'unresolved', 'prepublication': 'incomplete', 'wrong_margin': 'contradicted'}
    assert {key: value['guarded_classification'] for key, value in cases.items()} == expected
    assert report['case_count'] == 8
    assert report['guarded_matches_declared_expectations'] == 8
    assert report['baseline_matches_declared_expectations'] == 4
    assert cases['prepublication']['eligible_evidence_count'] == 0
    assert cases['prepublication']['citations'] == []
    for key in ('non_gaap', 'wrong_period', 'wrong_unit', 'prepublication'):
        assert cases[key]['baseline_classification'] == 'supported'
    citations = cases['correct_eps']['citations']
    assert citations and all(c['source_mode'] == 'cached_sec' and len(c['source_sha256']) == 64 for c in citations)
    assert all(c['url'].startswith('https://www.sec.gov/') and c['published_at'] == '2026-07-21' for c in citations)
    assert 'not an external model' in report['baseline']


def test_cli_writes_finite_utf8_output_and_same_stdout(tmp_path):
    target = tmp_path / 'evaluation.json'
    result = subprocess.run([sys.executable, '-m', 'backend.investigation.evaluate', '--output', str(target)],
        cwd=Path(__file__).parents[2], capture_output=True, text=True, timeout=10, check=True)
    artifact = json.loads(target.read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    assert json.loads(result.stdout) == artifact
    assert artifact['case_count'] == 8 and artifact['guarded_matches_declared_expectations'] == 8
