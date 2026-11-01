"""Real cross-process Windows lease controls; no game or sandbox is launched."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from native_runner_lease import NativeRunnerLease, RunnerBusy


@unittest.skipUnless(os.name == "nt", "Windows kernel lease")
class LeaseTests(unittest.TestCase):
    def test_excludes_other_process_and_releases_without_changing_file(self):
        with tempfile.TemporaryDirectory(prefix="native-lease-test-") as folder:
            path = Path(folder) / "runner.lock"
            path.write_bytes(b"preserved coordination data")
            code = (
                "import sys; from pathlib import Path; "
                "from native_runner_lease import NativeRunnerLease, RunnerBusy\n"
                "try:\n"
                " with NativeRunnerLease(Path(sys.argv[1])): print('acquired')\n"
                "except RunnerBusy: print('busy')\n"
            )
            def child():
                return subprocess.run([sys.executable, "-c", code, str(path)],
                                      cwd=Path(__file__).parent, capture_output=True,
                                      text=True, timeout=10, check=True).stdout.strip()
            with NativeRunnerLease(path):
                self.assertEqual(child(), "busy")
            self.assertEqual(child(), "acquired")
            self.assertEqual(path.read_bytes(), b"preserved coordination data")

    def test_same_process_second_handle_is_excluded_and_exception_releases(self):
        with tempfile.TemporaryDirectory(prefix="native-lease-test-") as folder:
            path = Path(folder) / "runner.lock"
            with self.assertRaisesRegex(ValueError, "test exception"):
                with NativeRunnerLease(path):
                    with self.assertRaises(RunnerBusy):
                        NativeRunnerLease(path).acquire()
                    raise ValueError("test exception")
            with NativeRunnerLease(path) as lease:
                with self.assertRaisesRegex(RuntimeError, "already held"):
                    lease.acquire()
            lease.close()

    def test_rejects_relative_or_missing_parent(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            NativeRunnerLease(Path("runner.lock")).acquire()
        with tempfile.TemporaryDirectory(prefix="native-lease-test-") as folder:
            with self.assertRaisesRegex(ValueError, "already exist"):
                NativeRunnerLease(Path(folder) / "missing" / "runner.lock").acquire()


if __name__ == "__main__":
    unittest.main()
