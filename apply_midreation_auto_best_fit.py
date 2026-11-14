#!/usr/bin/env python3
"""Upgrade Midreation's C++ layout engine with compact, centered Auto Best Fit.

Usage (from the repository root):
    python3 apply_midreation_auto_best_fit.py
    cmake -S . -B build && cmake --build build
    python3 -m unittest discover -s test -p 'test_*.py' -v

The patch is intentionally narrow: it only changes all-Auto desktop boards.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
ENGINE = ROOT / 'src' / 'main.cpp'
STUDIO = ROOT / 'studio' / 'index.html'
TEST = ROOT / 'test' / 'test_auto_best_fit.py'

METHOD = r'''  // Auto Best Fit for desktop boards: preserve each control bank's internal
  // geometry and spacing, then pack the banks into centered, balanced rows.
  // Explicit placement zones, foot controllers and keybeds keep their own solver.
  void fitAutoBoard(){
    if(spec.kind!="board" || spec.keys>0 || spec.groups.empty())return;
    for(const auto& g:spec.groups)if(g.zone!="auto")return;

    struct Block {
      size_t first,last;
      double x,z,w,d;
      string type;
    };
    vector<Block> blocks;
    // The existing generator appends the parts of each group consecutively.
    // Keeping these groups intact respects explicit grids, row/column layouts,
    // physical component dimensions, and paired knob/fader channel alignment.
    for(size_t first=1;first<parts.size();){
      size_t last=first+1;
      while(last<parts.size() && parts[last].group==parts[first].group)++last;
      double x0=1e100,z0=1e100,x1=-1e100,z1=-1e100;
      for(size_t j=first;j<last;j++){
        x0=min(x0,parts[j].x);z0=min(z0,parts[j].z);
        x1=max(x1,parts[j].x+parts[j].w);z1=max(z1,parts[j].z+parts[j].d);
      }
      blocks.push_back({first,last,x0,z0,x1-x0,z1-z0,parts[first].type});
      first=last;
    }
    if(blocks.empty())return;

    // Offer meaningful alternatives without changing individual components:
    // design 1 is control-oriented, 2 is area-oriented, 3 is width-oriented.
    auto priority=[](const string& type){
      if(type=="knob")return 0;
      if(type=="fader")return 1;
      if(type=="display")return 2;
      if(type=="pad")return 3;
      if(type=="button" || type=="clicky")return 4;
      if(type=="wheel")return 9;
      return 5;
    };
    stable_sort(blocks.begin(),blocks.end(),[&](const Block& a,const Block& b){
      if(a.type=="wheel" && b.type!="wheel")return false;
      if(b.type=="wheel" && a.type!="wheel")return true;
      if(id%3==1)return priority(a.type)<priority(b.type);
      if(id%3==2)return a.w*a.d>b.w*b.d;
      return a.w>b.w;
    });

    const double edge=20.,groupGap=18.;
    struct Row {vector<size_t> members;double w=0,d=0;};
    auto makeRows=[&](double limit){
      vector<Row> rows;Row row;
      for(size_t i=0;i<blocks.size();i++){
        const Block& b=blocks[i];
        if(b.w>limit+1e-6)return vector<Row>{};
        if(!row.members.empty() && row.w+groupGap+b.w>limit+1e-6){
          rows.push_back(row);row=Row{};
        }
        if(!row.members.empty())row.w+=groupGap;
        row.w+=b.w;row.d=max(row.d,b.d);row.members.push_back(i);
      }
      if(!row.members.empty())rows.push_back(row);
      return rows;
    };

    vector<Row> bestRows;
    double bestScore=1e100,newWidth=spec.width,newDepth=spec.depth;
    const double targetAspect=(id%3==1?2.3:(id%3==2?1.9:2.7));
    auto consider=[&](double limit){
      auto rows=makeRows(limit);
      if(rows.empty())return;
      double usedWidth=0,usedDepth=groupGap*(rows.size()-1);
      for(const Row& row:rows){usedWidth=max(usedWidth,row.w);usedDepth+=row.d;}
      double requiredWidth=usedWidth+2*edge,requiredDepth=usedDepth+2*edge;
      double w=spec.fixedWidth?spec.width:max(140.,requiredWidth);
      double d=spec.fixedDepth?spec.depth:max(100.,requiredDepth);
      if(requiredWidth>w+1e-6 || requiredDepth>d+1e-6 || w>4000 || d>1800)return;
      double aspect=w/d;
      double score=w*d*(1.+.20*abs(log(aspect/targetAspect)))+70.*rows.size();
      if(score<bestScore){bestScore=score;bestRows=move(rows);newWidth=w;newDepth=d;}
    };

    if(spec.fixedWidth){
      consider(spec.width-2*edge);
    }else{
      double minContentWidth=0,totalContentWidth=groupGap*(blocks.size()-1);
      for(const Block& b:blocks){minContentWidth=max(minContentWidth,b.w);totalContentWidth+=b.w;}
      const double step=max(8.,(totalContentWidth-minContentWidth)/80.);
      for(double limit=minContentWidth;limit<=totalContentWidth+1e-6;limit+=step)consider(limit);
      consider(totalContentWidth);
    }
    // The original collision-free placement remains intact if no candidate
    // meets a tightly specified width/depth constraint.
    if(bestRows.empty())return;

    spec.width=newWidth;spec.depth=newDepth;
    parts.front().w=newWidth;parts.front().d=newDepth;
    double baseDepth=groupGap*(bestRows.size()-1);
    for(const Row& row:bestRows)baseDepth+=row.d;
    double extraZ=0;
    if(spec.fixedDepth && bestRows.size()>1)
      extraZ=min(60.,max(0.,(newDepth-2*edge-baseDepth)/(bestRows.size()-1)));
    const double rowGap=groupGap+extraZ;
    double z=(newDepth-(baseDepth+extraZ*(bestRows.size()-1)))/2.;
    used.clear();
    for(const Row& row:bestRows){
      double extraX=0;
      if(spec.fixedWidth && row.members.size()>1)
        extraX=min(48.,max(0.,(newWidth-2*edge-row.w)/(row.members.size()-1)));
      double x=(newWidth-(row.w+extraX*(row.members.size()-1)))/2.;
      for(size_t index:row.members){
        const Block& b=blocks[index];
        double blockZ=z+(row.d-b.d)/2.;
        for(size_t j=b.first;j<b.last;j++){
          parts[j].x+=x-b.x;
          parts[j].z+=blockZ-b.z;
        }
        used.push_back({x,blockZ,b.w,b.d});
        x+=b.w+groupGap+extraX;
      }
      z+=row.d+rowGap;
    }
    if(!spec.fixedWidth || !spec.fixedDepth)
      warnings.push_back("Auto Best Fit sized the enclosure around its controls.");
  }
'''

TEST_CONTENT = '''"""Regression coverage for the desktop Auto Best Fit arrangement."""
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


DEFAULT_BOARD = ''' + "'''" + '''CONTROLLERTYPE controller=board
KNOBS count=8 zone=auto
FADERS count=4 zone=auto
PADS count=4 zone=auto
BUTTONS count=6 zone=auto
''' + "'''" + '''


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
        model = generate(DEFAULT_BOARD + 'BODY width=480\\n')[0]
        self.assertEqual(model['width'], 480)
        self.assertGreater(model['depth'], 0)
        self.assert_centered(model)
        self.assert_clear(model)

    def test_fixed_depth_only(self):
        model = generate(DEFAULT_BOARD + 'BODY depth=220\\n')[0]
        self.assertEqual(model['depth'], 220)
        self.assert_centered(model)
        self.assert_clear(model)

    def test_fixed_both_dimensions(self):
        model = generate(DEFAULT_BOARD + 'BODY width=650 depth=320\\n')[0]
        self.assertEqual((model['width'], model['depth']), (650, 320))
        self.assert_centered(model)
        self.assert_clear(model)

    def test_paired_channels_stay_aligned(self):
        brief = ''' + "'''" + '''CONTROLLERTYPE controller=board
KNOBS count=6 zone=auto layout=row
FADERS count=6 zone=auto layout=row
PADS count=4 zone=auto
''' + "'''" + '''
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
        spec = ''' + "'''" + '''CONTROLLERTYPE controller=board
BODY width=420 depth=260
KNOBS count=4 zone=left
FADERS count=4 zone=right
''' + "'''" + '''
        model = generate(spec)[0]
        self.assertEqual((model['width'], model['depth']), (420, 260))
        self.assert_clear(model)


if __name__ == '__main__':
    unittest.main(verbosity=2)
'''


def replace_once(text, old, new, path):
    matches = text.count(old)
    if matches != 1:
        raise RuntimeError(f'{path}: expected exactly one anchor, found {matches}. '
                           'Please compare your checkout with the latest main branch.')
    return text.replace(old, new, 1)


def main():
    if not ENGINE.is_file() or not STUDIO.is_file():
        sys.exit('Run from the Midreation repository root (src/main.cpp must exist).')
    if (ROOT / '.git').exists():
        proc = subprocess.run(['git', 'status', '--porcelain', '--',
                               'src/main.cpp', 'studio/index.html',
                               'test/test_auto_best_fit.py'],
                              text=True, capture_output=True)
        if proc.returncode == 0 and proc.stdout.strip():
            sys.exit('Those target files have uncommitted changes. Commit or stash '
                     'them first so the patch does not overwrite your work.')

    engine = ENGINE.read_text(encoding='utf-8')
    studio = STUDIO.read_text(encoding='utf-8')
    if 'void fitAutoBoard(){' in engine:
        sys.exit('Auto Best Fit is already present in src/main.cpp; no changes made.')

    engine = replace_once(engine, '  bool tryBuild(){', METHOD + '  bool tryBuild(){', ENGINE)
    engine = replace_once(
        engine,
        '''      try{build();if(attempt>0)warnings.push_back("Automatically enlarged enclosure to fit all controls.");return true;}''',
        '''      try{
        build();fitAutoBoard();
        if(attempt>0 && (spec.width>startWidth+1e-6 || spec.depth>startDepth+1e-6))
          warnings.push_back("Automatically enlarged enclosure to fit all controls.");
        return true;
      }''',
        ENGINE,
    )
    engine = replace_once(
        engine,
        '''  bool tryBuild(){
    for(int attempt=0;attempt<14;attempt++){''',
        '''  bool tryBuild(){
    const double startWidth=spec.width,startDepth=spec.depth;
    for(int attempt=0;attempt<14;attempt++){''',
        ENGINE,
    )
    studio = replace_once(
        studio,
        'Leave dimensions blank for automatic sizing. You can return to any step and regenerate to refine your design.',
        'Leave dimensions blank to fit a compact, centered enclosure around your controls. Specify either dimension to lock it. You can return to any step and regenerate.',
        STUDIO,
    )
    if TEST.exists():
        sys.exit(f'{TEST} already exists. Move it aside before patching.')
    ENGINE.write_text(engine, encoding='utf-8')
    STUDIO.write_text(studio, encoding='utf-8')
    TEST.write_text(TEST_CONTENT, encoding='utf-8')
    print('Updated src/main.cpp (compact Auto Best Fit layout)')
    print('Updated studio/index.html (sizing explanation)')
    print('Created test/test_auto_best_fit.py (six regression tests)')
    print('\nNext:')
    print('  cmake -S . -B build')
    print('  cmake --build build')
    print("  python3 -m unittest discover -s test -p 'test_*.py' -v")


if __name__ == '__main__':
    main()
