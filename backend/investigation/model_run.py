"""Standalone opt-in model dispatcher; default invocation performs no network."""
import argparse
from datetime import date
import json
from pathlib import Path

from backend.models import InvestigationRequest
from backend.providers.meterless_client import strict_json
from backend.providers.nightshift import configured_structured_runtime
from .dispatcher import RestrictedDispatcher
from .memory import HMemMemory
from .model_contracts import TrustedDisclosure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', help='Trusted local InvestigationRequest JSON file')
    parser.add_argument('--disclosures', help='Trusted local primary SEC disclosures JSON list')
    parser.add_argument('--live', action='store_true', help='Requires authorized host and explicit server enablement')
    args = parser.parse_args(argv)
    try:
        def load(path):
            with Path(path).open('rb') as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError
            return strict_json(raw)
        request = InvestigationRequest.model_validate(load(args.request))
        disclosures = []
        if args.disclosures:
            rows = load(args.disclosures)
            if not isinstance(rows, list) or len(rows) > 3:
                raise ValueError
            for row in rows:
                row = dict(row)
                for key in ('published_at', 'period_start', 'period_end'):
                    row[key] = date.fromisoformat(row[key])
                disclosures.append(TrustedDisclosure(**row))
        dispatcher = RestrictedDispatcher(request, disclosures=disclosures, memory=HMemMemory())
        provider = None
        if args.live:
            try:
                provider = configured_structured_runtime(enabled=True)
            except Exception:
                pass
        result = dispatcher.run(provider)
        print(json.dumps(result, allow_nan=False))
        return 2 if result['status'] == 'blocked' else 0
    except Exception:
        print(json.dumps({'status': 'blocked', 'error_code': 'invalid_local_model_run_input',
                          'live_inference_verified': False, 'human_review_status': 'required'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
