"""Inspect actual Git-index blobs, not fixtures or the ignored local environment."""
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).parents[2]
KEY_PATTERNS = (
    rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    rb'\bsk-proj-[A-Za-z0-9_-]{24,}',
    rb'\bgh[pousr]_[A-Za-z0-9]{36,}\b',
    rb'\bgithub_pat_[A-Za-z0-9_]{60,}\b',
)


def git(*arguments):
    return subprocess.run(['git', *arguments], cwd=ROOT, check=True, capture_output=True).stdout


def test_git_index_contains_no_private_config_or_high_confidence_keys():
    paths = [p.decode('utf-8') for p in git('ls-files', '-z').split(b'\0') if p]
    findings = []
    for path in paths:
        pure = PurePosixPath(path)
        lowered = [part.lower() for part in pure.parts]
        name = pure.name.lower()
        private_env = (name == '.env' or name.startswith('.env.')) and name != '.env.example'
        if (private_env or any(part in ('.venv', 'venv', 'node_modules') for part in lowered)
                or name in ('id_rsa', 'id_ed25519', 'id_ecdsa') or name.endswith(('.pem', '.p12', '.pfx'))):
            findings.append(f'{path}: forbidden private/configuration artifact')
            continue
        # Read the staged/committed blob itself; a clean worktree replacement cannot hide a staged secret.
        content = git('show', ':' + path)
        if any(re.search(pattern, content) for pattern in KEY_PATTERNS):
            findings.append(f'{path}: high-confidence credential pattern')
    assert not findings, '\n'.join(findings)
