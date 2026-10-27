"""Explicit NVIDIA hosted acceptance, independent of React; default is no network."""
import argparse
from datetime import date
import json
from pathlib import Path
import re

from backend.models import InvestigationRequest
from backend.providers.meterless_client import strict_json
from backend.providers.nvidia import (configured_nvidia_provider, NvidiaError, BASE_URL,
                                     model_identity_status, OBSERVED_SUPER_IDENTITY_STATUS)
from .dispatcher import RestrictedDispatcher
from .memory import HMemMemory
from .model_contracts import TrustedDisclosure


def _load(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError
    return strict_json(raw)


def execution_report(report, receipts, *, allow_observed_super_route=False):
    """Annotate observed provider calls, never promote a blocked investigation.

    Caller supplies only receipts validated by the trusted fixed-endpoint client.
    Metadata and fixture tests alone are not independent live-service evidence.
    """
    if (type(allow_observed_super_route) is not bool or not isinstance(receipts, list)
            or not 0 < len(receipts) <= 8):
        return report
    statuses = []
    for receipt in receipts:
        if (not isinstance(receipt, dict) or receipt.get('provider') != 'nvidia_hosted'
                or receipt.get('endpoint') != BASE_URL or not isinstance(receipt.get('response_id'), str)
                or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', receipt['response_id'])):
            return report
        try:
            status = model_identity_status(receipt.get('requested_model'), receipt.get('response_model'),
                                           allow_observed_super_route=allow_observed_super_route)
        except NvidiaError:
            return report
        if ((status == OBSERVED_SUPER_IDENTITY_STATUS and receipt.get('identity_status') != status)
                or (status != OBSERVED_SUPER_IDENTITY_STATUS and 'identity_status' in receipt)):
            return report
        statuses.append(status)
    result = dict(report)
    result.update(execution_mode='model_directed_nvidia_hosted', provider_kind='nvidia_hosted',
                  model_inference_performed=True, live_inference_verified=True)
    result['provider_model_identity_status'] = (OBSERVED_SUPER_IDENTITY_STATUS
        if OBSERVED_SUPER_IDENTITY_STATUS in statuses else 'requested_and_server_reported_model_match')
    result['limitations'] = [text for text in report.get('limitations', [])
                             if text != 'No verified live Nightshift/Nemotron inference.']
    result['limitations'].append('Direct NVIDIA hosted calls observed; Nightshift was not used. Server-reported model identity is not hardware attestation. Completed financial verification and semantic accuracy are separate from inference.')
    if OBSERVED_SUPER_IDENTITY_STATUS in statuses:
        result['limitations'].append('Explicit observed text route: requested public Super VL name differs from the server-reported internal Nemotron name. Alias equivalence, exact weights and vision-language capability are not independently verified.')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', nargs='?', help='Trusted local InvestigationRequest JSON')
    parser.add_argument('--disclosures', help='Trusted local registered SEC disclosures JSON list')
    parser.add_argument('--live', action='store_true', help='Explicit authorized hosted requests only')
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--discover', action='store_true', help='List actually available Nemotron IDs')
    operation.add_argument('--smoke', action='store_true', help='One completion, at most32outputtokens')
    args = parser.parse_args(argv)
    try:
        provider = configured_nvidia_provider(enabled=args.live)
        if args.discover:
            print(json.dumps(provider.discover(), allow_nan=False))
            return 0
        if args.smoke:
            print(json.dumps(provider.smoke(), allow_nan=False))
            return 0
        if not args.request:
            raise ValueError
        request = InvestigationRequest.model_validate(_load(args.request))
        disclosures = []
        if args.disclosures:
            rows = _load(args.disclosures)
            if not isinstance(rows, list) or len(rows) > 3:
                raise ValueError
            for row in rows:
                row = dict(row)
                for key in ('published_at', 'period_start', 'period_end'):
                    row[key] = date.fromisoformat(row[key])
                disclosures.append(TrustedDisclosure(**row))
        dispatcher = RestrictedDispatcher(request, disclosures=disclosures, memory=HMemMemory())
        report = dispatcher.run(provider)
        report = execution_report(report, provider.receipts,
                                  allow_observed_super_route=provider.observed_super_route_enabled)
        print(json.dumps({'report': report, 'provider_receipts': provider.receipts,
                          'provider_error_code': provider.last_error_code,
                          'provider_diagnostic': provider.last_diagnostic,
                          'provider_propose_attempts': provider.propose_attempts,
                          'provider_validation_history': provider.validation_history,
                          'provider_format_correction_enabled': provider.format_correction_enabled,
                          'provider_observed_super_route_enabled': provider.observed_super_route_enabled,
                          'receipt_limit': 'Server-reported model identity; semantic extraction still requires human review.'}, allow_nan=False))
        return 2 if report['status'] == 'blocked' else 0
    except NvidiaError as error:
        code = str(error)
    except Exception:
        code = 'invalid_local_nvidia_run_input'
    print(json.dumps({'status': 'blocked', 'error_code': code,
                      'live_inference_verified': False, 'human_review_status': 'required'}))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
