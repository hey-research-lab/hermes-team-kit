import json
from pathlib import Path
import tempfile
import unittest
from ledger import append, events, finished, report


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.jsonl'

    def test_completion_retry_is_idempotent_and_acceptance_is_distinct(self):
        shown = {'task': {'assignee': 'builder'}, 'runs': [
            {'id': 3, 'profile': 'builder', 'model': 'example', 'provider': 'custom',
             'started_at': 95, 'ended_at': 100, 'metadata': {'cost_usd': .5, 'tokens': 20}}]}
        finished(self.path, 'task-1', 'card-1', shown, 'A')
        original = self.path.read_bytes()
        finished(self.path, 'task-1', 'card-1', shown, 'A')
        self.assertEqual(self.path.read_bytes(), original)
        append(self.path, {'type': 'accepted', 'event_id': 'ok:task-1', 'task_id': 'task-1', 'ts': 110})
        row = list(events(self.path))[0]
        self.assertEqual((row['duration'], row['tokens'], row['dollars']), (5, 20, .5))
        self.assertIn('builder\t0.5000\t1\t0.5000\t0', report(self.path, 1, 120))

    def test_unknown_cost_is_not_zero_and_old_work_is_excluded(self):
        finished(self.path, 'task-1', 'card-1', {'task': {'assignee': 'writer'}})
        self.assertIn('unknown', report(self.path))
        self.assertEqual(len(report(self.path, 1, 200).splitlines()), 1)

    def test_corruption_and_invalid_values_fail(self):
        self.path.write_text('not json\n')
        with self.assertRaises(json.JSONDecodeError):
            report(self.path)
        self.path.unlink()
        with self.assertRaises(ValueError):
            append(self.path, {'type': 'finished', 'event_id': 'a', 'profile': 'builder',
                               'model': 'a', 'provider': 'a', 'card_id': 'a', 'task_id': 'a',
                               'dollars': float('nan'), 'duration': 0})
