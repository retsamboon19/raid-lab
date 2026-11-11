"""Search regression gate; native execution is always mocked (no game launches)."""
import copy
import json
import queue
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

import core
import native_battle
import native_search
import report_history
import server


class NativeSearchTests(unittest.TestCase):
    def test_original_ui_damage_ranking_differs_from_aggregate(self):
        a = {'score': '6000000000', 'gameTotalDamage': '5400000000'}
        b = {'score': '5900000000', 'gameTotalDamage': '5500000000'}
        self.assertGreater(native_search._rank(b, 'anomaly'), native_search._rank(a, 'anomaly'))
        self.assertEqual(native_search._damage(a), '5400000000')
        self.assertEqual(native_search._damage({'score': '123'}), '123')
        self.assertEqual(native_search._damage({'score': '123', 'gameTotalDamage': '0'}), '0')

    def setUp(self):
        self.payload = {'engine': 'original153', 'roster': core.demo_roster(),
            'settings': {'encounter_id': 'practice:1'}, 'search': {'budget': 3, 'teams': 1}}
        self.encounter = {'id': 'practice:1', 'contentMode': 'practice', 'name': 'Test', 'timeLimit': 90}
        self.patches = [patch.object(native_battle, '_release', return_value=({}, 'receipt')),
                        patch.object(native_battle, '_encounter', side_effect=lambda _: self.encounter),
                        patch.object(native_search, 'shortlist', side_effect=lambda r,e,p,c:
                            (native_search.proposals(r,e,c), {'simulations':0,'elapsed':0}))]
        for p in self.patches:p.start()
        self.addCleanup(lambda: [p.stop() for p in reversed(self.patches)])
        self.calls = []

    def battle(self, request, progress):
        self.calls.append(copy.deepcopy(request))
        progress(phase='Mock native battle')
        return {'score': str(9007199254740993 + len(self.calls)), 'engine': 'original153',
            'nativeResult': 2, 'durationMs': 90000, 'characters': [], 'jobId': str(len(self.calls)),
            'nativeOutcome': {}, 'packet': {'mock': True}}

    def run_search(self, cancel=lambda: False):
        with patch.object(native_battle, 'run_battle', side_effect=self.battle):
            return native_search.run_search(self.payload, cancel=cancel)

    def test_automatic_candidates_and_exact_native_rank(self):
        result = self.run_search()
        self.assertEqual(result['simulations'], 3)
        self.assertEqual(result['teams'][0]['damage'], '9007199254740996')
        self.assertEqual(result['total'], '9007199254740996')
        self.assertEqual(len({r['settings']['random_seed'] for r in self.calls}), 1)
        for request in self.calls:
            self.assertEqual(len(set(request['members'])), 5)
            self.assertEqual(request['roster'], self.payload['roster'])
            self.assertEqual(request['settings']['encounter_id'], 'practice:1')
            self.assertNotIn('search', request)

    def test_disabled_units_never_selected(self):
        self.payload['roster'][0]['enabled'] = False
        self.run_search()
        self.assertTrue(all(self.payload['roster'][0]['id'] not in r['members'] for r in self.calls))

    def test_control_policy_and_explicit_seed_are_preserved(self):
        self.payload['settings'].update(control_policy='qte-parts-cover', random_seed=12345)
        self.run_search()
        self.assertTrue(all(r['settings'] == self.payload['settings'] for r in self.calls))

    def test_cancel_keeps_current_completed_battle(self):
        result = self.run_search(cancel=lambda: len(self.calls) == 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(result['completion']['reason'], 'cancelled')
        self.assertEqual(result['simulations'], 1)

    def test_cancel_before_start_does_not_launch(self):
        with self.assertRaises(InterruptedError):self.run_search(cancel=lambda: True)
        self.assertEqual(self.calls, [])

    def test_multisquad_no_reuse(self):
        self.encounter['contentMode'] = 'solo'
        self.payload['search']['teams'] = 5
        result = self.run_search()
        self.assertEqual(len(result['teams']), 5)
        members = [n for t in result['teams'] for n in t['members']]
        self.assertEqual(len(set(members)), 25)
        self.assertLessEqual(len(self.calls), 15)

    def test_runtime_failure_stops_and_preserves_completed(self):
        calls = []
        def run(request, progress):
            calls.append(request)
            if len(calls) == 2:raise native_battle.NativeBattleError('native_source_mismatch', 'Changed source')
            return self.battle(request, progress)
        with patch.object(native_battle, 'run_battle', side_effect=run):
            result = native_search.run_search(self.payload)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['completion']['reason'], 'error')
        self.assertEqual(result['simulations'], 1)
        self.assertEqual(result['failures'][0]['code'], 'native_source_mismatch')

    def test_first_failure_is_not_a_recommendation(self):
        with patch.object(native_battle, 'run_battle', side_effect=native_battle.NativeBattleError('bad', 'failed')):
            with self.assertRaises(native_battle.NativeBattleError):native_search.run_search(self.payload)

    def test_invalid_options_and_roster(self):
        for key, value in [('budget', 1000), ('teams', True), ('teams', 6)]:
            request = copy.deepcopy(self.payload);request['search'][key] = value
            with self.assertRaises(ValueError):native_search.validate_request(request)
        self.payload['roster'] = self.payload['roster'][:4]
        with self.assertRaises(ValueError):native_search.validate_request(self.payload)

    def test_duplicate_and_unknown_ids_rejected(self):
        self.payload['roster'].append(copy.deepcopy(self.payload['roster'][0]))
        with self.assertRaises(ValueError):native_search.validate_request(self.payload)
        self.payload['roster'][-1]['id'] = 'unknown'
        with self.assertRaises(ValueError):native_search.validate_request(self.payload)

    def test_single_mode_cannot_request_multiple_squads(self):
        self.payload['search']['teams'] = 2
        with self.assertRaises(ValueError):native_search.validate_request(self.payload)

    def test_same_five_can_compare_slot_orders(self):
        plan = native_search.proposals(self.payload, self.encounter)[0][0]
        self.payload['roster'] = [r for r in self.payload['roster'] if r['id'] in plan]
        plans = native_search.proposals(self.payload, self.encounter)
        self.assertGreaterEqual(len(plans), 2)
        self.assertTrue(all(set(p[0]) == set(plan) for p in plans))

    def test_clear_ranking_over_damage(self):
        clear = {'nativeResult': 1, 'durationMs': 80000, 'score': '1'}
        failed = {'nativeResult': 2, 'durationMs': 90000, 'score': '999999999999'}
        self.assertGreater(native_search._rank(clear, 'campaign'), native_search._rank(failed, 'campaign'))
        self.assertLess(native_search._rank(clear, 'anomaly'), native_search._rank(failed, 'anomaly'))

    def test_worker_and_history_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            history = report_history.ReportHistory(Path(directory), core.CAT)
            events = queue.Queue()
            with patch.object(native_battle, 'run_battle', side_effect=self.battle), patch.object(server, 'history_store', return_value=history):
                server.worker(self.payload, 'search', events, threading.Event())
            messages = []
            while not events.empty():messages.append(events.get())
            self.assertEqual(messages[-1]['status'], 'done')
            result = messages[-1]['result']
            saved = history.get(result['history']['id'])['report']
            self.assertEqual(saved['teams'], result['teams'])
            self.assertEqual(saved['schema'], 'native-search-v1')

    def test_http_search_to_job_result_without_manual_members(self):
        class InlineProcess:
            def __init__(self, target, args, **kwargs):self.target, self.args = target, args
            def start(self):self.target(*self.args)
            def is_alive(self):return False
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory, \
                    patch.object(server, 'PORT', http.server_port), patch.object(server, 'JOBS', {}), \
                    patch.object(server.mp, 'Process', InlineProcess), patch.object(server.mp, 'Queue', queue.Queue), \
                    patch.object(server, 'history_store', return_value=report_history.ReportHistory(Path(directory), core.CAT)), \
                    patch.object(native_battle, 'run_battle', side_effect=self.battle):
                base = f'http://127.0.0.1:{http.server_port}'
                req = Request(base + '/api/search', data=json.dumps(self.payload).encode(), headers={'Content-Type': 'application/json'})
                with urlopen(req) as response:
                    self.assertEqual(response.status, 202)
                    job = json.load(response)['id']
                with urlopen(base + '/api/jobs/' + job) as response:
                    state = json.load(response)
                self.assertEqual(state['status'], 'done')
                self.assertEqual(state['result']['schema'], 'native-search-v1')
                with urlopen(base + '/api/health') as response:self.assertTrue(json.load(response)['nativeSearch'])
        finally:
            http.shutdown();thread.join();http.server_close()


if __name__ == '__main__':unittest.main()
