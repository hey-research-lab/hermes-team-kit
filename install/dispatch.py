#!/usr/bin/env python3
"""Dispatch after budget enforcement. Use a dedicated board, no other dispatchers."""
from pathlib import Path
import os
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kit_config import load
config = load()
if not Path(config['paths']['gate'], 'PAUSE').exists():
    cli = config.get('hermes', {})
    result = subprocess.run([cli.get('command', 'hermes'), 'kanban', '--board', cli.get('board', 'default'),
                             'dispatch', '--max', '1'], timeout=120)
    sys.exit(result.returncode)
