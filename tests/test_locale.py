import os
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]

class LocaleTest(unittest.TestCase):
    def test_english_default_in_fresh_process(self):
        env = dict(os.environ)
        env.pop('TEAM_LOCALE', None)
        env['TEAM_CONFIG'] = str(ROOT / 'tests/missing-config.toml')
        script = '''
import importlib.util, re
spec = importlib.util.spec_from_file_location('gate', 'gate/gate.py')
gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
assert gate.LOCALE == 'en'
assert gate.L_NEW == '➕ task'
assert 'Using the team gate' in gate.OWNER_GUIDE
assert 'ref https://example.com/article' in gate.GUEST_GUIDE
for ru, en in gate.LOCALES['en'].items():
    if ru.startswith(('A chip under', 'Under a report', '🔎 глубже:')):
        continue
    assert not re.search('[А-Яа-яё]', en), en
    assert re.findall(r'%[ds]|%\\.\\d+f', ru) == re.findall(r'%[ds]|%\\.\\d+f', en), ru
'''
        result = subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
