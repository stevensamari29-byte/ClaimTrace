"""Opt-in, killable structured transport preparation, not verified live inference."""
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import time

from .meterless_client import (MeterlessClient, valid_runtime_model,
    NIGHTSHIFT_NVIDIA_MODEL, strict_json, validate_nightshift_receipt)


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
            if (not valid_runtime_model(model)
                    or type(max_tokens) is not int or not 1024 <= max_tokens <= 2048):
                raise ValueError
        except Exception:
            raise StructuredProviderError('structured_provider_configuration_invalid') from None
        self.__configuration = {'base_url': client.base_url, 'token': token,
                                'model': model, 'max_tokens': max_tokens}
        self.__receipts = []

    @property
    def provider_receipts(self):
        """Observed transport provenance only, never financial acceptance."""
        return strict_json(json.dumps(self.__receipts, allow_nan=False))

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
            if self.__configuration['model'] == NIGHTSHIFT_NVIDIA_MODEL and len(self.__receipts) >= 8:
                raise ValueError
            message = json.dumps({**self.__configuration, 'context': context,
                                  'tools': tools, 'timeout': min(120, remaining),
                                  'nightshift_receipt': self.__configuration['model'] == NIGHTSHIFT_NVIDIA_MODEL}, allow_nan=False).encode('utf-8')
            if len(message) > 262144:
                raise ValueError
            output = run_structured_worker(message, deadline, max_output=65536)
            from backend.investigation.dispatcher import decode_proposal
            text = output.decode('utf-8')
            if self.__configuration['model'] == NIGHTSHIFT_NVIDIA_MODEL:
                envelope = strict_json(text)
                if (not isinstance(envelope, dict) or set(envelope) - {'proposal', 'receipt', 'error_code'}
                        or len(self.__receipts) >= 8):
                    raise ValueError
                receipt = validate_nightshift_receipt(envelope.get('receipt'))
                if self.__configuration['token'] in json.dumps(receipt, allow_nan=False):
                    raise ValueError
                self.__receipts.append(receipt)
                if 'error_code' in envelope or not isinstance(envelope.get('proposal'), str):
                    raise ValueError
                text = envelope['proposal']
            decode_proposal(text)
            return text
        except Exception:
            raise StructuredProviderError('structured_provider_unavailable') from None


def run_structured_worker(message, deadline, *, max_output=131072):
    """Shared fixed child-process transport; absolute deadline and stdin secrets."""
    process = None
    try:
        if len(message) > 262144 or type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise ValueError
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        environment = {key: value for key, value in os.environ.items()
                       if key not in ('NVIDIA_API_KEY', 'NIGHTSHIFT_RUNTIME_TOKEN')}
        process = subprocess.Popen([sys.executable, '-E', '-s', '-m', 'backend.providers.structured_worker'],
            cwd=Path(__file__).resolve().parents[2], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        output, _ = process.communicate(message, timeout=remaining)
        if time.monotonic() >= deadline or process.returncode != 0 or len(output) > max_output:
            raise ValueError
        return output
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate()
