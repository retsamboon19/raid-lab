"""Guard against the installed bridge's undersized static value-type getter."""

from pathlib import Path
import re
import sqlite3
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


class TransporterBridgeGuardTest(unittest.TestCase):
    def test_large_static_value_type_never_uses_bridge_getter(self):
        with sqlite3.connect(ROOT / "client-decompiled/index/installed-2df7134a/client.sqlite") as db:
            row = db.execute(
                "SELECT parent FROM classes WHERE name=?",
                ("NK.Spot.Data.NKSpotDataTransporter",),
            ).fetchone()
            self.assertEqual(row, ("System.ValueType",))
            last_offset = db.execute(
                "SELECT MAX(offset) FROM fields WHERE class_name=? AND (flags & 0x10)=0",
                ("NK.Spot.Data.NKSpotDataTransporter",),
            ).fetchone()[0]
            self.assertGreater(last_offset, 100)

        for name in ("battle_probe.js", "mechanics_probe.js", "mechanics_fixture.js"):
            with self.subTest(probe=name):
                probe = (HERE / name).read_text(encoding="utf-8")
                unsafe_getters = re.findall(
                    r'\.field\("DataTransporter"\)\.value\b(?!\s*=)', probe
                )
                self.assertEqual(unsafe_getters, [], "DataTransporter static getter overruns an 8-byte buffer")


if __name__ == "__main__":
    unittest.main()
