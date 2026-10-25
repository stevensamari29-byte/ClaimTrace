"""Fixed isolated HTTP worker. Secrets arrive on stdin and are never printed."""
import sys
from .meterless_client import MeterlessClient, strict_json


def main():
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            return 2
        value = strict_json(raw)
        client = MeterlessClient(value['base_url'], value['token'])
        result = client.structured(value['context'], value['tools'], value['model'],
                                   max_tokens=value['max_tokens'], timeout=value['timeout'])
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        return 2


if __name__ == '__main__':
    sys.exit(main())
