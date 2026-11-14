"""Regression coverage for the desktop Auto Best Fit arrangement."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'build' / 'midi_generator'


def generate(spec, variants=1):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = folder / 'input.board'
        source.write_text(spec, encoding='utf-8')
        proc = subprocess.run(
            [str(ENGINE), str(source), str(folder), '7', str(variants)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode:
            raise AssertionError(proc.stderr)
        return [json.loads((folder / f'design_{i}.json').read_text())
                for i in range(1, variants + 1)]


def controls(model):
    return [p for p in model['parts'] if p['type'] not in
            ('body', 'white_key', 'black_key')]


def bounds(parts):
    return (min(p['x'] for p in parts), min(p['z'] for p in parts),
            max(p['x'] + p['w'] for p in parts),
            max(p['z'] + p['d'] for p in parts))


def intersects(a, b):
    return (a['x'] < b['x'] + b['w'] - .001 and
            a['x'] + a['w'] > b['x'] + .001 and
            a['z'] < b['z'] + b['d'] - .001 and
            a['z'] + a['d'] > b['z'] + .001)


DEFAULT_BOARD = '''CONTROLLERTYPE controller=board
KNOBS count=8 zone=auto
FADERS count=4 zone=auto
PADS count=4 zone=auto
BUTTONS count=6 zone=auto
'''


class AutoBestFitTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ENGINE.exists(), 'Build with cmake before testing.')

    def assert_clear(self, model):
        ps = controls(model)
        self.assertTrue(ps)
        for p in ps:
            self.assertGreaterEqual(p['x'], -.001)
            self.assertGreaterEqual(p['z'], -.001)
            self.assertLessEqual(p['x'] + p['w'], model['width'] + .001)
            self.assertLessEqual(p['z'] + p['d'], model['depth'] + .001)
        for i, a in enumerate(ps):
            for b in ps[i + 1:]:
                self.assertFalse(intersects(a, b), f"Collision: {a['type']} / {b['type']}")

    def assert_centered(self, model):
        left, top, right, bottom = bounds(controls(model))
        self.assertAlmostEqual(left, model['width'] - right, delta=0.01)
        self.assertAlmostEqual(top, model['depth'] - bottom, delta=0.01)

    def test_default_board_compacts_and_centers(self):
        variants = generate(DEFAULT_BOARD, 3)
        for model in variants:
            with self.subTest(variant=model['variant']):
                self.assertLess(model['width'], 420)
                self.assertLess(model['depth'], 260)
                self.assertEqual(len(controls(model)), 22)
                self.assert_clear(model)
                self.assert_centered(model)
        signatures = {
            (m['width'], m['depth'], tuple(
                (p['type'], p['x'], p['z']) for p in controls(m)))
            for m in variants
        }
        self.assertGreater(len(signatures), 1)

    def test_fixed_width_only(self):
        model = generate(DEFAULT_BOARD + 'BODY width=480\n')[0]
        self.assertEqual(model['width'], 480)
        self.assertGreater(model['depth'], 0)
        self.assert_centered(model)
        self.assert_clear(model)

    def test_fixed_depth_only(self):
        model = generate(DEFAULT_BOARD + 'BODY depth=220\n')[0]
        self.assertEqual(model['depth'], 220)
        self.assert_centered(model)
        self.assert_clear(model)

    def test_fixed_both_dimensions(self):
        model = generate(DEFAULT_BOARD + 'BODY width=650 depth=320\n')[0]
        self.assertEqual((model['width'], model['depth']), (650, 320))
        self.assert_centered(model)
        self.assert_clear(model)

    def test_paired_channels_stay_aligned(self):
        brief = '''CONTROLLERTYPE controller=board
KNOBS count=6 zone=auto layout=row
FADERS count=6 zone=auto layout=row
PADS count=4 zone=auto
'''
        model = generate(brief)[0]
        knobs = [p for p in controls(model) if p['type'] == 'knob']
        faders = [p for p in controls(model) if p['type'] == 'fader']
        self.assertEqual((len(knobs), len(faders)), (6, 6))
        for knob, fader in zip(knobs, faders):
            self.assertAlmostEqual(knob['x'] + knob['w']/2,
                                   fader['x'] + fader['w']/2)
            self.assertLess(knob['z'] + knob['d'], fader['z'])
        self.assert_clear(model)

    def test_explicit_zones_keep_existing_solver(self):
        spec = '''CONTROLLERTYPE controller=board
BODY width=420 depth=260
KNOBS count=4 zone=left
FADERS count=4 zone=right
'''
        model = generate(spec)[0]
        self.assertEqual((model['width'], model['depth']), (420, 260))
        self.assert_clear(model)


if __name__ == '__main__':
    unittest.main(verbosity=2)
