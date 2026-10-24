"""Process-isolated reuse of accepted SEC/Zetaris readers, with no cloud writes."""
import json
import subprocess
import sys
from pathlib import Path

from backend.models import InvestigationRequest, Evidence


def retrieve(request, timeout_seconds):
    # A process boundary enforces an overall wall deadline even if an upstream
    # read repeatedly sends bytes within its socket inactivity timeout.
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'backend.investigation.retrieval'],
            input=request.model_dump_json(), capture_output=True, text=True,
            cwd=Path(__file__).resolve().parents[2], timeout=timeout_seconds,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        payload = json.loads(result.stdout) if result.returncode == 0 else {}
        if not payload.get('ok'):
            raise RuntimeError('Evidence retrieval failed or is not configured')
        canonical = InvestigationRequest.model_validate(payload['request'])
        request.company = canonical.company
        return [Evidence.model_validate(e) for e in payload['evidence']]
    except subprocess.TimeoutExpired:
        raise TimeoutError('Evidence retrieval reached the wall deadline') from None
    except (ValueError, KeyError, OSError):
        raise RuntimeError('Evidence retrieval returned invalid data') from None


def main():
    try:
        request = InvestigationRequest.model_validate_json(sys.stdin.read(20000))
        if request.evidence_backend == 'zetaris':
            from backend.zetaris import zetaris_evidence
            evidence = zetaris_evidence(request)
        else:
            from backend.sources import sec_evidence
            evidence = sec_evidence(request)
        print(json.dumps({'ok': True, 'request': request.model_dump(mode='json'),
                          'evidence': [e.model_dump(mode='json') for e in evidence]}))
    except Exception:
        # Never expose private configuration, HTTP messages, URLs or headers.
        print(json.dumps({'ok': False, 'error_code': 'evidence_unavailable'}))


if __name__ == '__main__':
    main()
