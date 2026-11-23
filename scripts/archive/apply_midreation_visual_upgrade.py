#!/usr/bin/env python3
"""Upgrade the Midreation keyboard proportions, 3D chassis, lighting, and colors.

Run from the Midreation repository root:
    python3 scripts/archive/apply_midreation_visual_upgrade.py
    cmake -S . -B build && cmake --build build
    python3 -m unittest discover -s test -p 'test_*.py' -v

Compatible with the main.cpp / studio/index.html published on 2026-11-13
(after the Auto Best Fit update). Runs all validations before writing any files,
and refuses unknown file versions instead of risking accidental corruption.
"""
from pathlib import Path
import sys

ROOT = Path.cwd()
ENGINE = ROOT / 'src' / 'main.cpp'
STUDIO = ROOT / 'studio' / 'index.html'
TEST = ROOT / 'test' / 'test_premium_visuals.py'


def replace_once(content, original, replacement, label):
    n = content.count(original)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one matching section, found {n}. "
                           "No files were changed. The source may be a different revision.")
    return content.replace(original, replacement, 1)


def apply_engine(source):
    s = source
    s = replace_once(s,
        'constexpr double PI = 3.14159265358979323846;\n',
        '''constexpr double PI = 3.14159265358979323846;
// Consistent physical surface height for the chassis, controls and keybed.
constexpr double DECK_HEIGHT = 30.0;
// A compact keyboard begins near 265 mm deep. Additional control banks may
// require the enclosure to grow in the normal collision-free layout solver.
double keyboardKeyDepth(double enclosureDepth){
  return min(148.0, max(105.0, enclosureDepth*.55));
}
// 88-key pianos start at A; common compact keybeds start at C. The 76-key
// profile starts on E, matching a common extended-keyboard layout.
int keyboardStartSemitone(int count){return count==88?9:(count==76?4:0);}
bool blackKeySemitone(int semitone){
  const int p=(semitone%12+12)%12;
  return p==1||p==3||p==6||p==8||p==10;
}
int keyboardWhiteCount(int count){
  int n=0;for(int i=0;i<count;i++)if(!blackKeySemitone(i+keyboardStartSemitone(count)))++n;
  return n;
}
''', 'C++ physical dimensions helpers')

    s = replace_once(s,
        'if(!s.fixedWidth)s.width=(s.keys?max(340.,s.keys*16.0+110.):(s.kind.find("foot")!=string::npos?360.:420.));\n'
        '  if(!s.fixedDepth)s.depth=(s.keys?340.:(s.kind.find("foot")!=string::npos?200.:260.));',
        '''if(!s.fixedWidth)s.width=(s.keys?
      max(340.,keyboardWhiteCount(s.keys)*23.5+((s.pitch+s.mod)?80.:24.)+20.):
      (s.kind.find("foot")!=string::npos?360.:420.));
  if(!s.fixedDepth)s.depth=(s.keys?265.:(s.kind.find("foot")!=string::npos?200.:260.));''',
        'automatic keyboard dimensions')

    s = replace_once(s,
        'x=side; z=spec.depth*.55;\n      w=spec.width-side-20;d=spec.depth*.39;',
        '''x=side;
       d=keyboardKeyDepth(spec.depth); // target ~146 mm playable white-key length
       z=spec.depth-d-12.;        // keys finish close to the front lip
       w=spec.width-side-20.;''',
        'keybed front and back placement')

    s = replace_once(s,
        'int whites=0;for(int i=0;i<n;i++)if(!isBlack(i))whites++;',
        'int whites=keyboardWhiteCount(n);',
        'white key width count')
    s = replace_once(s,
        'if(!isBlack(i)){add("white_key"',
        'if(!blackKeySemitone(i+keyboardStartSemitone(n))){add("white_key"',
        '88/76-key semitone offsets')
    s = replace_once(s,
        'double topLimit() const {return spec.keys?spec.depth*.53:spec.depth-margin;}',
        '''double topLimit() const {
    return spec.keys?spec.depth-keyboardKeyDepth(spec.depth)-20.:spec.depth-margin;
  }''', 'avoid overlapping the longer physical keybed')

    s = replace_once(s,
        '{"white",{.93,.94,.97}},{"ivory",{.93,.93,.89}},{"red",{.90,.26,.32}},{"blue",{.26,.50,.91}},',
        '{"white",{.93,.94,.97}},{"ivory",{.93,.93,.89}},{"red",{.90,.26,.32}},\n'
        '  {"bright-red",{.96,.075,.11}},{"blue",{.26,.50,.91}},',
        'bright-red procedural color')

    original_deck = 'double x=p.x,z=p.z,w=p.w,d=p.d,deck=19.;'
    if s.count(original_deck) != 2:
        raise RuntimeError('Expected two keycap deck declarations. No files were changed.')
    s = s.replace(original_deck,
                  'double x=p.x,z=p.z,w=p.w,d=p.d,deck=DECK_HEIGHT;')
    s = replace_once(s, 'constexpr double deck=19.;',
                     'constexpr double deck=DECK_HEIGHT;', 'component deck height')

    # The lower aluminum shell is now 30 mm high instead of 19 mm.
    old_body = '''        // Inset brushed enclosure with a chamfered outer silhouette, side cheek
        // materials, fastener heads, front bottom rail, and functional seam lines.
        roundedPrism(x,0,z,w,16.8,d,12,3.0,shade(c,.82));
        roundedPrism(x+2,14.9,z+2,w-4,4.1,d-4,10,1.0,shade(c,1.12));
        Vec3 side=l.spec.panels=="wood"?color("wood"):shade(c,.72);
        roundedPrism(x+1.8,3.4,z+14,5.3,10.7,d-28,2.2,1.0,side);
        roundedPrism(x+w-7.1,3.4,z+14,5.3,10.7,d-28,2.2,1.0,side);
        roundedPrism(x+8,3.7,z+d-5.1,w-16,6.4,3.1,1.0,.8,shade(c,.59));
        for(double px:{x+9,x+w-9})for(double pz:{z+10,z+d-10}){
          cylinder(px,19.0,pz,1.8,.35,color("steel"),16);
          cube(px-1,19.36,pz-.20,2,.16,.4,color("dark"));
        }
        // Vent slits along the rear edge, with light metal dividers.
        for(int i=0;i<7&&w>300;i++){
          double px=x+w*.39+i*8.5;
          roundedPrism(px,19.05,z+5,4.2,.17,12,1,.08,shade(c,.48));
        }'''
    new_body = '''        // Premium two-part enclosure. The taller tapered lower housing and
        // inset upper deck produce a tangible three-dimensional side profile.
        roundedPrism(x,0,z,w,26.1,d,12.5,3.8,shade(c,.77));
        roundedPrism(x+1.8,24.4,z+1.8,w-3.6,5.6,d-3.6,10.0,1.35,shade(c,1.12));
        Vec3 side=l.spec.panels=="wood"?color("wood"):shade(c,.71);
        roundedPrism(x+1.8,3.8,z+14,5.5,19.3,d-28,2.4,1.0,side);
        roundedPrism(x+w-7.3,3.8,z+14,5.5,19.3,d-28,2.4,1.0,side);
        // Front rail, split-line, and small recessed toe-kick.
        roundedPrism(x+7,5.1,z+d-5.3,w-14,13.6,3.2,1.2,.85,shade(c,.57));
        roundedPrism(x+9,23.2,z+d-4.8,w-18,.75,2.2,.9,.18,shade(color("black"),.82));
        for(double px:{x+9,x+w-9})for(double pz:{z+10,z+d-10}){
          cylinder(px,DECK_HEIGHT,pz,1.8,.35,color("steel"),16);
          cube(px-1,DECK_HEIGHT+.36,pz-.20,2,.16,.4,color("dark"));
        }
        // Rubber feet are modeled below the case, not painted onto the surface.
        for(double fx:{x+23,x+w-23})for(double fz:{z+20,z+d-20})
          roundedPrism(fx-11,-4.0,fz-7,22.,4.,14.,3.0,.8,shade(color("black"),.63));
        // Vent slots on the rear deck and restrained industrial detailing.
        for(int i=0;i<7&&w>300;i++){
          double px=x+w*.39+i*8.5;
          roundedPrism(px,DECK_HEIGHT+.05,z+5,4.2,.17,12,1,.08,shade(c,.48));
        }
        // A keybed has its own recessed dark tray, end cheeks, and rear stop
        // rail. These parts stay correctly aligned even when the key count changes.
        if(l.spec.keys){
          double minX=1e100,minZ=1e100,maxX=-1e100,maxZ=-1e100;
          for(const Part& key:l.parts)if(key.type=="white_key"){
            minX=min(minX,key.x);minZ=min(minZ,key.z);
            maxX=max(maxX,key.x+key.w);maxZ=max(maxZ,key.z+key.d);
          }
          if(minX<maxX){
            const double kw=maxX-minX,kd=maxZ-minZ;
            roundedPrism(minX-3.2,deck-.3,minZ-3.2,kw+6.4,.85,kd+5.5,2.8,.25,shade(color("black"),1.00));
            roundedPrism(minX-4.5,deck+.05,minZ-7,kw+9,2.3,3.2,1.1,.55,shade(c,.64));
            roundedPrism(minX-5.8,deck-.15,minZ-2,3.6,3.1,kd+3,1.1,.55,side);
            roundedPrism(maxX+2.1,deck-.15,minZ-2,3.6,3.1,kd+3,1.1,.55,side);
          }
        }'''
    s = replace_once(s,old_body,new_body,'full chassis geometry section')

    # Tiny physical highlights help show that keys have raised, molded edges.
    s = replace_once(s,
        'roundedPrism(x+.30,deck+4.2,z+.8,w-.60,1.25,d-1.65,1.1,.37,shade(ivory,1.07));',
        '''roundedPrism(x+.30,deck+4.2,z+.8,w-.60,1.25,d-1.65,1.1,.37,shade(ivory,1.07));
      roundedPrism(x+.40,deck+5.48,z+2.2,w-.80,.10,1.2,.23,.04,shade(ivory,.83));''',
        'waterfall-key pivot highlights')
    s = replace_once(s,
        'roundedPrism(x+1.0,deck+4.6+thick-1.9,z+d-8,w-2,1.6,6.4,1.3,.65,shade(base,1.1));',
        '''roundedPrism(x+1.0,deck+4.6+thick-1.9,z+d-8,w-2,1.6,6.4,1.3,.65,shade(base,1.1));
    roundedPrism(x+1.4,deck+4.6+thick+.55,z+3,w-2.8,.12,d-13,1.0,.04,shade(base,1.14));''',
        'black-key top highlights')
    return s


def apply_studio(source):
    s = source
    s = replace_once(s,
        "{name:'Midnight black',value:'black',hex:'#11131b'},{name:'Cloud white'",
        "{name:'Midnight black',value:'black',hex:'#11131b'},{name:'Bright red',value:'bright-red',hex:'#f5131c'},{name:'Cloud white'",
        'bright-red finish swatch')

    old_shader = '''float light=0.46+0.14*max(n.y,0.0)+0.50*max(dot(n,key),0.0)+0.14*max(dot(n,fill),0.0);
 vec3 h=normalize(key+normalize(uEye-vPosition));
 float glint=0.18*pow(max(dot(n,h),0.0),36.0);
 gl_FragColor=vec4(clamp(vColor*light+vec3(glint),0.0,1.0),1.0);'''
    new_shader = '''vec3 viewDir=normalize(uEye-vPosition);
 float diffuse=0.41+0.21*max(n.y,0.0)+0.47*max(dot(n,key),0.0)+0.14*max(dot(n,fill),0.0);
 vec3 halfDir=normalize(key+viewDir);
 float highlight=pow(max(dot(n,halfDir),0.0),54.0);
 float edge=pow(1.0-max(dot(n,viewDir),0.0),3.0);
 // A narrow showroom highlight, gentle edge reflection, and soft hemisphere
 // lighting make the same OBJ geometry read as lacquered/painted hardware.
 vec3 shaded=vColor*diffuse+vec3(0.16*highlight+0.045*edge);
 gl_FragColor=vec4(clamp(shaded,0.0,1.0),1.0);'''
    s = replace_once(s,old_shader,new_shader,'3D preview lighting')
    s = replace_once(s,
        'Leave dimensions blank to fit a compact, centered enclosure around your controls. Specify either dimension to lock it. You can return to any step and regenerate.',
        'Leave dimensions blank for a compact, centered enclosure. Keyboards start near 265 mm deep and can grow to fit more controls. Specify either dimension to lock it.',
        'sizing explanation')
    return s


TEST_TEXT = '''"""Premium keyboard proportions, deep chassis and bright-red finish.
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
        m,_=render('CONTROLLERTYPE controller=keyboard-synth\\nKEYBED keys=61 type=semi-weighted\\n')
        self.assertAlmostEqual(m['depth'],265.,places=1)
        whites=get(m,'white_key')
        self.assertEqual(len(whites),36)
        self.assertTrue(all(22.0<=p['w']<=24.0 for p in whites))
        self.assertTrue(all(135<=p['d']<=150 for p in whites))
        self.assertGreater(min(p['z'] for p in whites),80)
        self.assertLess(max(p['z']+p['d'] for p in whites),m['depth'])

    def test_88_key_begins_with_a_natural(self):
        m,_=render('CONTROLLERTYPE controller=keyboard-synth\\nKEYBED keys=88 type=weighted\\n')
        seq=[p['type'] for p in m['parts'] if p['type'].endswith('_key')]
        self.assertEqual(seq[:4],['white_key','black_key','white_key','white_key'])
        self.assertEqual(len(get(m,'white_key')),52)

    def test_user_defined_dimensions_are_preserved(self):
        spec='CONTROLLERTYPE controller=keyboard-synth\\nBODY width=1070 depth=360\\nKEYBED keys=61\\n'
        m,_=render(spec)
        self.assertAlmostEqual(m['width'],1070)
        self.assertAlmostEqual(m['depth'],360)

    def test_bright_red_is_painted_into_3d_export(self):
        m,obj=render('CONTROLLERTYPE controller=board\\nSTYLE color=bright-red\\nKNOBS count=4\\n')
        body=get(m,'body')[0]
        self.assertEqual(body['color'],'#f5131c')
        self.assertIn('# Midreation C++ procedural OBJ',obj)

    def test_chassis_is_physically_taller_than_old_flat_shell(self):
        m,obj=render('CONTROLLERTYPE controller=keyboard-synth\\nKEYBED keys=25 type=weighted\\n')
        ys=[float(line.split()[2]) for line in obj.splitlines() if line.startswith('v ')]
        self.assertGreater(max(ys)-min(ys),36.)
        self.assertLess(min(ys),0.) # underside rubber feet
        self.assertGreater(m['triangles'],3000)

    def test_custom_board_stays_compact_without_keybed(self):
        m,_=render('CONTROLLERTYPE controller=board\\nKNOBS count=8 zone=auto\\nFADERS count=4 zone=auto\\n')
        self.assertLess(m['width'],420.)
        self.assertLess(m['depth'],260.)

if __name__=='__main__':
    unittest.main(verbosity=2)
'''


def main():
    if not ENGINE.is_file() or not STUDIO.is_file():
        sys.exit('Run this script from the Midreation repository root (src/main.cpp and studio/index.html required).')
    if TEST.exists():
        sys.exit(f'Refusing to replace an existing test: {TEST}. This patch may already have been applied.')
    before_engine=ENGINE.read_text(encoding='utf-8')
    before_studio=STUDIO.read_text(encoding='utf-8')
    if 'constexpr double DECK_HEIGHT = 30.0;' in before_engine:
        sys.exit('The visual upgrade is already present; no changes made.')
    # Validate every anchor before touching source files.
    try:
        after_engine=apply_engine(before_engine)
        after_studio=apply_studio(before_studio)
    except RuntimeError as exc:
        sys.exit(str(exc))
    ENGINE.write_text(after_engine,encoding='utf-8')
    STUDIO.write_text(after_studio,encoding='utf-8')
    TEST.write_text(TEST_TEXT,encoding='utf-8')
    print('Updated src/main.cpp: realistic keybed sizes, deeper case, sculpted tray, bright red.')
    print('Updated studio/index.html: vivid red swatch, enhanced lighting, sizing note.')
    print('Added test/test_premium_visuals.py with six regression tests.')
    print('Next: cmake -S . -B build && cmake --build build')
    print('Then: python3 -m unittest discover -s test -p "test_*.py" -v')


if __name__=='__main__':
    main()
