"""Regression checks for Midreation's embedded pitch/mod wheel housing."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "build" / "midi_generator"


def generate(spec_text):
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        request = dest / "wheels.board"
        request.write_text(spec_text, encoding="utf8")
        p = subprocess.run([str(EXE), str(request), str(dest), "7", "1"],
                           capture_output=True, text=True, timeout=30)
        if p.returncode:
            raise AssertionError(p.stderr)
        model = json.loads((dest / "design_1.json").read_text())
        verts = []
        for line in (dest / "design_1.obj").read_text().splitlines():
            if line.startswith("v "):
                verts.append(tuple(float(x) for x in line.split()[1:4]))
        return model, verts


class WheelHousingTests(unittest.TestCase):
    def test_keyboard_wheels_are_recessed_and_supported(self):
        model, vertices = generate(
            "CONTROLLERTYPE controller=keyboard-synth\n"
            "KEYBED keys=61 type=weighted\n"
            "WHEELS pitch=1 mod=1\n")
        wheels = [p for p in model["parts"] if p["type"] == "wheel"]
        self.assertEqual(len(wheels), 2)
        self.assertEqual(model["depth"], 265)
        for wheel in wheels:
            in_region = [y for x, y, z in vertices
                         if wheel["x"]+4 < x < wheel["x"]+wheel["w"]-4
                         and wheel["z"]+3 < z < wheel["z"]+wheel["d"]-3]
            self.assertTrue(in_region)
            # A wheel now emerges through the full-height 45-mm deck.
            # The lower arc sits in the deep 29-mm well, not on a shelf.
            self.assertGreater(max(in_region), 46.0)
            self.assertLess(max(in_region), 55.0)
            self.assertTrue(any(height < 38.0 for height in in_region))

    def test_join_fills_side_gap(self):
        model, vertices = generate(
            "CONTROLLERTYPE controller=keyboard-synth\n"
            "KEYBED keys=61 type=weighted\n"
            "WHEELS pitch=1 mod=1\n")
        keys = [p for p in model["parts"] if p["type"] == "white_key"]
        rear = min(p["z"] for p in keys)
        # Filled shoulder just ahead of the rear deck, left of the keybed.
        joints = [y for x, y, z in vertices
                  if 17 < x < 55 and rear-17 < z < rear+3]
        self.assertTrue(any(y > 30.0 for y in joints), "Wheel-side panel still has a gap")

    def test_board_wheels_still_work_without_keybed(self):
        model, vertices = generate(
            "CONTROLLERTYPE controller=board\n"
            "WHEELS pitch=1 mod=1\nKNOBS count=4\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "wheel"]), 2)
        self.assertTrue(vertices)

if __name__ == "__main__":
    unittest.main(verbosity=2)
