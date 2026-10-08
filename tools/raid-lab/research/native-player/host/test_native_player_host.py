"""Safety gates for the staged Unity player host; tests never launch a game."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


MODULE = Path(__file__).with_name('native_player_host.py')
spec = importlib.util.spec_from_file_location('native_player_host', MODULE)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PlayerHostSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.private = Path(self.temp.name) / 'private'
        self.root = self.private / 'native-player-test'
        self.game = self.root / 'NIKKE/NIKKE/game'
        self.game.mkdir(parents=True)
        (self.root / 'profile').mkdir()
        self.files = {}
        for name in sorted(host.REQUIRED_FILES):
            path = self.game / name
            path.write_bytes(('fixture-' + name).encode())
            self.files[name] = {'path': str(path), 'sha256': sha(path)}
        self.bootstrap = self.root / 'bootstrap-receipt.json'
        self.network = self.root / 'network-receipt.json'
        self.bootstrap.write_text(json.dumps({
            'schema_version': 1, 'mode': 'unity_player_bootstrap',
            'sandbox_root': str(self.root), 'private_desktop_guard': True,
            'artifacts': {'nikkeBase.dll': self.files['nikkeBase.dll']['sha256']}}))
        self.network.write_text(json.dumps({
            'schema_version': 1, 'mode': 'deny_all', 'sandbox_root': str(self.root),
            'registry_mode': 'sandbox', 'known_folder_mode': 'sandbox',
            'self_test_passed': True,
            'artifacts': {'OfflineNetwork.dll': self.files['OfflineNetwork.dll']['sha256']}}))
        self.config = self.root / 'sandbox-player.json'
        self.value = {
            'schema_version': 1, 'sandbox_root': str(self.root),
            'game_executable': str(self.game / 'nikke.exe'),
            'working_directory': str(self.game),
            'scratch_root': str(self.root / 'profile'),
            'output_dir': str(self.root / 'probe-output'),
            'max_seconds': 30, 'args': ['-screen-fullscreen', '0'],
            'expected_files': self.files,
            'bootstrap_receipt': str(self.bootstrap),
            'network_receipt': str(self.network)}
        self.write_config()
        self.private_patch = patch.object(host, 'PRIVATE', self.private)
        self.private_patch.start()
        self.addCleanup(self.private_patch.stop)

    def write_config(self):
        self.config.write_text(json.dumps(self.value, indent=2), encoding='utf-8')

    def test_valid_plan_is_hash_bound_and_does_not_launch(self):
        plan = host.validate(self.config)
        self.assertEqual(plan['network_mode'], 'deny_all')
        self.assertEqual(plan['backend_mode'], 'none')
        self.assertEqual(len(plan['plan_sha256']), 64)
        self.assertEqual(plan['host_sha256'], sha(MODULE))
        self.assertEqual(plan['harness_sha256'], sha(host.HARNESS))
        self.assertFalse((self.root / 'probe-output').exists())

    def test_diagnostic_bundle_must_be_complete_and_hash_bound(self):
        for name in host.DIAGNOSTIC_FILES:
            target = self.game / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(('probe-' + name).encode())
        with self.assertRaisesRegex(ValueError, 'requires diagnostic_files'):
            host.validate(self.config)
        self.value['diagnostic_files'] = {
            name: {'path': str(self.game / name), 'sha256': sha(self.game / name)}
            for name in host.DIAGNOSTIC_FILES}
        self.write_config()
        plan = host.validate(self.config)
        self.assertEqual(len(plan['diagnostic_files']), 4)
        (self.game / 'NKAB/dist/scene-probe.js').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            host.validate(self.config)

    def test_nonempty_output_is_rejected_before_run(self):
        output = self.root / 'probe-output'
        output.mkdir()
        (output / 'prior-run.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'must be empty'):
            host.validate(self.config)
        # The already validated worker may see the parent's assignment gate.
        self.assertEqual(host.validate(self.config, fresh_output=False)['output_dir'], str(output))

    def test_staged_player_mutation_is_rejected(self):
        (self.game / 'GameAssembly.dll').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            host.validate(self.config)

    def test_guard_receipt_must_bind_exact_dll(self):
        record = json.loads(self.network.read_text())
        record['artifacts']['OfflineNetwork.dll'] = '0' * 64
        self.network.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'receipt artifact mismatch'):
            host.validate(self.config)

    def test_production_launcher_or_account_blocks_plan(self):
        (self.root / 'local-account.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Production account or launcher'):
            host.validate(self.config)

    def test_paths_cannot_escape_sandbox(self):
        self.value['output_dir'] = str(self.private / 'outside')
        self.write_config()
        with self.assertRaisesRegex(ValueError, 'escapes sandbox'):
            host.validate(self.config)

    def test_run_requires_exact_integration_ready_receipt_before_launch(self):
        plan = host.validate(self.config)
        ready = self.root / 'ready.json'
        ready.write_text(json.dumps({'schema_version': 1, 'status': 'integration_ready',
                                     'sandbox_root': str(self.root),
                                     'plan_sha256': '0' * 64}))
        with patch.object(host.importlib.util, 'spec_from_file_location',
                          side_effect=AssertionError('desktop must not open')):
            with self.assertRaisesRegex(ValueError, 'does not bind'):
                host.execute(self.config, ready)
        self.assertFalse((self.root / 'probe-output').exists())

    def test_worker_receives_absolute_config_after_cwd_change(self):
        plan = host.validate(self.config)
        ready = self.root / 'ready.json'
        ready.write_text(json.dumps({'schema_version': 1, 'status': 'integration_ready',
                                     'sandbox_root': str(self.root),
                                     'plan_sha256': plan['plan_sha256']}))
        seen = {}

        class FakeDesktop:
            name = 'NikkeCatalogProbe_fixture'

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def popen(self, args, *, cwd):
                seen['args'] = args
                seen['cwd'] = cwd
                raise RuntimeError('fixture stopped before process start')

        fake_module = SimpleNamespace(IsolatedDesktop=FakeDesktop)
        fake_spec = SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            with patch.object(host.importlib.util, 'spec_from_file_location', return_value=fake_spec), \
                 patch.object(host.importlib.util, 'module_from_spec', return_value=fake_module):
                with self.assertRaisesRegex(RuntimeError, 'before process start'):
                    host.execute(Path('sandbox-player.json'), Path('ready.json'))
        finally:
            os.chdir(previous)
        config_arg = seen['args'][seen['args'].index('--config') + 1]
        self.assertEqual(config_arg, str(self.config.resolve()))
        self.assertEqual(seen['cwd'], Path(plan['output_dir']))

    def test_run_has_hard_timeout_cap(self):
        self.value['max_seconds'] = host.MAX_SECONDS + 1
        self.write_config()
        with self.assertRaisesRegex(ValueError, 'max_seconds'):
            host.validate(self.config)


if __name__ == '__main__':
    unittest.main()
