"""Opt-in, killable structured transport preparation, not verified live inference."""
import json
import math
import re
from pathlib import Path
import subprocess
import sys
import time

from .meterless_client import MeterlessClient


class StructuredProviderError(RuntimeError):
    """Public errors intentionally contain no endpoint, token or provider text."""


class NightshiftStructuredProvider:
    structured_deadline_protocol = 'claimtrace.structured-deadline.v1'
    execution_kind = 'unverified_provider'

    def __init__(self, base_url, token, model, *, enabled=False, max_tokens=1536):
        if enabled is not True:
            raise StructuredProviderError('structured_provider_disabled')
        # Reuse the existing secure normalization/auth checks without networking.
        try:
            client = MeterlessClient(base_url, token)
            if (not isinstance(model, str) or not re.fullmatch(r'meterless/[A-Za-z0-9_.:/-]{1,160}', model)
                    or type(max_tokens) is not int or not 1024 <= max_tokens <= 2048):
                raise ValueError
        except Exception:
            raise StructuredProviderError('structured_provider_configuration_invalid') from None
        self.__configuration = {'base_url': client.base_url, 'token': token,
                                'model': model, 'max_tokens': max_tokens}

    def propose(self, *, context, tools, deadline):
        process = None
        try:
            if type(deadline) not in (int, float) or not math.isfinite(deadline):
                raise ValueError
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            # Tools originate in host contracts, never in model/source output.
            from backend.investigation.model_contracts import tool_definitions
            if tools != tool_definitions():
                raise ValueError
            message = json.dumps({**self.__configuration, 'context': context,
                                  'tools': tools, 'timeout': min(120, remaining)}, allow_nan=False).encode('utf-8')
            if len(message) > 262144:
                raise ValueError
            if time.monotonic() >= deadline:
                raise TimeoutError
            process = subprocess.Popen([sys.executable, '-E', '-s', '-m', 'backend.providers.structured_worker'],
                cwd=Path(__file__).resolve().parents[2], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            output, _ = process.communicate(message, timeout=remaining)
            if time.monotonic() >= deadline:
                raise TimeoutError
            if process.returncode != 0 or len(output) > 65536:
                raise ValueError
            from backend.investigation.dispatcher import decode_proposal
            text = output.decode('utf-8')
            decode_proposal(text)
            return text
        except Exception:
            raise StructuredProviderError('structured_provider_unavailable') from None
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
