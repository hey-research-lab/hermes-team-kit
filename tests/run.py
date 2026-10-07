#!/usr/bin/env python3
"""Run all suites without requiring a third-party test runner."""
import os
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['TEAM_LOCALE'] = 'ru'
os.environ['TEAM_CONFIG'] = str(ROOT / 'tests/missing-config.toml')
suite = unittest.TestSuite()
for directory in ('gate', 'take-tasks', 'tests'):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / directory), pattern='test_*.py', top_level_dir=str(ROOT / directory)))
sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
