#!/usr/bin/env python3
"""Check the original task's scrub patterns in packaged source, excluding Git
metadata, generated caches and private runtime/configuration files. Encoding
prevents this validation program from matching its own forbidden literals.
"""
import base64
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(base64.b64decode('cXVvdHVtfGtpY2tlcnxlZ2dwb3B8Y2VudGltYW51c3xuaWdodGRlc2t8L1VzZXJzL3wxNjIwNjU5OTQ4fDE3NzkzNTQxOXwxODYzMjE0ODV8MTAwXC43M1wufHBheV8/dG98bnZkYXxwb25zfHJvYmluaG9vZHx2ZW5pY2V8YWdlbnRzLTF8YmtrfHN1YnNcLmpzb258MHhbMC05YS1mQS1GXXs0MH0=').decode(), re.I)
errors = []
for file in ROOT.rglob('*'):
    relative = file.relative_to(ROOT)
    if any(part in {'.git', '__pycache__', '.pytest_cache', 'var'} for part in relative.parts):
        continue
    if not file.is_file() or file.name in {'config.toml', 'service.env', 'bot.env', '.env'}:
        continue
    try:
        text = file.read_text()
    except UnicodeDecodeError:
        continue
    for number, line in enumerate(text.splitlines(), 1):
        if PATTERN.search(line):
            errors.append(f'{relative}:{number}: forbidden deployment reference')
if errors:
    raise SystemExit('\n'.join(errors))
print('PASS: deployment scrub patterns absent from packaged source.')
