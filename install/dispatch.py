#!/usr/bin/env python3
"""Dispatch after budget enforcement. Use a dedicated board, no other dispatchers."""
from pathlib import Path
import os
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kit_config import load
from breaker import control_lock, update, enforce


def main():
    config = load()
    if Path(config['paths']['gate'], 'PAUSE').exists():
        return 0
    cli = config.get('hermes', {})
    base = [cli.get('command', 'hermes'), 'kanban', '--board', cli.get('board', 'default')]
    def command(*args):
        return subprocess.check_output(base + list(args), timeout=120, text=True)
    with control_lock(config):
        snapshot = update(config)
        enforce(snapshot, command, Path(config['paths']['out']) / 'breaker-held.json')
        if snapshot['tripped'] or Path(config['paths']['gate'], 'PAUSE').exists():
            return 0
        return subprocess.run(base + ['dispatch', '--max', '1'], timeout=120).returncode


if __name__ == '__main__':
    sys.exit(main())
