"""Midreation CGI material and geometry regressions (no external renderer)."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build' / 'midi_generator'


def generate(brief):
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        spec = folder / 'spec.board'
        spec.write_text(brief, encoding='utf8')
        result = subprocess.run([str(EXE), str(spec), str(folder), '7', '1'],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise AssertionError(result.stderr)
        return (json.loads((folder/'design_1.json').read_text()),
                (folder/'design_1.obj').read_text())


class CGIRealismTests(unittest.TestCase):
    def test_weighted_keyboard_has_recessed_parts_and_materials(self):
        model, obj = generate('CONTROLLERTYPE controller=keyboard-synth\n'
                              'KEYBED keys=61 type=weighted\n')
        self.assertEqual(sum(p['type'].endswith('_key') for p in model['parts']), 61)
        self.assertGreater(obj.count('v '), 4000)
        self.assertIn('#mr ', obj)
        materials = {line.split('#mr ')[1] for line in obj.splitlines()
                     if line.startswith('v ') and '#mr ' in line}
        self.assertGreater(len(materials), 4)
        self.assertIn('cgi', model)

    def test_realism_is_procedurally_controllable(self):
        brief = ('CONTROLLERTYPE controller=keyboard-synth\n'
                 'KEYBED keys=25 type=unweighted\n')
        a, obj_a = generate(brief+'STYLE corner_radius=7 keybed_overhang=10\n')
        b, obj_b = generate(brief+'STYLE corner_radius=17 keybed_overhang=20\n')
        self.assertEqual(a['width'], b['width'])
        self.assertEqual(a['cgi']['keybedOverhang'], 10)
        self.assertEqual(b['cgi']['cornerRadius'], 17)
        self.assertNotEqual(obj_a, obj_b)

    def test_default_board_autofit_is_preserved(self):
        model, obj = generate('CONTROLLERTYPE controller=board\n'
                              'KNOBS count=8\nFADERS count=8\nPADS count=4\n')
        self.assertEqual(sum(p['type']=='knob' for p in model['parts']), 8)
        self.assertLess(model['width'], 1000)
        self.assertIn('#mr ', obj)

    def test_red_finish_is_supported(self):
        model, obj = generate('CONTROLLERTYPE controller=board\n'
                              'STYLE color=bright-red\nKNOBS count=4\n')
        self.assertEqual(model['bodyColor'], 'bright-red')
        self.assertIn('#mr ', obj)

    def test_web_studio_uses_material_vertex_stride(self):
        html = (ROOT/'studio'/'index.html').read_text()
        self.assertIn('vertexCount=output.length/11', html)
        self.assertIn('uFloor', html)
        self.assertIn('aMR', html)

if __name__=='__main__':
    unittest.main(verbosity=2)
