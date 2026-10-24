"""Run typed investigations without the frontend or an inference runtime."""
import argparse
import json
from pathlib import Path

from . import InvestigationInput, run_investigation


def main():
    parser = argparse.ArgumentParser(description='ClaimTrace incomplete agent: deterministic investigation, no model inference')
    parser.add_argument('input', type=Path, help='JSON file containing request and claim_inputs')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--memory-dir', type=Path, help='Optional private local H-MEM state directory')
    parser.add_argument('--memory-scope', default='local-cli')
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 24000:
            raise ValueError('Input too large')
        data = InvestigationInput.model_validate_json(args.input.read_text(encoding='utf-8-sig'))
        memory = None
        if args.memory_dir:
            from .memory import HMemMemory
            memory = HMemMemory(root=args.memory_dir, scope_id=args.memory_scope, actor='local-human')
        report = run_investigation(data, memory=memory)
        output = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            args.output.write_text(output + '\n', encoding='utf-8')
        else:
            print(output)
        return 0
    except Exception:
        # Validation exceptions can contain user inputs; only bounded setup text
        # is emitted. API callers receive normal typed validation exceptions.
        print(json.dumps({'error_code': 'invalid_input_or_local_setup',
                          'message': 'Check input JSON, approved evidence configuration and optional local memory setup.'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
