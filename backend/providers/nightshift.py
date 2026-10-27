"""Explicit opt-in runtime construction, never a startup/investigation request."""
import os
from .meterless_client import MeterlessClient


def configured_runtime():
    if os.getenv('NIGHTSHIFT_INFERENCE_ENABLED', 'false').lower() != 'true':
        raise ValueError('Nightshift inference is disabled; explicit authorization/configuration required')
    return MeterlessClient(os.environ['NIGHTSHIFT_BASE_URL'], os.environ['NIGHTSHIFT_RUNTIME_TOKEN'], app_id='claimtrace')


def configured_structured_runtime(*, enabled=False):
    """Two explicit gates; no discovery, request or fallback during construction."""
    from .structured import NightshiftStructuredProvider, StructuredProviderError
    if enabled is not True or os.getenv('NIGHTSHIFT_INFERENCE_ENABLED', 'false').lower() != 'true':
        raise StructuredProviderError('structured_provider_disabled')
    try:
        return NightshiftStructuredProvider(os.environ['NIGHTSHIFT_BASE_URL'],
            os.environ['NIGHTSHIFT_RUNTIME_TOKEN'], os.environ['NIGHTSHIFT_MODEL_ID'], enabled=True)
    except Exception:
        raise StructuredProviderError('structured_provider_configuration_invalid') from None
