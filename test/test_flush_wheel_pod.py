"""Regressions for the fully level left wheel housing and real wheel openings."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build' / 'midi_generator'


def run(spec):
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        source = folder / 'input.board'
        source.write_text(spec, encoding='utf-8')
        proc = subprocess.run([str(EXE), str(source), str(folder), '7', '1'],
                              capture_output=True, text=True, timeout=30)
        if proc.returncode:
            raise AssertionError(proc.stderr)
        model = json.loads((folder / 'design_1.json').read_text())
        vertices = [tuple(float(x) for x in line.split()[1:4])
                    for line in (folder / 'design_1.obj').read_text().splitlines()
                    if line.startswith('v ')]
        return model, vertices


class FlushWheelPodTests(unittest.TestCase):
    def sample(self, wheels):
        return run('CONTROLLERTYPE controller=keyboard-synth\n'
                   'KEYBED keys=61 type=weighted\n'
                   f'WHEELS pitch={int(wheels)} mod={int(wheels)}\n')

    def test_keyboard_has_flush_left_housing_with_or_without_wheels(self):
        for wheels in (False, True):
            with self.subTest(wheels=wheels):
                model, vertices = self.sample(wheels)
                keyleft = min(p['x'] for p in model['parts']
                              if p['type'] == 'white_key')
                keyback = min(p['z'] for p in model['parts']
                              if p['type'] == 'white_key')
                keyfront = max(p['z']+p['d'] for p in model['parts']
                               if p['type'] == 'white_key')
                # The left-side surface must reach the controls' 45-mm plane
                # well IN FRONT of the rear deck (where the old void appeared).
                left_deck = [y for x, y, z in vertices
                             if 1.0 < x < keyleft-1.0
                             and keyback+18.0 < z < keyfront+9.0
                             and 44.5 <= y <= 45.5]
                self.assertTrue(left_deck, 'Left wheel-side housing remains lowered')
                self.assertEqual(len([p for p in model['parts']
                                      if p['type'] == 'wheel']), 2 if wheels else 0)

    def test_wheels_clear_keybed_and_have_recessed_floor(self):
        model, vertices = self.sample(True)
        wheels = [p for p in model['parts'] if p['type'] == 'wheel']
        keyleft = min(p['x'] for p in model['parts']
                      if p['type'] == 'white_key')
        self.assertEqual(len(wheels), 2)
        self.assertLess(max(p['x']+p['w'] for p in wheels), keyleft)
        for wheel in wheels:
            cx = wheel['x'] + wheel['w']*.5
            cz = wheel['z'] + wheel['d']*.5
            wheel_verts = [y for x,y,z in vertices
                           if abs(x-cx) < 4 and abs(z-cz) < wheel['d']*.3]
            self.assertTrue(any(28.0 < y < 31.0 for y in wheel_verts),
                            'No deep wheel-well floor in the geometry')
            self.assertTrue(any(46 < y < 55 for y in wheel_verts),
                            'Wheel does not protrude through the upper deck')

    def test_standalone_board_not_changed(self):
        model, vertices = run('CONTROLLERTYPE controller=board\n'
                              'WHEELS pitch=1 mod=1\n'
                              'KNOBS count=4\n')
        self.assertEqual(len([p for p in model['parts']
                              if p['type'] == 'wheel']), 2)
        self.assertTrue(vertices)

if __name__ == '__main__':
    unittest.main(verbosity=2)
