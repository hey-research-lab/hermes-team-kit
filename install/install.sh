#!/bin/sh
# Run as the user that owns Hermes. No third-party downloads or root writes.
set -eu
if [ "$(id -u)" -eq 0 ]; then
    echo 'Run install.sh as a non-root user.' >&2
    exit 1
fi
kit_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$kit_root"
python3 - "$kit_root" <<'PY'
import hashlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
for line in (root / 'install/SHA256SUMS').read_text().splitlines():
    expected, filename = line.split('  ', 1)
    path = root / filename
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Hash mismatch: ' + filename)
print('Source hashes verified.')
PY
exec python3 install/setup.py "$@"
