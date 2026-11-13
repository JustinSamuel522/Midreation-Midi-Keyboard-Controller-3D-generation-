"""Regression tests for physical keycap differences and 3D mesh output.
Run: python3 test/test_realistic_geometry.py after cmake --build build
"""
from pathlib import Path
import hashlib
import json
import math
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/'build'/'midi_generator'


def generate(brief):
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        spec=root/'spec.board'
        spec.write_text(brief,encoding='utf-8')
        result=subprocess.run([str(ENGINE),str(spec),str(root),'7','1'],
                              capture_output=True,text=True,timeout=30)
        if result.returncode:
            raise AssertionError(f'Generation failed: {result.stderr}')
        obj=(root/'design_1.obj').read_bytes()
        design=json.loads((root/'design_1.json').read_text(encoding='utf-8'))
        return design,obj


class MeshDetailTests(unittest.TestCase):
    def keybed(self,action):
        return generate(f'CONTROLLERTYPE controller=keyboard-synth\n'
                        f'KEYBED keys=25 type={action}\n'
                        'STYLE color=navy\n')

    def test_keybed_profiles_are_distinct_in_actual_obj(self):
        output={k:self.keybed(k) for k in ('unweighted','semi-weighted','weighted','hammer')}
        waterfall=output['unweighted'][0]
        self.assertEqual(waterfall['keycapProfile'],'waterfall')
        self.assertEqual(output['semi-weighted'][0]['keycapProfile'],'semi-weighted')
        self.assertEqual(output['weighted'][0]['keycapProfile'],'weighted')
        self.assertEqual(output['hammer'][0]['keycapProfile'],'weighted')
        # Ensures the OBJ surface itself changes, not just the displayed label.
        digests={name:hashlib.sha256(obj).hexdigest() for name,(_,obj) in output.items()}
        self.assertNotEqual(digests['unweighted'],digests['semi-weighted'])
        self.assertNotEqual(digests['semi-weighted'],digests['weighted'])
        self.assertEqual(digests['hammer'],digests['weighted'])
        for action,(model,obj) in output.items():
            self.assertEqual(len([p for p in model['parts'] if p['type'] in ('white_key','black_key')]),25)
            self.assertGreater(model['triangles'],3000)
            self.assertTrue(obj.startswith(b'# Midreation C++ procedural OBJ'))

    def test_complex_board_models_multiple_component_families(self):
        brief='''CONTROLLERTYPE controller=board
KNOBS count=4 zone=top-left
FADERS count=4 zone=top-left
PADS count=4 zone=right
BUTTONS regular=3 clicky=3 zone=bottom
DISPLAY count=1 zone=center
SWITCHES count=2 zone=top-right
'''
        model,obj=generate(brief)
        types={p['type'] for p in model['parts']}
        self.assertTrue({'knob','fader','pad','button','clicky','display','switch'}<=types)
        self.assertGreater(model['triangles'],6000)
        self.assertLess(len(obj),50_000_000)

    def test_reject_unknown_keybed_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);spec=folder/'invalid.board'
            spec.write_text('CONTROLLERTYPE controller=keyboard-synth\nKEYBED keys=61 type=banana\n')
            proc=subprocess.run([str(ENGINE),str(spec),str(folder)],capture_output=True,text=True,timeout=30)
            self.assertNotEqual(proc.returncode,0)
            self.assertIn('Unsupported keybed type',proc.stderr)

if __name__=='__main__':
    unittest.main(verbosity=2)
