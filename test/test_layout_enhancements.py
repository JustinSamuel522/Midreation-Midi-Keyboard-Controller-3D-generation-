"""Additional regression coverage for Midreation's improved channel layouts."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / 'build' / 'midi_generator'


def generate(brief, variants=3):
    with tempfile.TemporaryDirectory() as tmp:
        directory=Path(tmp)
        spec=directory/'request.board'
        spec.write_text(brief,encoding='utf8')
        p=subprocess.run([str(EXE),str(spec),str(directory),'7',str(variants)],capture_output=True,text=True,timeout=30)
        if p.returncode:
            raise AssertionError(f'Generation failed: {p.stderr}')
        return [json.loads((directory/f'design_{i}.json').read_text()) for i in range(1,variants+1)]


def parts(model, typ):
    return [p for p in model['parts'] if p['type']==typ]


class ChannelBankTests(unittest.TestCase):
    def test_eight_channels_are_straight_and_paired(self):
        text=(ROOT/'examples'/'aligned-control-bank.board').read_text()
        for model in generate(text):
            knobs=parts(model,'knob');faders=parts(model,'fader')
            self.assertEqual(len(knobs),8);self.assertEqual(len(faders),8)
            self.assertEqual(len({round(x['z'],4) for x in knobs}),1)
            self.assertEqual(len({round(x['z'],4) for x in faders}),1)
            for k,f in zip(knobs,faders):
                self.assertAlmostEqual(k['x']+k['w']/2,f['x']+f['w']/2)
                self.assertLess(k['z']+k['d'],f['z'])
            self.assertGreater(model['triangles'],2000)

    def test_unequal_counts_work_without_presets(self):
        brief='''CONTROLLERTYPE controller=board
KNOBS count=11 zone=center
FADERS count=5 zone=center
PADS count=6 layout=grid zone=right
'''
        for model in generate(brief):
            self.assertEqual(len(parts(model,'knob')),11)
            self.assertEqual(len(parts(model,'fader')),5)
            self.assertEqual(len(parts(model,'pad')),6)

    def test_row_column_and_wheels_without_keybed(self):
        brief='''CONTROLLERTYPE controller=board
KNOBS count=3 layout=column zone=left
FADERS count=3 layout=row zone=center
WHEELS pitch=1 mod=1
'''
        model=generate(brief,1)[0]
        self.assertEqual(len(parts(model,'wheel')),2)
        self.assertEqual(len({round(x['x'],4) for x in parts(model,'knob')}),1)
        self.assertEqual(len({round(x['z'],4) for x in parts(model,'fader')}),1)

if __name__=='__main__':unittest.main(verbosity=2)
