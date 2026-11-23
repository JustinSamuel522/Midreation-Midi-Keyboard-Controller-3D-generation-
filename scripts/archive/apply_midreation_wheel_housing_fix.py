#!/usr/bin/env python3
"""Midreation: integrate pitch/mod wheels into a continuous, enclosed side pod.

Run from the Midreation repository root:
    python3 scripts/archive/apply_midreation_wheel_housing_fix.py
    cmake -S . -B build && cmake --build build
    python3 -m unittest discover -s test -p 'test_*.py' -v

This is a surgical, CGI-only src/main.cpp update for the recessed-keybed
branch. It will not alter files if expected sections are missing. It preserves
all Auto Best Fit, adjustable keybed, rendering, and procedural work.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
CPP = ROOT / "src" / "main.cpp"
TEST = ROOT / "test" / "test_wheel_housing.py"
MARKER = "MIDREATION_WHEEL_HOUSING_V1"


def change_once(src, old, new, what):
    n = src.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected one matching source section, found {n}. No files changed.")
    return src.replace(old, new, 1)


# The wheel side area stays structurally connected to the rear control deck.
# The surface is BELOW control-deck level so that only the upper arc of each
# wheel protrudes through its matte-black slot. The side cheeks enclose the
# transition, eliminating the open notch alongside the keys.
POD = r'''      // MIDREATION_WHEEL_HOUSING_V1
      // A real keyboard's pitch/mod assembly is inset into a dedicated side
      // housing. A full-height deck here would make the wheels float; this
      // lower pod joins the high rear control platform and the keybed cheek.
      if(l.spec.pitch+l.spec.mod>0){
        constexpr double podTop = 32.5; // wheel-well top, below control deck
        double lastWheel=keyBack;
        for(const Part &wheel:l.parts)if(wheel.type=="wheel")
          lastWheel=max(lastWheel,wheel.z+wheel.d);
        const double podX=x+5.5;
        const double podRight=keyLeft-6.9; // overlaps inner keybed cheek
        const double podStart=panelFront-3.7; // joins upper deck
        const double podEnd=min(z+d-10.0,max(keyBack+37.0,lastWheel+7.0));
        if(podRight-podX>12.0 && podEnd-podStart>10.0){
          // Cast lower wheel housing, physically connected to both shells.
          roundedPrism(podX,lowShellTop-1.25,podStart,
                       podRight-podX,podTop-(lowShellTop-1.25),
                       podEnd-podStart,5.2,1.35,shade(c,.97));
          // Outer raised cheek: conceals the exposed side of the join.
          const double cheekEnd=min(z+d-4.8,keyFront+6.5);
          roundedPrism(x+1.8,lowShellTop-1.25,podStart-1.5,
                       7.8,deck-(lowShellTop-1.25),
                       cheekEnd-(podStart-1.5),2.6,.85,side);
          // Satin-finished upper shoulder behind the wheel openings.
          // The shoulder continues the front edge of the control housing.
          roundedPrism(podX,deck-3.0,podStart-4.5,
                       podRight-podX,3.0,5.5,1.5,.55,shade(c,.91));
          // Short dark seam at the end of the wheel pod, not a transparent gap.
          roundedPrism(podX+2.0,podTop-.6,podEnd-1.7,
                       max(1.0,podRight-podX-4.0),.65,1.15,.45,.15,
                       shade(color("black"),.66));
        }
      }
'''

SIDE_BRIDGE = r'''      // Complete the outer keyboard end cheeks so their rear ends
      // overlap the raised deck. This closes the seam at the keybed sides.
      const double jointStart=panelFront-3.7;
      const double jointEnd=min(z+d-4.8,keyFront+6.5);
      const double jointDepth=jointEnd-jointStart;
      if(jointDepth>2.0){
        const double rightStart=keyRight+3.1;
        const double rightWidth=x+w-1.8-rightStart;
        if(rightWidth>1.5)
          roundedPrism(rightStart,lowShellTop-1.2,jointStart,
                       rightWidth,deck-(lowShellTop-1.2),jointDepth,
                       2.0,.65,side);
      }
'''

WHEELS_OLD = r'''      }else if(p.type=="wheel"){
        roundedPrism(x,deck-.12,z,w,1.0,d,3.4,.38,shade(color("dark"),.85));
        double r=min(w*.33,d*.40);
        roundedPrism(cx-6,deck+.9,cz-r*.82,12,.25,r*1.64,2,.1,color("black"));
        verticalWheel(cx,deck+1.0,cz,r,8.8,shade(c,.97));
'''

WHEELS_NEW = r'''      }else if(p.type=="wheel"){
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

TEST_SOURCE = '''"""Regression checks for Midreation's embedded pitch/mod wheel housing."""
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
            "CONTROLLERTYPE controller=keyboard-synth\\n"
            "KEYBED keys=61 type=weighted\\n"
            "WHEELS pitch=1 mod=1\\n")
        wheels = [p for p in model["parts"] if p["type"] == "wheel"]
        self.assertEqual(len(wheels), 2)
        self.assertEqual(model["depth"], 265)
        for wheel in wheels:
            in_region = [y for x, y, z in vertices
                         if wheel["x"]+4 < x < wheel["x"]+wheel["w"]-4
                         and wheel["z"]+3 < z < wheel["z"]+wheel["d"]-3]
            self.assertTrue(in_region)
            # Wheel tops protrude above the well, but remain below the 45-mm
            # main control deck (the old floating discs reached ~58 mm).
            self.assertGreater(max(in_region), 38.0)
            self.assertLess(max(in_region), 44.6)
            # The surrounding housing really exists at this level.
            self.assertTrue(any(31.5 < height < 33.6 for height in in_region))

    def test_join_fills_side_gap(self):
        model, vertices = generate(
            "CONTROLLERTYPE controller=keyboard-synth\\n"
            "KEYBED keys=61 type=weighted\\n"
            "WHEELS pitch=1 mod=1\\n")
        keys = [p for p in model["parts"] if p["type"] == "white_key"]
        rear = min(p["z"] for p in keys)
        # Filled shoulder just ahead of the rear deck, left of the keybed.
        joints = [y for x, y, z in vertices
                  if 17 < x < 55 and rear-17 < z < rear+3]
        self.assertTrue(any(y > 30.0 for y in joints), "Wheel-side panel still has a gap")

    def test_board_wheels_still_work_without_keybed(self):
        model, vertices = generate(
            "CONTROLLERTYPE controller=board\\n"
            "WHEELS pitch=1 mod=1\\nKNOBS count=4\\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "wheel"]), 2)
        self.assertTrue(vertices)

if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def patch(src):
    if MARKER in src:
        raise ValueError("Wheel-housing fix is already applied; nothing changed.")
    if "MIDREATION_RECESSED_KEYBED_V2" not in src:
        raise ValueError("Please use the recessed-keybed source before this update.")
    # Don't assume the user has the same material/lighting version; geometry is
    # intentionally local to the casing and the wheel branches.
    old_pod_marker = "      // Rear keybed cover: the lip extends ~15 mm over the backs of the black"
    src = change_once(src, old_pod_marker, POD + old_pod_marker,
                      "wheel pod in keyboard enclosure")
    old_side = '''      roundedPrism(keyRight+3.3,lowShellTop-1.0,keyBack-1.5,6.2,
                   deck-lowShellTop-3.2,keyD+6.5,2.0,1.0,side);
'''
    src = change_once(src, old_side, old_side + SIDE_BRIDGE,
                      "side-cheek joint")
    src = change_once(src, WHEELS_OLD, WHEELS_NEW,
                      "floating pitch/mod wheel geometry")
    return src


def main():
    try:
        if not CPP.is_file():
            raise ValueError("Run from the Midreation repository root (src/main.cpp missing).")
        if TEST.exists():
            raise ValueError("test/test_wheel_housing.py exists; refusing to overwrite it.")
        before = CPP.read_text(encoding="utf8")
        after = patch(before)
        if after == before or len(after) < len(before):
            raise ValueError("Unexpected patch result; refusing to write.")
        compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
        with tempfile.TemporaryDirectory(prefix="midreation-wheel-validate-") as tmp:
            if compiler:
                check = Path(tmp) / "candidate.cpp"
                check.write_text(after, encoding="utf8")
                proc = subprocess.run([compiler, "-std=c++17", "-fsyntax-only", str(check)],
                                      capture_output=True, text=True, timeout=90)
                if proc.returncode:
                    raise ValueError("C++ syntax validation failed; no changes made:\n"+proc.stderr[-4500:])
                print("C++17 syntax validation passed.")
            else:
                print("No local C++ compiler found; skipping syntax validation.")
        backup = ROOT / "build" / "wheel_housing_backup"
        if backup.exists():
            raise ValueError(f"Backup already exists ({backup}); no files changed.")
        backup.mkdir(parents=True, exist_ok=False)
        shutil.copy2(CPP, backup / "main.cpp")
        output = CPP.with_name("main.cpp.wheel-tmp")
        try:
            output.write_text(after, encoding="utf8")
            os.replace(output, CPP)
            TEST.parent.mkdir(parents=True, exist_ok=True)
            TEST.write_text(TEST_SOURCE, encoding="utf8")
        except Exception:
            shutil.copy2(backup / "main.cpp", CPP)
            output.unlink(missing_ok=True)
            TEST.unlink(missing_ok=True)
            raise
        print("Midreation wheel housing and side-gap fix applied.")
        print("Changed: src/main.cpp | Added: test/test_wheel_housing.py")
        print("Backup: build/wheel_housing_backup/main.cpp")
        print("Next: cmake -S . -B build && cmake --build build")
        print("      python3 -m unittest discover -s test -p 'test_*.py' -v")
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"No changes applied: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
