"""Exercise the actual dispatch script with an isolated fake CLI, no network."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from breaker import trip, reset_manual
from ledger import append

ROOT = Path(__file__).resolve().parents[1]


class DispatchTest(unittest.TestCase):
    def test_manual_and_hourly_stop_prevent_launch_but_keep_running_card(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cli = root / 'hermes'
            cli.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
path = Path(os.environ['FAKE_CARDS'])
cards = json.loads(path.read_text())
with open(os.environ['FAKE_CALLS'], 'a') as stream:
    stream.write(json.dumps(args) + '\\n')
if 'list' in args:
    print(json.dumps(cards))
elif 'schedule' in args or 'unblock' in args:
    action = 'schedule' if 'schedule' in args else 'unblock'
    card = next(c for c in cards if c['id'] == args[args.index(action) + 1])
    card['status'] = 'scheduled' if action == 'schedule' else 'ready'
    path.write_text(json.dumps(cards))
''')
            cli.chmod(0o755)
            config_path = root / 'config.toml'
            config_path.write_text('[paths]\ngate="gate"\nout="out"\nledger="ledger.jsonl"\n'
                                   '[hermes]\ncommand=' + json.dumps(str(cli)) + '\n'
                                   '[limits]\nhourly_usd=5\n[telegram]\nowner_ids=[42]\n')
            from kit_config import load
            config = load(config_path)
            cards_path = root / 'cards.json'
            cards_path.write_text(json.dumps([
                {'id': 'next', 'assignee': 'builder', 'status': 'ready'},
                {'id': 'live', 'assignee': 'writer', 'status': 'running'},
                {'id': 'outside', 'assignee': 'tester', 'status': 'scheduled'}]))
            calls_path = root / 'calls.jsonl'
            env = {**os.environ, 'TEAM_CONFIG': str(config_path),
                   'FAKE_CARDS': str(cards_path), 'FAKE_CALLS': str(calls_path)}
            def run():
                calls_path.write_text('')
                subprocess.run([sys.executable, str(ROOT / 'install/dispatch.py')], env=env, check=True)
                return [json.loads(line) for line in calls_path.read_text().splitlines()]
            def launches(calls):
                return any('dispatch' in call for call in calls)
            trip(config, 'builder', 'tool failure')
            self.assertFalse(launches(run()))
            self.assertEqual([c['status'] for c in json.loads(cards_path.read_text())],
                             ['scheduled', 'running', 'scheduled'])
            reset_manual(config, 42, 'tool checked')
            self.assertTrue(launches(run()))
            append(config['paths']['ledger'], {'type': 'finished', 'event_id': 'cost',
                'task_id': 't', 'card_id': 'live', 'profile': 'writer', 'model': 'example',
                'provider': 'custom', 'dollars': 5, 'duration': 1, 'ts': time.time()})
            calls = run()
            self.assertFalse(launches(calls))
            self.assertTrue(any(call[-1] == 'hourly cap' for call in calls))
            # Move only the fixture completion out of the rolling window.
            ledger = Path(config['paths']['ledger'])
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            rows[-1]['ts'] -= 3601
            ledger.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            self.assertTrue(launches(run()))
            self.assertEqual([c['status'] for c in json.loads(cards_path.read_text())],
                             ['ready', 'running', 'scheduled'])
