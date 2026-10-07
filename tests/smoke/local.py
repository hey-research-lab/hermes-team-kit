#!/usr/bin/env python3
"""Fresh-tree installer + private owner update -> real dispatcher -> fake Hermes.

No Telegram or model calls; the fake CLI validates the card command boundary.
"""
import importlib.util
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[2]


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / 'kit'
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '__pycache__', 'var', 'config.toml', 'service.env'))
        cli = Path(temporary) / 'hermes'
        cli.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
if 'create' in args:
    Path(os.environ['SMOKE_CARD']).write_text(json.dumps({'args': args, 'body': sys.stdin.read()}))
    print(json.dumps({'id': 'card-smoke'}))
elif 'show' in args:
    done = Path(os.environ['SMOKE_DONE']).exists()
    print(json.dumps({'task': {'id': 'card-smoke', 'assignee': 'builder', 'status': 'done' if done else 'ready'}, 'runs': [{'id': 1, 'profile': 'builder', 'ended_at': __import__('time').time(), 'metadata': {'cost_usd': .1, 'tokens': 50, 'model': 'example', 'provider': 'custom', 'duration': 2}}] if done else []}))
else:
    print('[]')
''')
        cli.chmod(0o755)
        config = root / 'config.toml'
        config.write_text((root / 'config.example.toml').read_text().replace('command = "hermes"', 'command = ' + json.dumps(str(cli))))
        env = {**os.environ, 'TEAM_CONFIG': str(config), 'TEAM_LOCALE': 'en',
               'HERMES_HOME': str(Path(temporary) / 'hermes-home'), 'SMOKE_CARD': str(Path(temporary) / 'card.json'), 'SMOKE_DONE': str(Path(temporary) / 'done')}
        # Twice validates idempotence; never touches the real Hermes home.
        for _ in range(2):
            subprocess.run(['sh', str(root / 'install/install.sh')], env=env, check=True)
        script = '''
import importlib.util, logging, os
from pathlib import Path
from kit_config import load
spec = importlib.util.spec_from_file_location('gate', 'gate/gate.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
class API:
    def send(self, *args, **kwargs): return 1
    def edit(self, *args, **kwargs): return None
config = load()
gate = module.Gate(config['paths']['gate'], config['paths']['out'], [900000001], API(), logging.getLogger('smoke'), own_uid=-1)
gate.handle_update({'update_id': 1, 'message': {'from': {'id': 900000001}, 'chat': {'id': 900000001, 'type': 'private'}, 'text': 'task write code to parse a public dataset'}})
'''
        subprocess.run([sys.executable, '-c', script], cwd=root, env=env, check=True)
        subprocess.run([sys.executable, str(root / 'take-tasks/take-tasks.py')], cwd=root, env=env, check=True)
        card = json.loads(Path(env['SMOKE_CARD']).read_text())
        assert card['args'][card['args'].index('--assignee') + 1] == 'builder'
        assert '## owner (en)' in card['body']
        assert 'Russian' not in card['body']
        assert len(list((root / 'var/out/tasks').glob('*.card'))) == 1
        Path(env['SMOKE_DONE']).touch()
        task = next((root / 'var/gate/tasks').glob('*.json'))
        tid = task.stem
        workspace = root / 'var/work/tasks' / tid
        (workspace / 'handoff.md').write_text('## owner (en)\nParser built and checked.\n## details (en)\nVerified empty and valid input.\n')
        subprocess.run([sys.executable, str(root / 'take-tasks/take-tasks.py')], cwd=root, env=env, check=True)
        proposal = json.loads((root / 'var/out/proposals' / ('report-' + tid + '.json')).read_text())
        assert proposal['title'].startswith('done:')
        decision_script = script[:script.index("gate.handle_update")] + "gate.scan()\nslug = next(iter(gate.state['proposals']))\ngate.decide(slug, 'approved', 900000001, nonce=gate.state['proposals'][slug]['nonce'])\n"
        subprocess.run([sys.executable, '-c', decision_script], cwd=root, env=env, check=True)
        subprocess.run([sys.executable, str(root / 'take-tasks/take-tasks.py')], cwd=root, env=env, check=True)
        rows = [json.loads(line) for line in (root / 'var/ledger.jsonl').read_text().splitlines()]
        assert sum(row['type'] == 'finished' for row in rows) == 1
        assert sum(row['type'] == 'accepted' for row in rows) == 1
        assert rows[0]['dollars'] == .1
        # A tampered runtime source must stop installation before any setup work.
        with (root / 'breaker.py').open('a') as stream:
            stream.write('\n# tampered\n')
        failed = subprocess.run(['sh', str(root / 'install/install.sh')], env=env, capture_output=True, text=True)
        assert failed.returncode != 0 and 'Hash mismatch' in failed.stderr
        print('PASS: idempotent fresh install, task, card, English report, acceptance, ledger and hash rejection.')

if __name__ == '__main__':
    main()
