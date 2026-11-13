#!/usr/bin/env python3
"""Run with python3 tests/test_generator.py after building the C++ generator."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
ENGINE = BASE / 'build' / 'midi_generator'


def gen(spec, variants=2, seed=7):
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        path = work / 'input.board'
        path.write_text(spec, encoding='utf8')
        result = subprocess.run([str(ENGINE), str(path), str(work), str(seed), str(variants)],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            return result, []
        data = [json.loads((work / f'design_{i}.json').read_text()) for i in range(1, variants + 1)]
        for i in range(1, variants + 1):
            assert (work / f'design_{i}.obj').stat().st_size > 0
            assert (work / f'design_{i}.svg').stat().st_size > 0
        return result, data


def collision(a, b):
    return a['x'] < b['x'] + b['w'] and a['x'] + a['w'] > b['x'] and a['z'] < b['z'] + b['d'] and a['z'] + a['d'] > b['z']


class ProceduralGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ENGINE.exists(), 'Build first: cmake -S . -B build && cmake --build build')

    def assert_valid(self, model):
        parts = model['parts']
        width, depth = model['width'], model['depth']
        self.assertGreater(model['triangles'], 0)
        for p in parts:
            self.assertGreater(p['w'], 0)
            self.assertGreater(p['d'], 0)
            self.assertGreaterEqual(p['x'], -0.001)
            self.assertGreaterEqual(p['z'], -0.001)
            self.assertLessEqual(p['x'] + p['w'], width + 0.001)
            self.assertLessEqual(p['z'] + p['d'], depth + 0.001)
        # Keyboard black keys intentionally overlap adjacent white keys and the body supports everything.
        controls = [p for p in parts if p['type'] not in ('body', 'white_key', 'black_key')]
        for i, a in enumerate(controls):
            for b in controls[i + 1:]:
                self.assertFalse(collision(a, b), f"Overlap: {a['type']} with {b['type']}")

    def test_all_presentation_examples(self):
        for name in ('simple', 'medium', 'complex'):
            with self.subTest(name=name):
                text = (BASE / 'examples' / f'{name}.board').read_text()
                res, results = gen(text)
                self.assertEqual(res.returncode, 0, res.stderr)
                self.assertEqual(len(results), 2)
                for model in results:
                    self.assert_valid(model)

    def test_arbitrary_37_key_design(self):
        res, data = gen((BASE / 'examples' / 'custom-37key.board').read_text())
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(sum(x['type'].endswith('_key') for x in data[0]['parts']), 37)
        self.assertEqual(sum(x['type'] == 'knob' for x in data[0]['parts']), 7)
        self.assertEqual(sum(x['type'] == 'fader' for x in data[0]['parts']), 5)
        for x in data:self.assert_valid(x)

    def test_auto_dimensions_and_partial_brief(self):
        res, data = gen((BASE / 'examples' / 'minimal-input.board').read_text(), 3)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(len(data), 3)
        self.assertEqual(sum(x['type'] == 'pad' for x in data[0]['parts']), 16)
        for x in data:self.assert_valid(x)

    def test_foot_controller(self):
        res, data = gen((BASE / 'examples' / 'foot-controller.board').read_text())
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(sum(x['type'] == 'footswitch' for x in data[0]['parts']), 8)
        self.assert_valid(data[0])

    def test_layout_variants_and_seed_determinism(self):
        spec = (BASE / 'examples' / 'medium.board').read_text()
        res, data = gen(spec, 3, 7)
        self.assertEqual(res.returncode, 0, res.stderr)
        coords = [[(x['type'], x['x'], x['z']) for x in m['parts']] for m in data]
        self.assertGreater(len({tuple(map(tuple, v)) for v in coords}), 1)
        again, data2 = gen(spec, 3, 7)
        self.assertEqual(again.returncode, 0)
        self.assertEqual(coords, [[(x['type'], x['x'], x['z']) for x in m['parts']] for m in data2])

    def test_unsupported_and_impossible_specs_are_rejected(self):
        for spec in ('POTATO count=5',
                     'CONTROLLERTYPE controller=keyboard\nBODY width=300 depth=180\nKEYBED keys=88'):
            result, _ = gen(spec, 1)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Error:', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
