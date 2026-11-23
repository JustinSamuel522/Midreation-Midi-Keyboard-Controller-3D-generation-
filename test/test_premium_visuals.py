"""Premium keyboard proportions, deep chassis and bright-red finish.
Run after building the project: python3 -m unittest discover -s test -v
"""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
ENGINE=ROOT/'build'/'midi_generator'


def render(spec):
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)
        (p/'test.board').write_text(spec, encoding='utf8')
        run=subprocess.run([str(ENGINE),str(p/'test.board'),str(p),'7','1'],
                           capture_output=True,text=True,timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        model=json.loads((p/'design_1.json').read_text())
        obj=(p/'design_1.obj').read_text()
        return model,obj


def get(model,t):
    return [part for part in model['parts'] if part['type']==t]


class PremiumVisualTests(unittest.TestCase):
    def test_auto_keyboard_is_265_deep_without_extra_controls(self):
        m,_=render('CONTROLLERTYPE controller=keyboard-synth\nKEYBED keys=61 type=semi-weighted\n')
        self.assertAlmostEqual(m['depth'],265.,places=1)
        whites=get(m,'white_key')
        self.assertEqual(len(whites),36)
        self.assertTrue(all(22.0<=p['w']<=24.0 for p in whites))
        self.assertTrue(all(135<=p['d']<=150 for p in whites))
        self.assertGreater(min(p['z'] for p in whites),80)
        self.assertLess(max(p['z']+p['d'] for p in whites),m['depth'])

    def test_88_key_begins_with_a_natural(self):
        m,_=render('CONTROLLERTYPE controller=keyboard-synth\nKEYBED keys=88 type=weighted\n')
        seq=[p['type'] for p in m['parts'] if p['type'].endswith('_key')]
        self.assertEqual(seq[:4],['white_key','black_key','white_key','white_key'])
        self.assertEqual(len(get(m,'white_key')),52)

    def test_user_defined_dimensions_are_preserved(self):
        spec='CONTROLLERTYPE controller=keyboard-synth\nBODY width=1070 depth=360\nKEYBED keys=61\n'
        m,_=render(spec)
        self.assertAlmostEqual(m['width'],1070)
        self.assertAlmostEqual(m['depth'],360)

    def test_bright_red_is_painted_into_3d_export(self):
        m,obj=render('CONTROLLERTYPE controller=board\nSTYLE color=bright-red\nKNOBS count=4\n')
        body=get(m,'body')[0]
        self.assertEqual(body['color'],'#f5131c')
        self.assertIn('# Midreation C++ procedural OBJ',obj)

    def test_chassis_is_physically_taller_than_old_flat_shell(self):
        m,obj=render('CONTROLLERTYPE controller=keyboard-synth\nKEYBED keys=25 type=weighted\n')
        ys=[float(line.split()[2]) for line in obj.splitlines() if line.startswith('v ')]
        self.assertGreater(max(ys)-min(ys),36.)
        self.assertLess(min(ys),0.) # underside rubber feet
        self.assertGreater(m['triangles'],3000)

    def test_custom_board_stays_compact_without_keybed(self):
        m,_=render('CONTROLLERTYPE controller=board\nKNOBS count=8 zone=auto\nFADERS count=4 zone=auto\n')
        self.assertLess(m['width'],420.)
        self.assertLess(m['depth'],260.)

if __name__=='__main__':
    unittest.main(verbosity=2)
