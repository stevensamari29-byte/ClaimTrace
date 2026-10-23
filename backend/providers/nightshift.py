"""Explicit opt-in runtime construction, never a startup/investigation request."""
import os
from .meterless_client import MeterlessClient


def configured_runtime():
    if os.getenv('NIGHTSHIFT_INFERENCE_ENABLED', 'false').lower() != 'true':
        raise ValueError('Nightshift inference is disabled; explicit authorization/configuration required')
    return MeterlessClient(os.environ['NIGHTSHIFT_BASE_URL'], os.environ['NIGHTSHIFT_RUNTIME_TOKEN'], app_id='claimtrace')
