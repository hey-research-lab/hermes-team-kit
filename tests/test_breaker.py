from pathlib import Path
import tempfile
import unittest
from breaker import evaluate, enforce
from ledger import append


class BreakerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ledger.jsonl'
        self.config = {'paths': {'ledger': str(self.path)}, 'limits': {'breaker_threshold': .8},
                       'seats': {'A': {'profiles': ['builder'], 'daily_cap_usd': 10}}}

    def spend(self, dollars):
        append(self.path, {'type': 'finished', 'event_id': str(dollars), 'card_id': 'c', 'task_id': 't',
                           'profile': 'builder', 'model': 'example', 'provider': 'custom',
                           'dollars': dollars, 'duration': 1, 'group': 'A', 'ts': 100})

    def test_threshold_and_daily_resume(self):
        self.spend(7.99)
        self.assertFalse(evaluate(self.config, 200)['groups']['A']['paused'])
        self.spend(.01)
        self.assertTrue(evaluate(self.config, 200)['groups']['A']['paused'])
        self.assertFalse(evaluate(self.config, 86400)['groups']['A']['paused'])

    def test_endpoint_cap_overrides_config_and_falls_back_on_error(self):
        self.config['provider'] = {'usage_url': 'https://example.com/usage', 'api_key_env': 'TEST_KEY'}
        def fetch(url, key):
            return {'daily_cap_usd': 5, 'spent_usd': 4, 'reset_at': '1970-01-02T00:00:00Z'}
        row = evaluate(self.config, 200, fetch)['groups']['A']
        self.assertTrue(row['paused'])
        self.assertEqual(row['source'], 'endpoint')
        self.spend(8)
        def fail(*args):
            raise OSError('offline')
        row = evaluate(self.config, 200, fail)['groups']['A']
        self.assertTrue(row['paused'])
        self.assertEqual(row['source'], 'ledger-fallback')

    def test_unknown_local_cost_pauses_capped_group(self):
        self.spend(None)
        self.assertTrue(evaluate(self.config, 200)['groups']['A']['paused'])

    def test_uncapped_key_does_not_need_usage(self):
        del self.config['seats']['A']['daily_cap_usd']
        self.assertFalse(evaluate(self.config, 200)['groups']['A']['paused'])

    def test_only_owned_scheduled_cards_resume_and_running_cards_finish(self):
        self.spend(8)
        cards = [{'id': 'c', 'assignee': 'builder', 'status': 'ready'},
                 {'id': 'live', 'assignee': 'builder', 'status': 'running'},
                 {'id': 'manual', 'assignee': 'builder', 'status': 'scheduled'}]
        calls = []
        def command(*args):
            import json
            calls.append(args)
            if args[0] == 'list':
                return json.dumps(cards)
            cards[0]['status'] = 'scheduled' if args[0] == 'schedule' else 'ready'
        path = Path(self.tmp.name) / 'held.json'
        enforce(evaluate(self.config, 200), command, path)
        enforce(evaluate(self.config, 86400), command, path)
        self.assertEqual([c for c in calls if c[0] != 'list'],
                         [('schedule', 'c', 'daily key budget breaker'), ('unblock', 'c')])
