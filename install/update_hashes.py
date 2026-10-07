#!/usr/bin/env python3
"""Refresh installer integrity hashes after intentionally changing source."""
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
files = [ROOT / name for name in ('kit_config.py', 'breaker.py', 'ledger.py', 'config.example.toml')]
for directory in ('gate', 'take-tasks', 'profiles', 'install'):
    files += [p for p in (ROOT / directory).iterdir() if p.is_file() and p.name != 'SHA256SUMS']
lines = [hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + str(p.relative_to(ROOT)) for p in sorted(files)]
(ROOT / 'install/SHA256SUMS').write_text('\n'.join(lines) + '\n')
