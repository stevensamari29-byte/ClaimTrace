"""Fixed isolated HTTP worker. Secrets arrive on stdin and are never printed."""
import sys
from .meterless_client import MeterlessClient, strict_json


def main():
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            return 2
        value = strict_json(raw)
        if value.get('provider') == 'nvidia':
            import json
            from .nvidia import NvidiaClient, NvidiaError
            try:
                client = NvidiaClient(value['token'],
                    allow_observed_super_route=value.get('allow_observed_super_route', False))
                operation = value['operation']
                if operation == 'discover':
                    result = client.discover(timeout=min(15, value['timeout']))
                elif operation == 'smoke':
                    result = client.smoke(value['model'], timeout=value['timeout'])
                elif operation == 'propose':
                    result = client.structured(value['context'], value['tools'], value['model'],
                        max_tokens=value['max_tokens'], timeout=value['timeout'])
                else:
                    return 2
            except NvidiaError as error:
                result = {'error_code': str(error)}
                if error.diagnostic is not None:
                    from .nvidia import validate_diagnostic
                    result['diagnostic'] = validate_diagnostic(error.diagnostic)
            sys.stdout.buffer.write(json.dumps(result, allow_nan=False).encode('utf-8'))
            sys.stdout.buffer.flush()
            return 0
        client = MeterlessClient(value['base_url'], value['token'])
        result = client.structured(value['context'], value['tools'], value['model'],
                                   max_tokens=value['max_tokens'], timeout=value['timeout'],
                                   with_receipt=value.get('nightshift_receipt', False))
        if value.get('nightshift_receipt', False):
            import json
            sys.stdout.buffer.write(json.dumps(result, allow_nan=False).encode('utf-8'))
        else:
            sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        return 2


if __name__ == '__main__':
    sys.exit(main())
