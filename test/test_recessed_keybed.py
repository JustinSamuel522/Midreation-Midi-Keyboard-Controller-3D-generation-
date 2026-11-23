"""Regression coverage for Midreation's separate keyboard housing and keybed."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "build" / "midi_generator"


def build(brief):
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        spec = folder / "input.board"
        spec.write_text(brief, encoding="utf8")
        run = subprocess.run([str(EXE), str(spec), str(folder), "7", "1"],
                             capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        model = json.loads((folder / "design_1.json").read_text())
        verts = []
        for line in (folder / "design_1.obj").read_text().splitlines():
            if line.startswith("v "):
                xyz = list(map(float, line.split()[1:4]))
                verts.append(xyz)
        return model, verts


class RecessedKeybedTests(unittest.TestCase):
    def test_raised_upper_housing_and_overhang(self):
        model, vertices = build("CONTROLLERTYPE controller=keyboard-synth\n"
                                "KEYBED keys=61 type=semi-weighted\n")
        white = [p for p in model["parts"] if p["type"] == "white_key"]
        black = [p for p in model["parts"] if p["type"] == "black_key"]
        self.assertEqual(len(white) + len(black), 61)
        rear = min(p["z"] for p in white)
        lx = min(p["x"] for p in white)
        rx = max(p["x"] + p["w"] for p in white)
        cx = (lx + rx) / 2
        # Chassis top behind the keybed is visibly above the black-key caps.
        rear_deck = [v[1] for v in vertices if abs(v[0] - cx) < 4 and v[2] < rear - 9]
        self.assertTrue(rear_deck and max(rear_deck) >= 44.5)
        # There must also be a substantial bridge projecting INTO the keybed.
        lip = [v[1] for v in vertices if abs(v[0] - cx) < 5 and rear + 2 <= v[2] <= rear + 17]
        self.assertTrue(lip and max(lip) >= 44.5)
        self.assertEqual(model["depth"], 265)

    def test_88_key_and_wheel_clearance(self):
        model, vertices = build("CONTROLLERTYPE controller=keyboard-synth\n"
                                "KEYBED keys=88 type=weighted\nWHEELS pitch=1 mod=1\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"].endswith("_key")]), 88)
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "wheel"]), 2)
        self.assertTrue(vertices)

    def test_standalone_board_remains_supported(self):
        model, vertices = build("CONTROLLERTYPE controller=board\n"
                                "KNOBS count=8\nFADERS count=4\nPADS count=4\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "white_key"]), 0)
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "knob"]), 8)
        self.assertGreater(len(vertices), 1000)

    def test_explicit_dimensions_still_respected(self):
        model, _ = build("CONTROLLERTYPE controller=keyboard-synth\n"
                         "BODY width=1070 depth=340\nKEYBED keys=61 type=weighted\n")
        self.assertEqual(model["width"], 1070)
        self.assertEqual(model["depth"], 340)


if __name__ == "__main__":
    unittest.main(verbosity=2)
