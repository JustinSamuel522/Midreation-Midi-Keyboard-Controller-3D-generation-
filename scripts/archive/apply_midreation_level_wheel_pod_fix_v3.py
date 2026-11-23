#!/usr/bin/env python3
"""Midreation CGI-only Flush Wheel Pod V3 (for Nov 23 source).

From the repository root, after applying the previous wheel-housing update:
    python3 scripts/archive/apply_midreation_level_wheel_pod_fix_v3.py
    cmake -S . -B build && cmake --build build
    python3 -m unittest discover -s test -p 'test_*.py' -v

The rear control deck and left wheel pod become one level structural surface.
Only wheel apertures are recessed. With no wheels, the pod remains solid.
Safeguards: source-marker checks, atomic writes, syntax check, local backups,
rollback on errors, and an update to the prior wheel test's old height limits.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
ENGINE = ROOT / 'src' / 'main.cpp'
OLD_TEST = ROOT / 'test' / 'test_wheel_housing.py'
NEW_TEST = ROOT / 'test' / 'test_flush_wheel_pod.py'
MARKER = 'MIDREATION_FLUSH_WHEEL_POD_V3'
BACKUP = ROOT / 'build' / 'flush_wheel_pod_backup'


def once(text, before, after, label):
    count = text.count(before)
    if count != 1:
        raise ValueError(f'{label}: expected one exact match, found {count}. No changes made.')
    return text.replace(before, after, 1)


def once_regex(text, pattern, after, label, flags=0):
    result, count = re.subn(pattern, lambda _m: after, text, flags=flags)
    if count != 1:
        raise ValueError(f'{label}: expected one source section, found {count}. No changes made.')
    return result


# The case is full height whether wheels are requested or not. Instead of
# placing a low wheel shelf beside the elevated control deck, we build a full
# left-hand extrusion and tessellate only its top skin around the wheel wells.
# This creates real 3D apertures (not just black decals sitting on a solid lid).
POD_V3 = r'''      // MIDREATION_FLUSH_WHEEL_POD_V3
      // Flush left-hand side housing: same 45-mm mounting plane as rear controls.
      // Always present, including on keyboards with pitch=0 and mod=0.
      // Aperture geometry is generated from the actual procedural wheel parts.
      {
        const double podX=x+1.8;
        const double podRight=keyLeft-3.3;  // joins raised inner keybed cheek
        const double podStart=max(z+1.8,panelFront-5.5);
        const double podEnd=min(z+d-4.5,keyFront+6.0);
        const double lowerY=lowShellTop-1.1;
        const double recessY=deck-16.0; // true well floor below the wheel arc
        if(podRight-podX>14.0 && podEnd-podStart>14.0){
          // Structural core and enclosed exterior (no exposed void beneath).
          roundedPrism(podX,lowerY,podStart,
                       podRight-podX,recessY-lowerY,podEnd-podStart,
                       3.4,1.15,shade(c,.98));

          vector<Rect> wells;
          for(const Part &wheel:l.parts)if(wheel.type=="wheel"){
            // Wheel opening is narrower than its mounting area so each wheel
            // has a solid surround rather than a disconnected shallow shelf.
            const double slotW=min(wheel.w-3.0,max(14.0,wheel.w*.68));
            const double xa=max(podX+2.2,wheel.x+wheel.w*.5-slotW*.5);
            const double xb=min(podRight-2.2,wheel.x+wheel.w*.5+slotW*.5);
            const double za=max(podStart+2.0,wheel.z+2.0);
            const double zb=min(podEnd-2.0,wheel.z+wheel.d-2.0);
            if(xb-xa>8.0 && zb-za>8.0)wells.push_back({xa,za,xb-xa,zb-za});
          }

          // Partition a planar deck along hole edges; skip cells inside wells.
          // No CSG library is required and the top is exactly deck-high.
          vector<double> xs{podX,podRight},zs{podStart,podEnd};
          for(const Rect &r:wells){
            xs.push_back(r.x);xs.push_back(r.x+r.w);
            zs.push_back(r.z);zs.push_back(r.z+r.d);
          }
          auto distinct=[](vector<double>&values){
            sort(values.begin(),values.end());
            values.erase(unique(values.begin(),values.end(),
              [](double a,double b){return fabs(a-b)<.001;}),values.end());
          };
          distinct(xs);distinct(zs);
          for(size_t i=0;i+1<xs.size();++i){
            for(size_t j=0;j+1<zs.size();++j){
              const double ax=xs[i],bx=xs[i+1],az=zs[j],bz=zs[j+1];
              if(bx-ax<.001 || bz-az<.001)continue;
              const double mx=(ax+bx)*.5,mz=(az+bz)*.5;
              bool opening=false;
              for(const Rect &r:wells)
                if(mx>r.x && mx<r.x+r.w && mz>r.z && mz<r.z+r.d)
                  {opening=true;break;}
              if(!opening)cube(ax,recessY,az,bx-ax,deck-recessY,bz-az,
                               shade(c,1.07));
            }
          }
          // Narrow satin front edge, continuously cast with the left housing.
          roundedPrism(podX+1.1,deck-1.05,podEnd-2.3,
                       podRight-podX-2.2,1.05,1.6,.7,.25,shade(c,.91));
        }
      }
'''

# Preserve the exact keyboard wheel positions present in the pushed main.cpp.
# Only their surrounding physical enclosure and mounting heights change.
WHEEL_V1 = '''      }else if(p.type=="wheel"){
        // MIDREATION_WHEEL_HOUSING_V1 (continued): a recessed wheel, not a
        // vertical cylinder balanced on the high control panel.
        const bool keyboard=l.spec.keys>0;
        const double wellTop=keyboard?32.5:deck;
        const double r=min(w*.33,d*.40);
        // Black well with a thin satin-metal perimeter and a deep central
        // opening. On keyboards it is flush with the lower side pod.
        roundedPrism(x-.65,wellTop-.17,z-.5,w+1.3,1.05,d+1.,3.5,.38,
                     shade(color("steel"),.44));
        roundedPrism(x+1.15,wellTop+.86,z+1.0,w-2.3,.19,d-2.0,2.65,.07,
                     shade(color("black"),.49));
        roundedPrism(cx-5.6,wellTop+1.02,cz-r*.84,11.2,.16,r*1.68,1.8,.05,
                     shade(color("black"),.34));
        // Hide the lower wheel arc inside the case. Only the knurled upper
        // part rises through the bezel; use dark molded rubber, not neon discs.
        const double wheelCenter=keyboard?wellTop-3.0:deck+1.0;
        verticalWheel(cx,wheelCenter,cz,r,8.8,shade(color("black"),1.35));
        // Small color-coded marker distinguishes pitch and modulation wheels.
        rod({cx-2.7,wheelCenter+r+.22,cz},
            {cx+2.7,wheelCenter+r+.22,cz},.33,.33,shade(c,.94),8);
'''

WHEEL_V3 = '''      }else if(p.type=="wheel"){
        // MIDREATION_FLUSH_WHEEL_POD_V3: wheel rises through a REAL well in
        // the keyboard's flush upper shell. No dropped side shelf or floating
        // disc; the wheel's lower half is hidden inside the enclosure.
        const bool keyboard=l.spec.keys>0;
        const double surface=deck;
        const double r=min(w*.33,d*.40);
        if(keyboard){
          const double slotW=min(w-3.0,max(14.0,w*.68));
          const double slotX=cx-slotW*.5;
          // Dark well floor, approximately 16 mm below the metal deck.
          roundedPrism(slotX+.35,surface-15.85,z+2.15,
                       slotW-.7,.35,d-4.3,1.0,.09,
                       shade(color("black"),.43));
          // Low-profile metallic seam outlining the true aperture.
          const Vec3 rim=shade(color("steel"),.51);
          roundedPrism(slotX-.7,surface+.025,z+1.65,
                       .7,.22,d-3.3,.3,.05,rim);
          roundedPrism(slotX+slotW,surface+.025,z+1.65,
                       .7,.22,d-3.3,.3,.05,rim);
          roundedPrism(slotX-.2,surface+.025,z+1.65,
                       slotW+.4,.22,.45,.15,.045,rim);
          roundedPrism(slotX-.2,surface+.025,z+d-2.1,
                       slotW+.4,.22,.45,.15,.045,rim);
        }else{
          // Standalone boards retain their original wheel mounting behavior.
          roundedPrism(x-.65,surface-.17,z-.5,w+1.3,1.05,d+1.,3.5,.38,
                       shade(color("steel"),.44));
          roundedPrism(x+1.15,surface+.86,z+1.0,w-2.3,.19,d-2.0,2.65,.07,
                       shade(color("black"),.49));
        }
        const double wheelCenter=keyboard?surface-2.5:surface+1.0;
        verticalWheel(cx,wheelCenter,cz,r,8.8,shade(color("black"),1.35));
        rod({cx-2.7,wheelCenter+r+.22,cz},
            {cx+2.7,wheelCenter+r+.22,cz},.33,.33,shade(c,.94),8);
'''

# Old test asserted that wheel tops must stay BELOW the 45-mm control deck.
# That would reject the user's desired flush wheel assembly. We revise it only
# if the exact previous test assertion exists, leaving other tests untouched.
TEST_V1 = '''            # Wheel tops protrude above the well, but remain below the 45-mm
            # main control deck (the old floating discs reached ~58 mm).
            self.assertGreater(max(in_region), 38.0)
            self.assertLess(max(in_region), 44.6)
            # The surrounding housing really exists at this level.
            self.assertTrue(any(31.5 < height < 33.6 for height in in_region))
'''

TEST_V2 = '''            # A wheel now emerges through the full-height 45-mm deck.
            # The lower arc sits in the deep 29-mm well, not on a shelf.
            self.assertGreater(max(in_region), 46.0)
            self.assertLess(max(in_region), 55.0)
            self.assertTrue(any(height < 38.0 for height in in_region))
'''

NEW_TEST_CONTENT = '''"""Regressions for the fully level left wheel housing and real wheel openings."""
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
        return run('CONTROLLERTYPE controller=keyboard-synth\\n'
                   'KEYBED keys=61 type=weighted\\n'
                   f'WHEELS pitch={int(wheels)} mod={int(wheels)}\\n')

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
        model, vertices = run('CONTROLLERTYPE controller=board\\n'
                              'WHEELS pitch=1 mod=1\\n'
                              'KNOBS count=4\\n')
        self.assertEqual(len([p for p in model['parts']
                              if p['type'] == 'wheel']), 2)
        self.assertTrue(vertices)

if __name__ == '__main__':
    unittest.main(verbosity=2)
'''


def patch_engine(source):
    if MARKER in source:
        raise ValueError('Flush Wheel Pod V3 is already installed. No changes made.')
    if 'MIDREATION_RECESSED_KEYBED_V2' not in source:
        raise ValueError('The recessed keybed update is missing. No changes made.')
    if 'MIDREATION_WHEEL_HOUSING_V1' not in source:
        raise ValueError('Apply the previous wheel housing update first. No changes made.')
    # Replace only the previous optional low pod; leave all neighboring keybed
    # and renderer geometry (including CGI PBR materials) exactly as-is.
    source = once_regex(
        source,
        r'      // MIDREATION_WHEEL_HOUSING_V1\n.*?(?=      // Rear keybed cover:)',
        POD_V3, 'lowered wheel pod', re.S)
    # Keep the checked-in wheel placement intact. The prior V2 installer failed
    # because its expected wheel-position snippet was not present in main.cpp.
    # This version edits only the housing and wheel geometry.
    source = once(source, WHEEL_V1, WHEEL_V3, 'wheel-well mesh')
    return source


def write_atomically(path, content):
    temp = path.with_name(path.name+'.flush-wheel-tmp')
    temp.write_text(content, encoding='utf-8')
    os.replace(temp, path)


def main():
    try:
        if not ENGINE.is_file():
            raise ValueError('Run from the Midreation repository root: missing src/main.cpp')
        if NEW_TEST.exists():
            raise ValueError(f'{NEW_TEST} already exists; refusing to overwrite')
        if not OLD_TEST.exists():
            raise ValueError('Existing test/test_wheel_housing.py is missing; please verify the prior update')
        before = ENGINE.read_text(encoding='utf-8')
        old_test = OLD_TEST.read_text(encoding='utf-8')
        after = patch_engine(before)
        new_old_test = once(old_test, TEST_V1, TEST_V2, 'previous wheel test height assumptions')
        if after == before or len(after) < 1000:
            raise ValueError('Unexpected source transformation')
        compiler = shutil.which('clang++') or shutil.which('g++') or shutil.which('c++')
        with tempfile.TemporaryDirectory(prefix='midreation-flush-wheel-pod-') as tmp:
            if compiler:
                candidate = Path(tmp)/'main.cpp'
                candidate.write_text(after, encoding='utf-8')
                proc = subprocess.run([compiler,'-std=c++17','-fsyntax-only',str(candidate)],
                                      capture_output=True, text=True, timeout=90)
                if proc.returncode:
                    raise ValueError('Updated C++ did not pass syntax validation; no files changed:\\n'
                                     + proc.stderr[-4000:])
                print('C++17 syntax check passed.')
            else:
                print('No C++ compiler found; please build with CMake after installation.')
        if BACKUP.exists():
            raise ValueError(f'{BACKUP} already exists; refusing to overwrite earlier backup')
        BACKUP.mkdir(parents=True)
        originals = {ENGINE:before, OLD_TEST:old_test}
        try:
            (BACKUP/'main.cpp').write_text(before, encoding='utf-8')
            (BACKUP/'test_wheel_housing.py').write_text(old_test, encoding='utf-8')
            write_atomically(ENGINE, after)
            write_atomically(OLD_TEST, new_old_test)
            write_atomically(NEW_TEST, NEW_TEST_CONTENT)
        except Exception:
            for dest, original in originals.items():
                write_atomically(dest, original)
            NEW_TEST.unlink(missing_ok=True)
            raise
        print('Midreation FLUSH WHEEL POD V3 applied.')
        print('  Updated src/main.cpp: full-height side wing + deep inset wheel apertures.')
        print('  Updated test/test_wheel_housing.py: height expectations.')
        print('  Added test/test_flush_wheel_pod.py.')
        print('  Backup saved under build/flush_wheel_pod_backup/.')
        print('Next: cmake -S . -B build && cmake --build build')
        print("      python3 -m unittest discover -s test -p 'test_*.py' -v")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f'No files changed: {error}',file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
