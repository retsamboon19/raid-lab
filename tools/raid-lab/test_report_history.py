import copy
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch

from report_history import ReportHistory, timestamp


CATALOG = {'a': dict(name='Liter', element='Iron', burst='1', weapon='SMG'),
           'b': dict(name='Cinderella', element='Electric', burst='3', weapon='RL')}


def report(mode='museum', boss='museum-mother-whale', count=5, total=12345):
    return dict(settings=dict(content_mode=mode, boss_id=boss, museum_mode='challenge',
                             encounter=dict(name='Mother Whale', model_revision='model-v1'),
                             duration=180, teams=count, budget=6, playstyle='auto'),
                teams=[dict(members=['b', 'a', f'unknown-{i}'], damage=total/count, bursts=11,
                            builds=[dict(name='a', investment=dict(level=400))], timeline=[dict(time=5)])
                       for i in range(count)],
                total=total, simulations=999,
                selection=dict(critical_parts=dict(enabled=True, passed_teams=2, total_teams=count, fallback=True)))


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.history = ReportHistory(self.root, CATALOG)

    def tearDown(self):
        self.temp.cleanup()

    def test_persistent_grouped_snapshot_preserves_exact_report_and_order(self):
        original = report()
        snapshot = copy.deepcopy(original)
        saved = self.history.save(original)
        original['teams'][0]['builds'][0]['investment']['level'] = 1
        reopened = ReportHistory(self.root).get(saved['id'])
        self.assertEqual(reopened['report'], snapshot)
        self.assertEqual(reopened['summary']['simulations'], 999)
        self.assertEqual(reopened['summary']['budget'], 6)
        self.assertEqual(reopened['summary']['playstyle'], 'auto')
        page = self.history.list(mode='museum', boss='museum-mother-whale')
        self.assertEqual(page['total'], 1)
        summary = page['runs'][0]
        self.assertEqual(len(summary['teams']), 5)
        self.assertEqual(summary['total'], snapshot['total'])
        self.assertEqual([m['name'] for m in summary['teams'][0]['members']], ['Cinderella', 'Liter', 'unknown-0'])
        self.assertEqual([m['weapon'] for m in summary['teams'][0]['members']], ['RL', 'SMG', 'Unknown'])
        self.assertEqual(summary['critical_parts'], dict(passed_teams=2, total_teams=5, fallback=True))
        self.assertEqual(summary['model_revision'], 'model-v1')

    def test_damage_basis_only_for_reports_with_recorded_accounting(self):
        old=self.history.save(report())
        self.assertNotIn('damage_basis',self.history.get(old['id'])['summary'])
        updated=report()
        for team in updated['teams']:team['damage_accounting']={'boss_direct':team['damage']}
        saved=self.history.save(updated)
        self.assertEqual(self.history.get(saved['id'])['summary']['damage_basis'],'boss_direct')

    def test_mode_then_boss_and_newest_first_pagination(self):
        for total in range(12):
            self.history.save(report(total=total))
        self.history.save(report(mode='anomaly', boss='anomaly-ultra', count=1))
        self.history.save(report(mode='museum', boss='museum-ultra'))
        index = self.history.list()
        self.assertEqual(index['runs'], [])
        self.assertEqual(index['total'], 0)
        museum = next(m for m in index['modes'] if m['id'] == 'museum')
        self.assertEqual({b['id']: b['count'] for b in museum['bosses']}, {'museum-mother-whale': 12, 'museum-ultra': 1})
        self.assertEqual(self.history.list(mode='museum')['runs'], [])
        first = self.history.list(mode='museum', boss='museum-mother-whale', limit=10)
        second = self.history.list(mode='museum', boss='museum-mother-whale', offset=10, limit=10)
        self.assertEqual([r['total'] for r in first['runs']], list(range(11, 1, -1)))
        self.assertTrue(first['has_more'])
        self.assertEqual([r['total'] for r in second['runs']], [1, 0])
        self.assertFalse(second['has_more'])
        self.assertEqual(self.history.list(mode='anomaly', boss='museum-mother-whale')['total'], 0)

    def test_migrate_only_legacy_report_once_using_original_mtime(self):
        legacy = self.root/'report.json'
        legacy.write_text(json.dumps(report()), encoding='utf-8')
        original_bytes = legacy.read_bytes()
        date = 1700000000.25
        os.utime(legacy, (date, date))
        (self.root/'smoke-report.json').write_text(json.dumps(report()), encoding='utf-8')
        initial = self.history.list(mode='museum', boss='museum-mother-whale')
        entry = initial['runs'][0]
        self.assertEqual(entry['kind'], 'legacy')
        self.assertEqual(entry['created_at'], timestamp(date))
        self.assertEqual(legacy.read_bytes(), original_bytes)
        self.assertEqual(self.history.get(entry['id'])['report'], report())
        legacy.write_text(json.dumps(report(total=50000)), encoding='utf-8')
        self.assertEqual(ReportHistory(self.root).list(mode='museum', boss='museum-mother-whale')['total'], 1)

    def test_empty_or_invalid_legacy_does_not_block_future_saves(self):
        (self.root/'report.json').write_text('{bad json', encoding='utf-8')
        self.assertEqual(self.history.list()['modes'], [])
        saved = self.history.save(report(count=1), 'manual')
        self.assertEqual(self.history.get(saved['id'])['kind'], 'manual')

    def test_concurrent_initialization_migrates_once_and_keeps_every_run(self):
        (self.root/'report.json').write_text(json.dumps(report()), encoding='utf-8')
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda i: ReportHistory(self.root).save(report(total=i)), range(16)))
        self.assertEqual(len({r['id'] for r in results}), 16)
        rows = self.history.list(mode='museum', boss='museum-mother-whale', limit=50)
        self.assertEqual(rows['total'], 17)
        self.assertEqual(sum(r['kind'] == 'legacy' for r in rows['runs']), 1)

    def test_cancelled_partial_run_keeps_requested_count_and_squads_grouped(self):
        partial = report(count=2)
        partial['completion'] = dict(reason='cancelled', requested_teams=5, returned_teams=2)
        saved = self.history.save(partial)
        row = self.history.get(saved['id'])['summary']
        self.assertEqual(row['completion_reason'], 'cancelled')
        self.assertEqual(row['requested_teams'], 5)
        self.assertEqual(len(row['teams']), 2)
        self.assertEqual(self.history.list(mode='museum', boss='museum-mother-whale')['total'], 1)

    def test_campaign_summary_does_not_claim_damage_objective(self):
        saved = self.history.save(report(mode='campaign', boss='campaign-stage', count=1))
        self.assertIsNone(self.history.get(saved['id'])['summary']['total'])
        self.assertEqual(self.history.get(saved['id'])['report']['total'], 12345)

    def test_invalid_ids_filters_pages_and_empty_runs_are_rejected(self):
        for ident in ('../report.json', 'x'*32, "' OR 1=1 --", ''):
            with self.assertRaises(ValueError):
                self.history.get(ident)
        for args in (dict(mode="museum' OR 1=1"), dict(boss='../report'), dict(offset=-1), dict(limit=51), dict(limit=0), dict(offset='nan')):
            with self.assertRaises(ValueError):
                self.history.list(**args)
        with self.assertRaises(ValueError):
            self.history.save(dict(teams=[]))
        self.assertIsNone(self.history.get('0'*32))
        self.assertEqual(self.history.list()['modes'], [])


class WorkerHistoryTests(unittest.TestCase):
    def test_manual_worker_saves_single_squad_even_in_five_squad_mode(self):
        import server
        with tempfile.TemporaryDirectory() as folder:
            result = report(count=1)
            result['settings']['teams'] = 5
            events = queue.Queue()
            with patch.object(server, 'ROOT', Path(folder)), patch.object(server.core, 'manual', return_value=result):
                server.worker({}, 'manual', events, threading.Event())
                done = events.get_nowait()
                saved = ReportHistory(Path(folder)/'private').get(done['result']['history']['id'])
                self.assertEqual(saved['kind'], 'manual')
                self.assertEqual(saved['summary']['requested_teams'], 1)
                self.assertEqual(saved['report']['settings']['teams'], 5)

    def test_worker_saves_before_done_without_polling_and_keeps_cancelled_partial(self):
        import server
        with tempfile.TemporaryDirectory() as folder:
            partial = report(count=2)
            partial['completion'] = dict(reason='cancelled', requested_teams=5, returned_teams=2)
            events = queue.Queue()
            cancel = threading.Event()
            cancel.set()
            with patch.object(server, 'ROOT', Path(folder)), patch.object(server.core, 'search', return_value=partial):
                server.worker({}, 'search', events, cancel)
                done = events.get_nowait()
                self.assertEqual(done['status'], 'done')
                ident = done['result']['history']['id']
                stored = ReportHistory(Path(folder)/'private').get(ident)
                self.assertEqual(stored['summary']['completion_reason'], 'cancelled')
                self.assertEqual(len(stored['report']['teams']), 2)
                self.assertNotIn('history', stored['report'])

    def test_worker_manual_history_failure_preserves_recommendation(self):
        import server
        events = queue.Queue()
        result = report(count=1)
        with patch.object(server.core, 'manual', return_value=result), patch.object(server, 'history_store', side_effect=OSError('Disk full')):
            server.worker({}, 'manual', events, threading.Event())
        done = events.get_nowait()
        self.assertEqual(done['status'], 'done')
        self.assertEqual(done['result']['teams'], result['teams'])
        self.assertIn('could not be saved', done['result']['history_error'])

    def test_worker_no_completed_team_is_not_saved(self):
        import server
        events = queue.Queue()
        with patch.object(server.core, 'search', side_effect=InterruptedError('No completed result')), patch.object(server, 'history_store') as store:
            server.worker({}, 'search', events, threading.Event())
        store.assert_not_called()
        self.assertEqual(events.get_nowait()['status'], 'cancelled')


class HistoryApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import server
        cls.server_module = server
        cls.temp = tempfile.TemporaryDirectory()
        cls.root_patch = patch.object(server, 'ROOT', Path(cls.temp.name))
        cls.root_patch.start()
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.port_patch = patch.object(server, 'PORT', cls.httpd.server_address[1])
        cls.port_patch.start()
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.saved = server.history_store().save(report())

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.port_patch.stop()
        cls.root_patch.stop()
        cls.temp.cleanup()

    def request(self, url, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.httpd.server_address[1])
        try:
            connection.request('GET', url, headers=headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_get_index_page_and_snapshot(self):
        status, index = self.request('/api/history')
        self.assertEqual(status, 200)
        self.assertEqual(index['runs'], [])
        status, page = self.request('/api/history?mode=museum&boss=museum-mother-whale&limit=10')
        self.assertEqual(status, 200)
        self.assertEqual(page['total'], 1)
        status, detail = self.request('/api/history/'+self.saved['id'])
        self.assertEqual(status, 200)
        self.assertEqual(detail['report'], report())
        self.assertEqual(detail['summary']['id'], self.saved['id'])

    def test_loopback_guard_and_query_validation(self):
        for headers in (dict(Host='evil.test'), dict(Origin='https://evil.test')):
            self.assertEqual(self.request('/api/history', headers)[0], 403)
        for url in ('/api/history?limit=9999', '/api/history?offset=-1', '/api/history?mode=museum&mode=anomaly', '/api/history?path=../report.json', '/api/history/../../report.json'):
            self.assertEqual(self.request(url)[0], 400)
        self.assertEqual(self.request('/api/history/'+'0'*32)[0], 404)


if __name__ == '__main__':
    unittest.main()
