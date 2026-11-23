#!/usr/bin/env python3
"""Midreation: raised control housing and recessed, framed keyboard action.

Run from the repository root:
    python3 scripts/archive/apply_midreation_recessed_keybed.py
    cmake -S . -B build && cmake --build build
    python3 -m unittest discover -s test -p 'test_*.py' -v

This script deliberately edits the *local* src/main.cpp, including any
uncommitted DECK_HEIGHT changes; it doesn't reset or download the file.
The entire patch is prepared/validated before any file is written.
"""
from pathlib import Path
import re
import sys

ROOT = Path.cwd()
ENGINE = ROOT / "src" / "main.cpp"
TEST = ROOT / "test" / "test_recessed_keybed.py"
MARKER = "MIDREATION_RECESSED_KEYBED_V2"


def replace_regex_once(source, pattern, replacement, label, flags=0):
    result, count = re.subn(pattern, replacement, source, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one matching section, found {count}. Nothing was changed.")
    return result


# The construction below deliberately does not rely on the global DECK_HEIGHT
# for keyboards. That existing setting remains the height of controller-only
# boards, whose casing now follows the configured height too.
RENDER_CHASSIS = r'''  // MIDREATION_RECESSED_KEYBED_V2
  // Enclosure heights are tied to the mounting planes, so controls do not float.
  // Keyboard instruments use a raised *rear* control housing and a physically
  // distinct keybed tray. Both are constructed as meshes; this is not a shader trick.
  void renderChassis(const Layout &l,const Part &p,Vec3 c,double deck){
    const double x=p.x,z=p.z,w=p.w,d=p.d;
    const Vec3 side=l.spec.panels=="wood"?color("wood"):shade(c,.71);
    if(!l.spec.keys){
      // Standard desktop/foot controller: a single full-size top deck. Its
      // outer shell always rises to the same mounting height as the controls.
      roundedPrism(x,0,z,w,max(4.,deck-3.9),d,12.5,3.8,shade(c,.77));
      roundedPrism(x+1.8,deck-5.6,z+1.8,w-3.6,5.6,d-3.6,10.0,1.35,shade(c,1.12));
      roundedPrism(x+1.8,3.8,z+14,5.5,max(5.,deck-10.7),d-28,2.4,1.0,side);
      roundedPrism(x+w-7.3,3.8,z+14,5.5,max(5.,deck-10.7),d-28,2.4,1.0,side);
      roundedPrism(x+7,5.1,z+d-5.3,w-14,max(5.,deck-16.4),3.2,1.2,.85,shade(c,.57));
      roundedPrism(x+9,deck-6.8,z+d-4.8,w-18,.75,2.2,.9,.18,shade(color("black"),.82));
      for(double px:{x+9,x+w-9})for(double pz:{z+10,z+d-10}){
        cylinder(px,deck,pz,1.8,.35,color("steel"),16);
        cube(px-1,deck+.36,pz-.20,2,.16,.4,color("dark"));
      }
      for(int i=0;i<7&&w>300;i++){
        double px=x+w*.39+i*8.5;
        roundedPrism(px,deck+.05,z+5,4.2,.17,12,1,.08,shade(c,.48));
      }
    }else{
      // Locate the actual generated keybed, rather than hardcoding 61/88 keys.
      double keyLeft=1e100,keyRight=-1e100,keyBack=1e100,keyFront=-1e100;
      for(const Part &k:l.parts)if(k.type=="white_key"){
        keyLeft=min(keyLeft,k.x);keyRight=max(keyRight,k.x+k.w);
        keyBack=min(keyBack,k.z);keyFront=max(keyFront,k.z+k.d);
      }
      if(keyLeft>=keyRight)return;
      const double keyW=keyRight-keyLeft,keyD=keyFront-keyBack;
      const double lowShellTop=18.7;
      // Lower case is continuous, but does not fill the height below the rear
      // control panel. The keys are mounted a few millimeters above a dark tray.
      roundedPrism(x,0,z,w,lowShellTop,d,12.5,2.6,shade(c,.74));
      roundedPrism(keyLeft-4.5,lowShellTop-1.1,keyBack-3.6,
                   keyW+9.0,KEYBED_DECK_HEIGHT-lowShellTop+.45,keyD+5.5,
                   2.8,.65,shade(color("black"),.80));
      // Upper control platform: only occupies space *behind* the keys. Its
      // upper surface and all encoders/faders share CONTROL_DECK_HEIGHT.
      const double panelFront=keyBack-7.0;
      const double panelDepth=panelFront-(z+1.8);
      if(panelDepth>2.0){
        roundedPrism(x+1.8,lowShellTop-1.1,z+1.8,w-3.6,
                     deck-(lowShellTop-1.1),panelDepth,10.0,2.0,shade(c,1.10));
        roundedPrism(x+3.8,deck-.9,z+3.8,w-7.6,.9,max(1.0,panelDepth-3.2),
                     8.5,.27,shade(c,1.07));
      }
      // Rear keybed cover: the lip extends ~15 mm over the backs of the black
      // keys but stays physically ABOVE their molded top surfaces.
      roundedPrism(keyLeft-7.0,deck-4.2,keyBack-7.5,keyW+14.0,4.2,23.0,
                   2.3,1.0,shade(c,.96));
      roundedPrism(keyLeft-5.8,deck-4.32,keyBack+13.1,keyW+11.6,.33,1.15,
                   .45,.08,shade(color("black"),.83));
      // Raised end cheeks and front fallboard lip frame the exposed white keys.
      // Their x/z footprints stay outside the playable key rectangles.
      roundedPrism(keyLeft-9.5,lowShellTop-1.0,keyBack-1.5,6.2,
                   deck-lowShellTop-3.2,keyD+6.5,2.0,1.0,side);
      roundedPrism(keyRight+3.3,lowShellTop-1.0,keyBack-1.5,6.2,
                   deck-lowShellTop-3.2,keyD+6.5,2.0,1.0,side);
      roundedPrism(x+6.5,4.7,z+d-8.4,w-13,14.9,5.3,1.6,1.0,shade(c,.58));
      roundedPrism(x+8.2,19.5,z+d-6.4,w-16.4,.7,1.9,.5,.18,
                   shade(color("black"),.70));
      // A narrow rear top seam and a few recessed fasteners emphasize the
      // join between the raised control housing and the lower keybed shell.
      if(panelDepth>22.0){
        roundedPrism(x+8.0,deck+.04,z+6,w-16,.16,1.15,.4,.05,shade(c,.63));
        for(double px:{x+10,x+w-10}){
          cylinder(px,deck+.02,z+10,1.7,.32,color("steel"),16);
          cube(px-.9,deck+.35,z+9.82,1.8,.14,.36,color("dark"));
        }
      }
    }
    // Rubber feet work for both controller-only boards and keyboards.
    for(double fx:{x+23,x+w-23})for(double fz:{z+20,z+d-20})
      roundedPrism(fx-11,-4.0,fz-7,22.,4.,14.,3.0,.8,shade(color("black"),.63));
  }

'''


TEST_TEXT = '''"""Regression coverage for Midreation's separate keyboard housing and keybed."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "build" / "midi_generator"


def build(brief):
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        spec = folder / "input.board"
        spec.write_text(brief, encoding="utf8")
        run = subprocess.run([str(EXE), str(spec), str(folder), "7", "1"],
                             capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stderr)
        model = json.loads((folder / "design_1.json").read_text())
        verts = []
        for line in (folder / "design_1.obj").read_text().splitlines():
            if line.startswith("v "):
                xyz = list(map(float, line.split()[1:4]))
                verts.append(xyz)
        return model, verts


class RecessedKeybedTests(unittest.TestCase):
    def test_raised_upper_housing_and_overhang(self):
        model, vertices = build("CONTROLLERTYPE controller=keyboard-synth\\n"
                                "KEYBED keys=61 type=semi-weighted\\n")
        white = [p for p in model["parts"] if p["type"] == "white_key"]
        black = [p for p in model["parts"] if p["type"] == "black_key"]
        self.assertEqual(len(white) + len(black), 61)
        rear = min(p["z"] for p in white)
        lx = min(p["x"] for p in white)
        rx = max(p["x"] + p["w"] for p in white)
        cx = (lx + rx) / 2
        # Chassis top behind the keybed is visibly above the black-key caps.
        rear_deck = [v[1] for v in vertices if abs(v[0] - cx) < 4 and v[2] < rear - 9]
        self.assertTrue(rear_deck and max(rear_deck) >= 44.5)
        # There must also be a substantial bridge projecting INTO the keybed.
        lip = [v[1] for v in vertices if abs(v[0] - cx) < 5 and rear + 2 <= v[2] <= rear + 17]
        self.assertTrue(lip and max(lip) >= 44.5)
        self.assertEqual(model["depth"], 265)

    def test_88_key_and_wheel_clearance(self):
        model, vertices = build("CONTROLLERTYPE controller=keyboard-synth\\n"
                                "KEYBED keys=88 type=weighted\\nWHEELS pitch=1 mod=1\\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"].endswith("_key")]), 88)
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "wheel"]), 2)
        self.assertTrue(vertices)

    def test_standalone_board_remains_supported(self):
        model, vertices = build("CONTROLLERTYPE controller=board\\n"
                                "KNOBS count=8\\nFADERS count=4\\nPADS count=4\\n")
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "white_key"]), 0)
        self.assertEqual(len([p for p in model["parts"] if p["type"] == "knob"]), 8)
        self.assertGreater(len(vertices), 1000)

    def test_explicit_dimensions_still_respected(self):
        model, _ = build("CONTROLLERTYPE controller=keyboard-synth\\n"
                         "BODY width=1070 depth=340\\nKEYBED keys=61 type=weighted\\n")
        self.assertEqual(model["width"], 1070)
        self.assertEqual(model["depth"], 340)


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''


def patch_engine(source):
    if MARKER in source:
        raise RuntimeError("The recessed-keybed update is already applied. Nothing was changed.")
    # The visual upgrade defines DECK_HEIGHT; don't silently overwrite a value
    # the user has adjusted by hand. Fall back to the older source layout.
    if source.count("constexpr double DECK_HEIGHT") != 1:
        source = replace_regex_once(
            source, r"(constexpr double PI\s*=\s*3\.14159265358979323846\s*;)",
            r"\1\nconstexpr double DECK_HEIGHT = 19.0;", "original deck constant")
    source = replace_regex_once(
        source,
        r"(constexpr double DECK_HEIGHT\s*=\s*[0-9]+(?:\.[0-9]*)?\s*;)",
        r"\1\n// Keyboard controls and keys intentionally have different mounting planes.\n"
        r"constexpr double CONTROL_DECK_HEIGHT = 45.0;\n"
        r"constexpr double KEYBED_DECK_HEIGHT = 24.0;",
        "separate keyboard mounting heights")

    cap = r"double x=p\.x,z=p\.z,w=p\.w,d=p\.d,deck=(?:DECK_HEIGHT|19\.)\s*;"
    if len(re.findall(cap, source)) != 2:
        raise RuntimeError("Expected two original keycap-height declarations; source differs. Nothing was changed.")
    source = re.sub(cap,
                    "double x=p.x,z=p.z,w=p.w,d=p.d,deck=KEYBED_DECK_HEIGHT;",
                    source)
    source = replace_regex_once(
        source, r"constexpr double deck\s*=\s*(?:DECK_HEIGHT|19\.)\s*;",
        "const double deck = l.spec.keys ? CONTROL_DECK_HEIGHT : DECK_HEIGHT;",
        "main control deck reference")
    source = replace_regex_once(
        source,
        r"(?=  void build\(const Layout &l\)\{)",
        RENDER_CHASSIS,
        "mesh enclosure helper")
    source = replace_regex_once(
        source,
        r'(if\(p\.type=="body"\)\{)\n.*?(?=\n      \}else if\(p\.type=="knob"\)\{)',
        r"\1\n        renderChassis(l,p,c,deck);",
        "body geometry",
        flags=re.S)
    return source


def main():
    try:
        if not ENGINE.is_file():
            raise RuntimeError("Run this from the Midreation repository root (src/main.cpp not found).")
        before = ENGINE.read_text(encoding="utf8")
        after = patch_engine(before)
        if TEST.exists():
            raise RuntimeError(f"{TEST} already exists; refusing to overwrite it.")
        if before == after:
            raise RuntimeError("No changes prepared.")
        TEST.parent.mkdir(parents=True, exist_ok=True)
        ENGINE.write_text(after, encoding="utf8")
        TEST.write_text(TEST_TEXT, encoding="utf8")
        print("Updated: src/main.cpp")
        print("Created: test/test_recessed_keybed.py")
        print("Keyboard rear housing + controls: 45 mm mounting height")
        print("Keybed: separate 24 mm mounting height, supporting tray and raised surround")
        print("Controller-only cases: their body now follows your DECK_HEIGHT setting")
        print("Next: cmake -S . -B build && cmake --build build")
        print("      python3 -m unittest discover -s test -p 'test_*.py' -v")
    except (RuntimeError, OSError) as error:
        print(f"Unable to apply update: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
