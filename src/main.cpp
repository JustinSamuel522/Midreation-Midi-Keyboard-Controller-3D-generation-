#include <algorithm>
#include <array>
#include <cmath>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>
using namespace std;
constexpr double PI = 3.14159265358979323846;
namespace fs = std::filesystem;

struct Vec3 {double x=0,y=0,z=0;};
struct Part {string type,group,color; double x=0,z=0,w=0,d=0,h=0;};
struct Rect {double x,z,w,d;};
struct Group {string type,zone,color; int count=0,cols=0; double w=0,d=0,h=0,space=8; string layout="auto";};
struct Spec {
  string kind="board",color="navy",material="aluminum",panels="rounded",keyAction="synth",keyColor="ivory";
  double width=0,depth=0,tilt=0; bool fixedWidth=false,fixedDepth=false;
  int keys=0; bool keySpecified=false;
  vector<Group> groups;
  int pitch=0,mod=0;
  vector<string> advisories;
};

string lower(string s){transform(s.begin(),s.end(),s.begin(),[](unsigned char c){return (char)tolower(c);});return s;}
string trim(string s){auto a=s.find_first_not_of(" \t\r\n"), b=s.find_last_not_of(" \t\r\n");return a==string::npos?"":s.substr(a,b-a+1);}
string get(const map<string,string>&a,const string&k,string d=""){auto i=a.find(k);return i==a.end()?d:i->second;}
int getInt(const map<string,string>&a,const string&k,int d=0){auto v=get(a,k);return v.empty()?d:stoi(v);}
double getDouble(const map<string,string>&a,const string&k,double d=0){auto v=get(a,k);return v.empty()?d:stod(v);}
pair<int,int> parseGrid(string s){auto x=s.find('x');if(x==string::npos)throw runtime_error("grid must look like 4x2");int a=stoi(s.substr(0,x)),b=stoi(s.substr(x+1));if(a<1||b<1||a>50||b>50)throw runtime_error("grid dimensions must be 1..50");return {a,b};}
string jsonEscape(const string&s){string t;for(char c:s){if(c=='"'||c=='\\'){t+='\\';t+=c;}else if(c=='\n')t+="\\n";else if((unsigned char)c<32)t+=' ';else t+=c;}return t;}
void positive(int x,const string&label){if(x<0||x>256)throw runtime_error(label+" count must be between 0 and 256");}

Spec parse(const string&path){
  ifstream f(path);if(!f)throw runtime_error("Cannot open specification: "+path);
  Spec s;string line;int ln=0;
  while(getline(f,line)){
    ++ln;
    // Allow '# comment' and hex color values (color=#aabbcc).
    auto comment=line.find(" #");if(comment!=string::npos)line.resize(comment);
    line=trim(line);if(line.empty()||line[0]=='#'||line.rfind("//",0)==0)continue;
    istringstream in(line);string cmd,word;in>>cmd;cmd=lower(cmd);map<string,string> a;
    while(in>>word){auto eq=word.find('=');if(eq==string::npos||eq==0||eq==word.size()-1)throw runtime_error("Line "+to_string(ln)+": expected key=value; got '"+word+"'");a[lower(word.substr(0,eq))]=lower(word.substr(eq+1));}
    try {
      if(cmd=="controllertype"||cmd=="instrument")s.kind=get(a,"controller",get(a,"type",s.kind));
      else if(cmd=="body"||cmd=="controller"){
        if(a.count("width")){s.width=getDouble(a,"width");s.fixedWidth=true;}
        if(a.count("depth")){s.depth=getDouble(a,"depth");s.fixedDepth=true;}
        s.material=get(a,"material",s.material);
        s.color=get(a,"color",s.color);
      } else if(cmd=="style"){
        s.color=get(a,"color",get(a,"body_color",s.color));s.material=get(a,"material",s.material);
        s.panels=get(a,"panels",get(a,"corners",s.panels));s.tilt=getDouble(a,"tilt",s.tilt);
      } else if(cmd=="keybed"){
        s.keys=getInt(a,"keys",49);s.keySpecified=true;
        s.keyAction=get(a,"type",get(a,"action",s.keyAction));
        // The key action controls the *visible keycap profile*, not the internal mechanics.
        static const set<string> actions={"synth","synth-action","unweighted","waterfall",
          "semi-weighted","semiweighted","weighted","hammer","hammer-action"};
        if(!actions.count(s.keyAction))throw runtime_error("Unsupported keybed type. Use unweighted, semi-weighted, weighted, or hammer");
        s.keyColor=get(a,"color",s.keyColor);
      } else if(cmd=="wheels"){
        s.pitch=getInt(a,"pitch",s.pitch);s.mod=getInt(a,"mod",s.mod);positive(s.pitch,"Pitch wheels");positive(s.mod,"Mod wheels");
      } else {
        string type,zone="auto",color="";int count=0,cols=0;
        double w=0,d=0,h=0,space=8;
        if(cmd=="knobs"||cmd=="encoders"){type="knob";w=19;d=19;h=12;space=10;color="slate";}
        else if(cmd=="faders"||cmd=="sliders"){type="fader";w=17;d=59;h=5;space=12;color="cyan";}
        else if(cmd=="pads"||cmd=="drumpads"){type="pad";w=27;d=27;h=5;space=5;color="purple";}
        else if(cmd=="buttons"){type="button";w=21;d=16;h=4;space=7;color="cyan";}
        else if(cmd=="switches"){type="switch";w=15;d=19;h=12;space=8;color="steel";}
        else if(cmd=="display"||cmd=="displays"){type="display";w=94;d=49;h=3;space=12;color="screen";}
        else if(cmd=="leds"||cmd=="indicators"){type="led";w=8;d=8;h=2;space=7;color="cyan";}
        else if(cmd=="footswitches"||cmd=="pedals"){type="footswitch";w=28;d=28;h=15;space=19;color="steel";}
        else if(cmd=="joystick"){type="joystick";w=35;d=35;h=20;space=12;color="purple";}
        else if(cmd=="xypad"||cmd=="touchpad"){type="xypad";w=80;d=58;h=2;space=12;color="screen";}
        else if(cmd=="ribbon"){type="ribbon";w=100;d=16;h=2;space=12;color="cyan";}
        else if(cmd=="ports"||cmd=="connections"){type="port";w=18;d=13;h=4;space=7;color="steel";}
        else throw runtime_error("Unsupported command '"+cmd+"'");
        count=getInt(a,"count",(type=="display"||type=="joystick"||type=="xypad"||type=="ribbon")?1:0);
        if(a.count("grid")){auto [c,r]=parseGrid(a.at("grid"));cols=c;count=c*r;}
        if(cmd=="buttons" && (a.count("regular")||a.count("soft")||a.count("clicky")||a.count("mechanical"))){
          int normal=getInt(a,"regular",getInt(a,"soft",0));int clicky=getInt(a,"clicky",getInt(a,"mechanical",0));
          positive(normal,"Regular buttons");positive(clicky,"Clicky buttons");
          double buttonSpacing=getDouble(a,"spacing",7);
          if(buttonSpacing<0||buttonSpacing>80)throw runtime_error("Button spacing out of range");
          if(normal)s.groups.push_back({"button",get(a,"zone","auto"),"cyan",normal,cols,21,16,4,buttonSpacing,get(a,"layout","auto")});
          if(clicky)s.groups.push_back({"clicky",get(a,"zone","auto"),"purple",clicky,0,20,18,8,buttonSpacing,get(a,"layout","auto")});
          continue;
        }
        if(type=="display"){
          string size=get(a,"size","medium");if(size=="small"){w=62;d=37;}else if(size=="large"){w=120;d=67;}
        }
        w=getDouble(a,"width",w);d=getDouble(a,"depth",d);space=getDouble(a,"spacing",space);
        positive(count,type);
        if(w<4||d<4||w>400||d>300||space<0||space>80)throw runtime_error("Component sizes or spacing out of range");
        string arrangement=get(a,"layout",get(a,"orientation","auto"));
        if(arrangement=="horizontal")arrangement="row";
        if(arrangement=="vertical")arrangement="column";
        if(arrangement!="auto"&&arrangement!="row"&&arrangement!="column"&&arrangement!="grid")throw runtime_error("layout must be auto, row, column or grid");
        if(count>0)s.groups.push_back({type,get(a,"zone",zone),get(a,"color",color),count,cols,w,d,h,space,arrangement});
      }
    }catch(const exception&e){throw runtime_error("Line "+to_string(ln)+": "+e.what());}
  }
  if(s.kind.find("keyboard")!=string::npos||s.kind.find("synth")!=string::npos){
    if(!s.keySpecified){s.keys=49;s.advisories.push_back("No keybed size specified; inferred a 49-key keybed. Override with KEYBED keys=... .");}
  }
  if(s.kind.find("foot")!=string::npos && s.keys>0)throw runtime_error("Foot controllers cannot include a piano keybed in this prototype");
  if(s.keys<0||s.keys>88)throw runtime_error("Key count must be 0..88");
  if(s.tilt<-20||s.tilt>25)throw runtime_error("Tilt must be from -20 to 25 degrees");
  if(s.fixedWidth && (s.width<180||s.width>4000))throw runtime_error("Width must be 180..4000 mm");
  if(s.fixedDepth && (s.depth<130||s.depth>1800))throw runtime_error("Depth must be 130..1800 mm");
  if(!s.fixedWidth)s.width=(s.keys?max(340.,s.keys*16.0+110.):(s.kind.find("foot")!=string::npos?360.:420.));
  if(!s.fixedDepth)s.depth=(s.keys?340.:(s.kind.find("foot")!=string::npos?200.:260.));
  return s;
}

bool overlaps(Rect a,Rect b,double pad=3){return a.x<b.x+b.w+pad&&a.x+a.w+pad>b.x&&a.z<b.z+b.d+pad&&a.z+a.d+pad>b.z;}
struct Layout {
  Spec spec; vector<Part> parts;vector<Rect> used;vector<string> warnings;
  mt19937 rng;int id=0;
  Layout(Spec s,unsigned seed,int variant):spec(s),rng(seed),id(variant){}
  double margin=12;
  void add(string type,string group,string color,double x,double z,double w,double d,double h){parts.push_back({type,group,color,x,z,w,d,h});}
  static bool isBlack(int semitone){int p=(semitone%12+12)%12;return p==1||p==3||p==6||p==8||p==10;}
  void addKeys(){
    double x=0,z=0,w=0,d=0;
    if(spec.keys){
      const int n=spec.keys;
      double side=(spec.pitch+spec.mod)?80:24;
      x=side; z=spec.depth*.55;
      w=spec.width-side-20;d=spec.depth*.39;
      if(d<65)throw runtime_error("Not enough depth for keybed");
      int whites=0;for(int i=0;i<n;i++)if(!isBlack(i))whites++;
      double keyW=w/whites;
      if(keyW<10.5)throw runtime_error("Keybed cannot fit "+to_string(n)+" keys. Increase width.");
      used.push_back({x-3,z-3,w+6,d+6});
      int wi=0;
      for(int i=0;i<n;i++){
        if(!isBlack(i)){add("white_key","keybed",spec.keyColor,x+wi*keyW,z,keyW-.65,d,5);wi++;}
        else add("black_key","keybed","black",x+wi*keyW-keyW*.33,z,keyW*.66,d*.64,11);
      }
    }
    int wheelCount=spec.pitch+spec.mod;
    if(wheelCount){
      // Keyboard wheels live beside the keys. Desktop wheels use an independent
      // bank near the lower left, so they're not silently omitted.
      double wz=spec.keys?z+min(15.,d*.08):spec.depth-52;
      double wh=spec.keys?min(29.,(d-30.)/max(1,wheelCount)):31.;
      for(int i=0;i<wheelCount;i++){
        double xx=spec.keys?19:19+i*43;
        double zz=spec.keys?wz+i*(wh+10):wz;
        if(zz+wh>spec.depth-10||xx+35>spec.width-10)throw runtime_error("Wheel area too small");
        used.push_back({xx,zz,35,wh});
        add("wheel","wheels",i<spec.pitch?"cyan":"purple",xx,zz,35,wh,12);
      }
    }
  }
  double topLimit() const {return spec.keys?spec.depth*.53:spec.depth-margin;}
  pair<double,double> preferred(string zone,double gw,double gd) const {
    string z=lower(zone);
    double x=(spec.width-gw)/2.,y=margin;
    if(z.find("left")!=string::npos||z=="auto")x=margin+5;
    if(z.find("right")!=string::npos)x=spec.width-gw-margin-5;
    if(z=="center")y=(topLimit()-gd)/2.;
    if(z.find("bottom")!=string::npos)y=topLimit()-gd-margin;
    if(id%3==2)y+=min(14.,gd*.18);  // Alternative layouts still respect the requested region.
    if(id%3==0 && z=="auto")x+=24;
    return {x,y};
  }
  struct Candidate {double score,x,z;int cols;};
  // A shared rectangle search for individual groups and paired control banks.
  // The rectangle may move to a nearby free region, but its internal alignment never changes.
  vector<Candidate> findLocations(const string&zone,double gw,double gd,int cols,double penalty=0){
    vector<Candidate> out;
    if(gw>spec.width-2*margin||gd>topLimit()-2*margin)return out;
    auto [px,pz]=preferred(zone,gw,gd);
    uniform_real_distribution<double> fuzz(0,3.5);
    for(double zz=margin;zz+gd<=topLimit()-margin+1e-6;zz+=5){
      for(double xx=margin;xx+gw<=spec.width-margin+1e-6;xx+=5){
        Rect r{xx,zz,gw,gd};bool clear=true;
        for(const auto&q:used)if(overlaps(r,q,4)){clear=false;break;}
        if(clear){
          const double deviation=hypot((xx-px)*.85,(zz-pz)*1.3);
          out.push_back({deviation+penalty+fuzz(rng),xx,zz,cols});
        }
      }
    }
    return out;
  }
  static Candidate pickBest(const vector<Candidate>&c){
    if(c.empty())throw runtime_error("No valid placement found");
    return *min_element(c.begin(),c.end(),[](const Candidate&a,const Candidate&b){return a.score<b.score;});
  }
  vector<int> choices(const Group&g) const {
    if(g.cols)return {g.cols};
    vector<int> cols;
    if(g.layout=="column")return {1};
    if(g.layout=="row")return {g.count};
    if(g.layout=="grid"){
      int natural=max(1,(int)ceil(sqrt((double)g.count)));
      return {natural};
    }
    // Horizontal rows are the default for knobs and faders, especially in a
    // center/top zone. A bank wraps only if a single row cannot fit.
    const bool strip=(g.type=="knob"||g.type=="fader") &&
      (g.zone=="center"||g.zone=="top"||g.zone=="auto"||g.zone=="top-left"||g.zone=="top-right");
    if(strip){for(int c=g.count;c>=1;--c)cols.push_back(c);return cols;}
    int natural=(g.type=="footswitch")?min(4,g.count):
      (g.type=="display")?1:min(6,g.count);
    cols={natural};
    if(natural>1)cols.push_back(natural-1);
    if(natural<g.count)cols.push_back(natural+1);
    return cols;
  }
  void addGroup(const Group&g){
    if(g.count<=0)return;
    vector<Candidate> candidates;
    for(int cols:choices(g)){
      int rows=(g.count+cols-1)/cols;
      double gw=cols*g.w+(cols-1)*g.space;
      double gd=rows*g.d+(rows-1)*g.space;
      // Prefer horizontal channels without overriding the user's explicit grid/column choice.
      double penalty=(g.layout=="auto" && (g.type=="knob"||g.type=="fader"))?(g.count-cols)*14.:0.;
      auto options=findLocations(g.zone,gw,gd,cols,penalty);
      candidates.insert(candidates.end(),options.begin(),options.end());
      if(g.layout=="auto"&&!candidates.empty()&&cols==g.count)break;
    }
    if(candidates.empty())throw runtime_error("Not enough room for "+to_string(g.count)+" "+g.type+" controls. Increase body dimensions or change layout.");
    Candidate best=pickBest(candidates);
    int rows=(g.count+best.cols-1)/best.cols;
    double gw=best.cols*g.w+(best.cols-1)*g.space,gd=rows*g.d+(rows-1)*g.space;
    used.push_back({best.x,best.z,gw,gd});
    for(int i=0;i<g.count;i++){
      double x=best.x+(i%best.cols)*(g.w+g.space),z=best.z+(i/best.cols)*(g.d+g.space);
      add(g.type,g.type,g.color,x,z,g.w,g.d,g.h);
    }
    if(g.zone!="auto"){
      auto [px,pz]=preferred(g.zone,gw,gd);
      if(hypot(best.x-px,best.z-pz)>75)warnings.push_back(g.type+" group was repositioned to avoid collisions.");
    }
  }
  // Treat matching knob/fader groups as one channel bank: one knob directly
  // above each fader, all channels evenly spaced left-to-right. This fixes
  // the old behavior of placing center-zone groups independently.
  void addChannelBank(const Group&knob,const Group&fader){
    const int count=knob.count;
    const double step=max(knob.w+knob.space,fader.w+fader.space);
    const double cellW=max(knob.w,fader.w);
    const double padZ=max(10.,min(knob.space,fader.space));
    const double cellD=knob.d+padZ+fader.d;
    vector<Candidate> candidates;
    int requestedCols=count;
    if(knob.cols)requestedCols=knob.cols;
    if(fader.cols)requestedCols=fader.cols;
    bool explicitGrid=knob.cols||fader.cols||knob.layout=="grid"||fader.layout=="grid";
    bool column=knob.layout=="column"||fader.layout=="column";
    bool row=knob.layout=="row"||fader.layout=="row";
    int lo=explicitGrid?requestedCols:(column?1:(row?count:1));
    int hi=explicitGrid?requestedCols:(column?1:count);
    for(int cols=hi;cols>=lo;--cols){
      int rows=(count+cols-1)/cols;
      double gw=cellW+(cols-1)*step,gd=rows*cellD+(rows-1)*12;
      double penalty=(count-cols)*18.;
      auto opts=findLocations(knob.zone,gw,gd,cols,penalty);
      candidates.insert(candidates.end(),opts.begin(),opts.end());
      if(!opts.empty()&&!explicitGrid&&!column)break;
    }
    if(candidates.empty())throw runtime_error("Paired knob/fader bank cannot fit. Increase body size or reduce controls.");
    Candidate best=pickBest(candidates);
    int rows=(count+best.cols-1)/best.cols;
    double gw=cellW+(best.cols-1)*step,gd=rows*cellD+(rows-1)*12;
    used.push_back({best.x,best.z,gw,gd});
    for(int i=0;i<count;i++){
      int c=i%best.cols,r=i/best.cols;
      double center=best.x+cellW/2+c*step;
      double z=best.z+r*(cellD+12);
      add("knob","channel_bank",knob.color,center-knob.w/2,z,knob.w,knob.d,knob.h);
      add("fader","channel_bank",fader.color,center-fader.w/2,z+knob.d+padZ,fader.w,fader.d,fader.h);
    }
    warnings.push_back("Aligned "+to_string(count)+" knob/fader channels in a shared control bank.");
  }
  void build(){
    add("body","chassis",spec.color,0,0,spec.width,spec.depth,17);
    addKeys();
    vector<Group> gs=spec.groups;
    // Pair equally sized control groups only when the customer asked for the
    // same zone and compatible layout; never override conflicting regions.
    vector<bool> merged(gs.size(),false);
    for(size_t i=0;i<gs.size();i++){
      if(gs[i].type!="knob"||merged[i])continue;
      for(size_t j=0;j<gs.size();j++){
        if(gs[j].type!="fader"||merged[j]||gs[i].count!=gs[j].count||gs[i].zone!=gs[j].zone)continue;
        if((gs[i].cols&&gs[j].cols&&gs[i].cols!=gs[j].cols)||
          (gs[i].layout!="auto"&&gs[j].layout!="auto"&&gs[i].layout!=gs[j].layout))continue;
        addChannelBank(gs[i],gs[j]);merged[i]=merged[j]=true;break;
      }
    }
    vector<Group> rest;
    for(size_t i=0;i<gs.size();++i)if(!merged[i])rest.push_back(gs[i]);
    stable_sort(rest.begin(),rest.end(),[](const Group&a,const Group&b){
      auto area=[](const Group&v){int c=v.cols?v.cols:min(v.count,(v.type=="display"?1:6));
        return (c*v.w+(c-1)*v.space)*(((v.count+c-1)/c)*v.d+(((v.count+c-1)/c)-1)*v.space);};
      return area(a)>area(b);
    });
    for(const auto&g:rest)addGroup(g);
  }
  // Auto Best Fit for desktop boards: preserve each control bank's internal
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
  bool tryBuild(){
    const double startWidth=spec.width,startDepth=spec.depth;
    for(int attempt=0;attempt<14;attempt++){
      parts.clear();used.clear();warnings.clear();
      try{
        build();fitAutoBoard();
        if(attempt>0 && (spec.width>startWidth+1e-6 || spec.depth>startDepth+1e-6))
          warnings.push_back("Automatically enlarged enclosure to fit all controls.");
        return true;
      }
      catch(const runtime_error&){
        if(spec.fixedWidth&&spec.fixedDepth)throw;
        if(attempt==13)throw;
        if(!spec.fixedWidth)spec.width=min(4000.,spec.width+max(45.,spec.width*.085));
        if(!spec.fixedDepth)spec.depth=min(1800.,spec.depth+max(30.,spec.depth*.11));
      }
    }
    return false;
  }
};

Vec3 color(string c){
  static const map<string,Vec3> colors={{"navy",{.10,.15,.28}},{"black",{.065,.073,.105}},{"dark",{.065,.073,.105}},
  {"white",{.93,.94,.97}},{"ivory",{.93,.93,.89}},{"red",{.90,.26,.32}},{"blue",{.26,.50,.91}},
  {"cyan",{.31,.84,.83}},{"teal",{.22,.76,.72}},{"purple",{.63,.48,.98}},{"pink",{.92,.40,.73}},
  {"steel",{.62,.69,.77}},{"silver",{.75,.77,.83}},{"slate",{.34,.43,.60}},{"wood",{.55,.36,.23}},
  {"screen",{.075,.35,.48}},{"green",{.32,.81,.55}},{"gold",{.91,.70,.31}}};
  auto it=colors.find(c);if(it!=colors.end())return it->second;
  if(c.size()==7&&c[0]=='#')try{return {stoi(c.substr(1,2),nullptr,16)/255.,stoi(c.substr(3,2),nullptr,16)/255.,stoi(c.substr(5,2),nullptr,16)/255.};}catch(...){}
  return {.31,.40,.55};
}
string css(string c){Vec3 v=color(c);ostringstream f;f<<"#"<<hex<<setfill('0');for(double a:{v.x,v.y,v.z})f<<setw(2)<<int(max(0.,min(255.,round(a*255.))));return f.str();}
struct Vertex {Vec3 p,n,c;};
struct Mesh {
  vector<Vertex> vertices;int faceCount=0;double angle=0;
  static Vec3 shade(Vec3 c,double f){return {min(1.,max(0.,c.x*f)),min(1.,max(0.,c.y*f)),min(1.,max(0.,c.z*f))};}
  void tri(Vec3 a,Vec3 b,Vec3 c,Vec3 rgb){
    Vec3 u{b.x-a.x,b.y-a.y,b.z-a.z},v{c.x-a.x,c.y-a.y,c.z-a.z};
    Vec3 n{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
    double l=sqrt(n.x*n.x+n.y*n.y+n.z*n.z);if(l>1e-9){n.x/=l;n.y/=l;n.z/=l;}
    for(auto p:{a,b,c})vertices.push_back({p,n,rgb});
    faceCount++;
  }
  void quad(Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 rgb){tri(a,b,c,rgb);tri(a,c,d,rgb);}
  void cube(double x,double y,double z,double w,double h,double d,Vec3 c){
    if(w<=0||h<=0||d<=0)return;
    Vec3 a{x,y,z},b{x+w,y,z},cc{x+w,y,z+d},dd{x,y,z+d};
    Vec3 A{x,y+h,z},B{x+w,y+h,z},C{x+w,y+h,z+d},D{x,y+h,z+d};
    quad(A,D,C,B,c);quad(a,b,cc,dd,shade(c,.60));
    quad(a,A,B,b,shade(c,.82));quad(b,B,C,cc,shade(c,.75));
    quad(cc,C,D,dd,shade(c,.70));quad(dd,D,A,a,shade(c,.90));
  }
  void cylinder(double x,double y,double z,double rad,double h,Vec3 col,int seg=24){
    if(rad<=0||h<=0)return;
    for(int i=0;i<seg;i++){
      double p=2*PI*i/seg,q=2*PI*(i+1)/seg;
      Vec3 a{x+cos(p)*rad,y,z+sin(p)*rad},b{x+cos(q)*rad,y,z+sin(q)*rad};
      Vec3 A{a.x,y+h,a.z},B{b.x,y+h,b.z};
      quad(a,A,B,b,shade(col,.83));tri({x,y+h,z},B,A,col);
    }
  }
  // Sloped, tapered surfaces make knobs and metal knobs visibly different from cylinders.
  void taperedCylinder(double x,double y,double z,double bottomR,double topR,double h,Vec3 col,int seg=40){
    if(bottomR<=0||topR<=0||h<=0)return;
    for(int i=0;i<seg;i++){
      double p=2*PI*i/seg,q=2*PI*(i+1)/seg;
      Vec3 a{x+cos(p)*bottomR,y,z+sin(p)*bottomR};
      Vec3 b{x+cos(q)*bottomR,y,z+sin(q)*bottomR};
      Vec3 A{x+cos(p)*topR,y+h,z+sin(p)*topR};
      Vec3 B{x+cos(q)*topR,y+h,z+sin(q)*topR};
      quad(a,A,B,b,shade(col,.87));tri({x,y+h,z},B,A,shade(col,1.08));
    }
  }
  void ring(double x,double y,double z,double inner,double outer,Vec3 col,int seg=48){
    if(inner>=outer)return;
    for(int i=0;i<seg;i++){
      double p=2*PI*i/seg,q=2*PI*(i+1)/seg;
      auto xy=[&](double a,double r){return Vec3{x+cos(a)*r,y,z+sin(a)*r};};
      quad(xy(p,outer),xy(p,inner),xy(q,inner),xy(q,outer),col);
    }
  }
  vector<Vec3> outline(double x,double z,double w,double d,double r,double y,int steps=6){
    r=max(0.,min({r,w*.49,d*.49}));
    vector<Vec3> out;out.reserve((steps+1)*4);
    array<tuple<double,double,double>,4> cs={
      make_tuple(x+w-r,z+r,-PI/2),make_tuple(x+w-r,z+d-r,0.),
      make_tuple(x+r,z+d-r,PI/2),make_tuple(x+r,z+r,PI)
    };
    for(const auto &c:cs){auto [cx,cz,theta]=c;
      for(int i=0;i<=steps;i++){
        double a=theta+PI/2*i/steps;out.push_back({cx+r*cos(a),y,cz+r*sin(a)});
      }
    }
    return out;
  }
  // Rounded, stepped, chamfered panel: rounded footprint, bevel around its upper edge,
  // and physically distinct side/top material shading. No textures are required.
  void roundedPrism(double x,double y,double z,double w,double h,double d,double radius,double bevel,Vec3 c){
    if(w<=0||d<=0||h<=0)return;
    bevel=max(0.,min({bevel,w*.18,d*.18,h*.43}));
    auto base=outline(x,z,w,d,radius,y);
    auto shoulders=outline(x,z,w,d,radius,y+h-bevel);
    auto top=outline(x+bevel,z+bevel,w-2*bevel,d-2*bevel,max(0.,radius-bevel),y+h);
    Vec3 topCenter{x+w*.5,y+h,z+d*.5},botCenter{x+w*.5,y,z+d*.5};
    for(size_t i=0;i<base.size();++i){size_t j=(i+1)%base.size();
      quad(base[i],shoulders[i],shoulders[j],base[j],shade(c,.77));
      quad(shoulders[i],top[i],top[j],shoulders[j],shade(c,.91));
      tri(topCenter,top[j],top[i],shade(c,1.035));
      tri(botCenter,base[i],base[j],shade(c,.56));
    }
  }
  void bevelPlate(double x,double y,double z,double w,double h,double d,double r,Vec3 c){
    roundedPrism(x,y,z,w,h,d,r,min(.85,h*.35),c);
  }
  // A thin cylindrical shaft from a to b. Used for realistically inclined switch levers.
  void rod(Vec3 a,Vec3 b,double r0,double r1,Vec3 c,int seg=16){
    Vec3 dir{b.x-a.x,b.y-a.y,b.z-a.z};double len=sqrt(dir.x*dir.x+dir.y*dir.y+dir.z*dir.z);
    if(len<1e-5)return;
    dir={dir.x/len,dir.y/len,dir.z/len};
    Vec3 temp=fabs(dir.y)<.9?Vec3{0,1,0}:Vec3{1,0,0};
    Vec3 u{dir.y*temp.z-dir.z*temp.y,dir.z*temp.x-dir.x*temp.z,dir.x*temp.y-dir.y*temp.x};
    double ul=sqrt(u.x*u.x+u.y*u.y+u.z*u.z);u={u.x/ul,u.y/ul,u.z/ul};
    Vec3 v{dir.y*u.z-dir.z*u.y,dir.z*u.x-dir.x*u.z,dir.x*u.y-dir.y*u.x};
    auto pt=[&](Vec3 p,double rad,double t){return Vec3{p.x+rad*(u.x*cos(t)+v.x*sin(t)),p.y+rad*(u.y*cos(t)+v.y*sin(t)),p.z+rad*(u.z*cos(t)+v.z*sin(t))};};
    for(int i=0;i<seg;i++){
      double p=2*PI*i/seg,q=2*PI*(i+1)/seg;
      quad(pt(a,r0,p),pt(b,r1,p),pt(b,r1,q),pt(a,r0,q),shade(c,.88));
      tri(b,pt(b,r1,q),pt(b,r1,p),shade(c,1.05));
    }
  }
  void keyWhite(const Part&p,const string&profile){
    double x=p.x,z=p.z,w=p.w,d=p.d,deck=19.;
    Vec3 ivory=shade(color(p.color),1.035);
    if(profile=="waterfall"){
      // Synth-action / unweighted 'waterfall' keys: smooth continuous rounded nose.
      // Deliberately NO protruding lower piano-key apron/lip.
      roundedPrism(x,deck,z,w,5.1,d,1.7,1.1,ivory);
      roundedPrism(x+.30,deck+4.2,z+.8,w-.60,1.25,d-1.65,1.1,.37,shade(ivory,1.07));
    }else{
      const bool weighted=(profile=="weighted");
      double baseH=weighted?7.4:6.2;
      double lip=weighted?3.0:1.6;
      // Key shank, distinct upper top cover, and the short overhanging
      // 'diving-board' front apron visible on piano-shaped keys.
      roundedPrism(x,deck,z,w,baseH,d-1.8,1.15,.63,shade(ivory,.96));
      roundedPrism(x+.16,deck+baseH-1.3,z+.5,w-.32,1.6,d-1.55,1.10,.65,ivory);
      // Protruding front (towards positive z), with a downward vertical lip.
      roundedPrism(x+.10,deck+baseH-(weighted?3.9:2.6),z+d-7.5,
                   w-.20,weighted?4.3:2.9,7.5+lip,1.10,.75,shade(ivory,1.02));
      // Visible underside step on weighted piano-style caps.
      if(weighted)roundedPrism(x+.25,deck+1.85,z+d-3.2,w-.5,2.45,4.0,1.05,.55,shade(ivory,.91));
    }
  }
  void keyBlack(const Part&p,const string&profile){
    double x=p.x,z=p.z,w=p.w,d=p.d,deck=19.;
    double thick=profile=="waterfall"?7.0:8.6;
    Vec3 base=shade(color("black"),1.34);
    // Black-key heels are wider than the gently sloping playing surface.
    roundedPrism(x,deck+4.6,z,w,thick,d,1.8,.8,base);
    roundedPrism(x+.8,deck+4.6+thick-.5,z+1,w-1.6,1.1,d-5,1.1,.45,shade(base,1.24));
    // Sloped bevel at the playing tip for a molded keycap instead of a box.
    roundedPrism(x+1.0,deck+4.6+thick-1.9,z+d-8,w-2,1.6,6.4,1.3,.65,shade(base,1.1));
  }
  // Vertically mounted wheel: unlike an upright knob, the curved tread rotates
  // in the Y-Z plane. Upper half visibly emerges from its recessed well.
  void verticalWheel(double cx,double centerY,double cz,double radius,double thickness,Vec3 col){
    const int segments=48;
    double x0=cx-thickness*.5,x1=cx+thickness*.5;
    for(int i=0;i<segments;i++){
      double a=2*PI*i/segments,b=2*PI*(i+1)/segments;
      auto p=[&](double x,double angle,double r){return Vec3{x,centerY+sin(angle)*r,cz+cos(angle)*r};};
      quad(p(x0,a,radius),p(x0,b,radius),p(x1,b,radius),p(x1,a,radius),shade(col,.85));
      tri({x1,centerY,cz},p(x1,a,radius),p(x1,b,radius),shade(col,1.04));
      tri({x0,centerY,cz},p(x0,b,radius),p(x0,a,radius),shade(col,.72));
    }
    for(int i=0;i<18;i++){
      double a=2*PI*i/18;
      Vec3 a0{x0-.1,centerY+sin(a)*(radius+.23),cz+cos(a)*(radius+.23)};
      Vec3 b0{x1+.1,a0.y,a0.z};
      rod(a0,b0,.32,.32,shade(col,1.32),6);
    }
  }
  void build(const Layout &l){
    angle=l.spec.tilt*PI/180.;
    constexpr double deck=19.;
    string keyProfile=l.spec.keyAction;
    if(keyProfile=="synth"||keyProfile=="unweighted"||keyProfile=="synth-action"||keyProfile=="waterfall")keyProfile="waterfall";
    else if(keyProfile=="weighted"||keyProfile=="hammer"||keyProfile=="hammer-action")keyProfile="weighted";
    else keyProfile="semi-weighted";
    int index=0;
    for(const Part&p:l.parts){
      auto c=color(p.color);double x=p.x,z=p.z,w=p.w,d=p.d;
      double cx=x+w*.5,cz=z+d*.5;
      if(p.type=="body"){
        // Inset brushed enclosure with a chamfered outer silhouette, side cheek
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
        }
      }else if(p.type=="knob"){
        double r=min(w,d)*.43,h=max(7.,p.h);
        cylinder(cx,deck,cz,r,1.15,shade(color("steel"),.78),36);
        ring(cx,deck+1.3,cz,r*.82,r*.97,shade(c,1.2));
        taperedCylinder(cx,deck+1.2,cz,r*.81,r*.73,2.6,shade(color("dark"),1.55),40);
        taperedCylinder(cx,deck+3.5,cz,r*.73,r*.66,h-3.2,shade(color("slate"),.87),40);
        cylinder(cx,deck+h+.3,cz,r*.63,1.25,shade(color("steel"),.9),40);
        for(int j=0;j<20;j++){
          double a=2*PI*j/20,ridge=r*.725;
          rod({cx+ridge*cos(a),deck+5.2,cz+ridge*sin(a)},
              {cx+ridge*.91*cos(a),deck+h-1,cz+ridge*.91*sin(a)},.24,.22,shade(color("steel"),1.12),6);
        }
        cube(cx-.8,deck+h+1.56,cz-r*.54,1.6,.22,r*.32,color("ivory"));
        for(int j=0;j<9;j++){
          double a=PI*.67+j*PI*1.65/8.;
          double rr=r*1.12;
          rod({cx+cos(a)*rr,deck+1.3,cz+sin(a)*rr},
              {cx+cos(a)*(rr+1.25),deck+1.3,cz+sin(a)*(rr+1.25)},.22,.22,color("silver"),5);
        }
      }else if(p.type=="fader"){
        // Metal outer bezel, recessed slider slot, calibrated ticks, and a
        // contoured thumb cap with molded grip ribs.
        roundedPrism(x,deck,z,w,1.15,d,2.5,.45,shade(color("steel"),.71));
        roundedPrism(cx-3.0,deck+1,z+4,6.0,.3,d-8,2.3,.12,color("black"));
        roundedPrism(cx-.65,deck+1.3,z+5,1.3,.30,d-10,.50,.1,shade(color("steel"),.62));
        for(int i=0;i<11;i++){
          double zz=z+5.4+i*(d-10.8)/10.;
          double len=(i%5==0)?3.3:1.75;
          cube(x+.8,deck+1.20,zz,len,.18,.52,shade(color("silver"),.85));
          cube(x+w-.8-len,deck+1.20,zz,len,.18,.52,shade(color("silver"),.85));
        }
        double pos=.46,capZ=z+5+(d-10)*pos;
        cylinder(cx,deck+1.4,capZ,1.35,3.4,color("steel"),14);
        roundedPrism(x-2,deck+4.25,capZ-5.6,w+4,4.35,11.2,2.8,1.25,shade(color("slate"),.68));
        roundedPrism(x-1,deck+7.3,capZ-4.45,w+2,2.25,8.9,2.2,.55,shade(color("silver"),.97));
        for(int j=-2;j<=2;j++){
          double zz=capZ+j*1.16;
          cube(cx-w*.30,deck+9.5,zz,w*.60,.18,.40,shade(c,1.26));
        }
      }else if(p.type=="pad"){
        roundedPrism(x,deck,z,w,1.5,d,4.0,.7,shade(color("dark"),1.0));
        roundedPrism(x+1.9,deck+1.5,z+1.9,w-3.8,max(2.5,p.h-1.4),d-3.8,3.5,1.1,shade(c,1.08));
        roundedPrism(x+4,deck+max(3.3,p.h),z+3.3,w-8,.33,d-7,2.2,.1,shade(c,1.23));
      }else if(p.type=="button"||p.type=="clicky"){
        bool mechanical=p.type=="clicky";
        roundedPrism(x,deck,z,w,1.45,d,2.75,.55,shade(color("dark"),1.05));
        if(mechanical){
          roundedPrism(x+3.8,deck+1.4,z+2.9,w-7.6,3.2,d-5.8,2.2,.65,shade(color("steel"),.68));
          roundedPrism(x+1.5,deck+4.4,z+1.0,w-3,5.0,d-2,3.0,1.35,shade(c,1.1));
          roundedPrism(x+4,deck+9.0,z+3.4,w-8,.65,d-6.8,1.8,.22,shade(c,1.2));
        }else{
          roundedPrism(x+1.3,deck+1.4,z+1.5,w-2.6,2.6,d-3,2.75,.85,shade(c,1.10));
          cube(x+w*.25,deck+4.1,z+d*.43,w*.50,.12,.65,shade(color("white"),.82));
        }
      }else if(p.type=="display"||p.type=="xypad"){
        roundedPrism(x,deck,z,w,2.7,d,4.5,1.1,shade(color("black"),1.4));
        roundedPrism(x+2.2,deck+2.7,z+2.2,w-4.4,1.0,d-4.4,3.8,.35,shade(color("steel"),.60));
        roundedPrism(x+4.8,deck+3.55,z+4.8,w-9.6,.22,d-9.6,2.1,.07,shade(color("screen"),.92));
        // Geometry-only user interface elements; no external texture dependencies.
        if(p.type=="display"){
          double z0=z+d*.52;
          for(int i=0;i<23;i++){
            double xx=x+8+i*(w-16)/22.;
            double y0=deck+3.80;
            double zz=z0+sin(i*.47)*d*.13+sin(i*.13)*d*.05;
            if(i>0){double prevX=x+8+(i-1)*(w-16)/22.;
              double prevZ=z0+sin((i-1)*.47)*d*.13+sin((i-1)*.13)*d*.05;
              rod({prevX,y0,prevZ},{xx,y0,zz},.43,.43,shade(color("cyan"),1.26),6);
            }
          }
          roundedPrism(x+8,deck+3.82,z+9,w*.30,.20,1.5,.5,.05,shade(color("cyan"),1.10));
          for(int i=0;i<5;i++){
            double xx=x+w*.52+i*(w*.38/5);
            double ht=(2+i%3)*d*.045;
            roundedPrism(xx,deck+3.82,z+d*.73-ht,3.0,.20,ht,.65,.04,shade(color("teal"),1.12));
          }
        }else{
          roundedPrism(x+w*.22,deck+3.82,z+6,w*.56,.2,1.2,.4,.06,shade(color("cyan"),1.3));
        }
        // Screws on each display corner.
        for(double px:{x+2.8,x+w-2.8})for(double zz:{z+2.8,z+d-2.8})
          cylinder(px,deck+2.7,zz,.78,.25,color("steel"),10);
      }else if(p.type=="switch"){
        cylinder(cx,deck,cz,min(w,d)*.40,1.1,shade(color("steel"),.8),28);
        ring(cx,deck+1.16,cz,min(w,d)*.23,min(w,d)*.37,shade(color("steel"),1.07),28);
        cylinder(cx,deck+1.2,cz,3.5,2.,shade(color("dark"),1.25),20);
        // Angled chrome toggle stem with a rounded grip.
        Vec3 a{cx,deck+3,cz},b{cx+3.1,deck+15,cz-1.9};
        rod(a,b,1.8,1.2,shade(color("silver"),1.03),18);
        cylinder(b.x,deck+15,b.z,2.6,2.9,shade(color("steel"),.93),20);
      }else if(p.type=="wheel"){
        roundedPrism(x,deck-.12,z,w,1.0,d,3.4,.38,shade(color("dark"),.85));
        double r=min(w*.33,d*.40);
        roundedPrism(cx-6,deck+.9,cz-r*.82,12,.25,r*1.64,2,.1,color("black"));
        verticalWheel(cx,deck+1.0,cz,r,8.8,shade(c,.97));
      }else if(p.type=="white_key")keyWhite(p,keyProfile);
      else if(p.type=="black_key")keyBlack(p,keyProfile);
      else if(p.type=="led"){
        cylinder(cx,deck,cz,min(w,d)*.44,.72,shade(color("dark"),1.0),24);
        ring(cx,deck+.75,cz,min(w,d)*.23,min(w,d)*.37,shade(color("steel"),.92),24);
        roundedPrism(cx-w*.23,deck+.75,cz-d*.23,w*.46,1.6,d*.46,w*.21,.60,shade(c,1.42));
      }else if(p.type=="footswitch"){
        taperedCylinder(cx,deck,cz,min(w,d)*.46,min(w,d)*.35,3.6,shade(color("steel"),.77),32);
        cylinder(cx,deck+3.7,cz,min(w,d)*.26,3.,shade(color("silver"),.95),28);
        taperedCylinder(cx,deck+6.6,cz,min(w,d)*.22,min(w,d)*.25,max(5.,p.h-6.),shade(color("silver"),1.03),28);
        cylinder(cx,deck+p.h+2,cz,min(w,d)*.27,1.0,shade(color("steel"),.94),28);
      }else if(p.type=="joystick"){
        roundedPrism(x,deck,z,w,1.4,d,4.,.5,color("dark"));
        cylinder(cx,deck+1.4,cz,min(w,d)*.30,2.2,color("black"),32);
        rod({cx,deck+3.0,cz},{cx+3.0,deck+p.h*.83,cz-1.5},2.4,1.8,color("steel"),18);
        taperedCylinder(cx+3,deck+p.h*.74,cz-1.5,6.6,5.5,6.6,shade(c,1.05),32);
      }else if(p.type=="ribbon"){
        roundedPrism(x,deck,z,w,1.0,d,3.,.35,color("black"));
        roundedPrism(x+3,deck+1.0,z+2,w-6,.45,d-4,2.2,.12,shade(c,.9));
        roundedPrism(x+w*.5-1,deck+1.45,z+3,2,.15,d-6,.6,.07,color("white"));
      }else if(p.type=="port"){
        roundedPrism(x,deck,z,w,1.2,d,2,.5,shade(color("steel"),.75));
        roundedPrism(x+3,deck+1.1,z+3,w-6,.4,d-6,1,.12,color("black"));
      }else roundedPrism(x,deck,z,w,p.h,d,1.5,.5,c);
      ++index;
    }
  }
  void obj(const string&path)const{
    ofstream o(path);if(!o)throw runtime_error("Cannot write OBJ: "+path);
    o<<"# Midreation C++ procedural OBJ; units=mm; vertex colors embedded\n";
    o<<fixed<<setprecision(4);
    double ca=cos(angle),sa=sin(angle);
    for(auto v:vertices){double yy=v.p.y*ca+v.p.z*sa,zz=-v.p.y*sa+v.p.z*ca;
      o<<"v "<<v.p.x<<' '<<yy<<' '<<zz<<' '<<v.c.x<<' '<<v.c.y<<' '<<v.c.z<<'\n';
    }
    for(size_t i=0;i<vertices.size();i+=3)o<<"f "<<i+1<<' '<<i+2<<' '<<i+3<<'\n';
  }
};
void svg(const Layout &l,const string &path){
  ofstream f(path);double w=l.spec.width,d=l.spec.depth;
  f<<"<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"-18 -18 "<<w+36<<' '<<d+36<<"\">\n";
  f<<"<rect x=\"-18\" y=\"-18\" width=\""<<w+36<<"\" height=\""<<d+36<<"\" fill=\"#f4f7fb\"/>\n";
  for(const Part&p:l.parts){
    const string c=css(p.color);double x=p.x,z=p.z,ww=p.w,dd=p.d,cx=x+ww*.5,cz=z+dd*.5;
    if(p.type=="body"){
      f<<"<rect x=\"0\" y=\"3\" width=\""<<w<<"\" height=\""<<d<<"\" rx=\"11\" fill=\"#c8d0df\"/>\n";
      f<<"<rect x=\"0\" y=\"0\" width=\""<<w<<"\" height=\""<<d<<"\" rx=\"11\" fill=\""<<c<<"\" stroke=\"#aab6c9\" stroke-width=\"1.2\"/>\n";
      for(double px:{10.,w-10.})for(double zz:{10.,d-10.})f<<"<circle cx=\""<<px<<"\" cy=\""<<zz<<"\" r=\"1.35\" fill=\"#96a0ae\"/>\n";
    }else if(p.type=="knob"){
      double r=min(ww,dd)*.43;
      f<<"<circle cx=\""<<cx<<"\" cy=\""<<cz<<"\" r=\""<<r<<"\" fill=\"#313a49\" stroke=\"#9cabbc\" stroke-width=\".9\"/>\n";
      f<<"<circle cx=\""<<cx<<"\" cy=\""<<cz<<"\" r=\""<<r*.68<<"\" fill=\""<<c<<"\" stroke=\"#202d3f\" stroke-width=\".5\"/>\n";
      f<<"<line x1=\""<<cx<<"\" y1=\""<<cz-r*.25<<"\" x2=\""<<cx<<"\" y2=\""<<cz-r*.60<<"\" stroke=\"#ffffff\" stroke-width=\"1.3\"/>\n";
    }else if(p.type=="fader"){
      f<<"<rect x=\""<<x+ww*.33<<"\" y=\""<<z<<"\" width=\""<<ww*.34<<"\" height=\""<<dd<<"\" rx=\"1.3\" fill=\"#202838\"/>\n";
      f<<"<rect x=\""<<x-1<<"\" y=\""<<z+dd*.42<<"\" width=\""<<ww+2<<"\" height=\""<<dd*.15<<"\" rx=\"2\" fill=\"#3b4454\" stroke=\"#a4b5c7\" stroke-width=\".5\"/>\n";
      f<<"<rect x=\""<<x+1<<"\" y=\""<<z+dd*.485<<"\" width=\""<<ww-2<<"\" height=\"1.1\" fill=\""<<c<<"\"/>\n";
    }else if(p.type=="pad"||p.type=="clicky"||p.type=="button"){
      double radius=p.type=="pad"?3.3:2.4;
      f<<"<rect x=\""<<x<<"\" y=\""<<z+1<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\""<<radius<<"\" fill=\"#3b4555\"/>\n";
      f<<"<rect x=\""<<x+1<<"\" y=\""<<z<<"\" width=\""<<ww-2<<"\" height=\""<<dd-2<<"\" rx=\""<<radius<<"\" fill=\""<<c<<"\" stroke=\"#ffffff\" stroke-opacity=\".35\"/>\n";
    }else if(p.type=="display"||p.type=="xypad"){
      f<<"<rect x=\""<<x<<"\" y=\""<<z<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\"3\" fill=\"#131c2b\" stroke=\"#8799af\"/>\n";
      f<<"<rect x=\""<<x+4<<"\" y=\""<<z+4<<"\" width=\""<<ww-8<<"\" height=\""<<dd-8<<"\" rx=\"1.6\" fill=\"#123c50\"/>\n";
      if(p.type=="display")for(int i=0;i<5;i++)f<<"<rect x=\""<<x+9+i*(ww-18)/6<<"\" y=\""<<z+dd*.38<<"\" width=\"2\" height=\""<<dd*.32*(.4+(i%3)*.2)<<"\" fill=\"#59d9dd\"/>\n";
    }else if(p.type=="footswitch"||p.type=="switch"||p.type=="joystick"||p.type=="led"){
      double r=min(ww,dd)*.43;
      f<<"<circle cx=\""<<cx<<"\" cy=\""<<cz<<"\" r=\""<<r<<"\" fill=\"#4b5667\" stroke=\"#8394a8\"/>\n";
      f<<"<circle cx=\""<<cx<<"\" cy=\""<<cz<<"\" r=\""<<r*.60<<"\" fill=\""<<c<<"\"/>\n";
    }else if(p.type=="wheel"){
      f<<"<rect x=\""<<x<<"\" y=\""<<z<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\"3\" fill=\"#141b28\"/>\n";
      f<<"<rect x=\""<<x+6<<"\" y=\""<<z+3<<"\" width=\""<<ww-12<<"\" height=\""<<dd-6<<"\" rx=\"3\" fill=\""<<c<<"\"/>\n";
    }else if(p.type=="white_key"){
      const string mode=l.spec.keyAction;
      const bool waterfall=(mode=="synth"||mode=="synth-action"||mode=="unweighted"||mode=="waterfall");
      f<<"<rect x=\""<<x<<"\" y=\""<<z<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\""<<(waterfall?1.9:1.1)<<"\" fill=\""<<c<<"\" stroke=\"#a8adb4\" stroke-width=\".55\"/>\n";
      if(!waterfall){
        // A thin front-apron seam is visible on piano-style keycaps but not waterfall keys.
        f<<"<line x1=\""<<x+.5<<"\" x2=\""<<x+ww-.5<<"\" y1=\""<<z+dd-5<<"\" y2=\""<<z+dd-5<<"\" stroke=\"#a8acb3\" stroke-width=\".65\"/>\n";
      }
    }else if(p.type=="black_key"){
      f<<"<rect x=\""<<x<<"\" y=\""<<z<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\"2.1\" fill=\"#191b21\" stroke=\"#090c12\" stroke-width=\".5\"/>\n";
      f<<"<line x1=\""<<x+2<<"\" y1=\""<<z+2<<"\" x2=\""<<x+ww-2<<"\" y2=\""<<z+2<<"\" stroke=\"#646772\" stroke-opacity=\".6\"/>\n";
    }else{
      f<<"<rect x=\""<<x<<"\" y=\""<<z<<"\" width=\""<<ww<<"\" height=\""<<dd<<"\" rx=\"1.6\" fill=\""<<c<<"\" stroke=\"#8090aa\" stroke-width=\".6\"/>\n";
    }
  }
  f<<"</svg>\n";
}
void json(const Layout &l,const Mesh &mesh,const string &path){
  ofstream o(path);if(!o)throw runtime_error("Cannot write JSON: "+path);
  o<<fixed<<setprecision(3);
  o<<"{\"kind\":\""<<jsonEscape(l.spec.kind)<<"\",\"width\":"<<l.spec.width<<",\"depth\":"<<l.spec.depth<<",\"tilt\":"<<l.spec.tilt;
  string profile=l.spec.keyAction;
  if(profile=="synth"||profile=="synth-action"||profile=="unweighted"||profile=="waterfall")profile="waterfall";
  else if(profile=="weighted"||profile=="hammer"||profile=="hammer-action")profile="weighted";
  else profile="semi-weighted";
  o<<",\"material\":\""<<jsonEscape(l.spec.material)<<"\",\"bodyColor\":\""<<jsonEscape(l.spec.color)<<"\",\"variant\":"<<l.id;
  o<<",\"keyAction\":\""<<jsonEscape(l.spec.keyAction)<<"\",\"keycapProfile\":\""<<profile<<"\"";
  o<<",\"triangles\":"<<mesh.faceCount<<",\"parts\":[";
  for(size_t i=0;i<l.parts.size();i++){
    if(i)o<<',';
    auto &p=l.parts[i];
    o<<"{\"type\":\""<<jsonEscape(p.type)<<"\",\"group\":\""<<jsonEscape(p.group)<<"\",\"x\":"<<p.x<<",\"z\":"<<p.z<<",\"w\":"<<p.w<<",\"d\":"<<p.d<<",\"h\":"<<p.h<<",\"color\":\""<<css(p.color)<<"\"}";
  }
  o<<"],\"warnings\":[";for(size_t i=0;i<l.warnings.size();i++){if(i)o<<',';o<<'"'<<jsonEscape(l.warnings[i])<<'"';}
  o<<"]}\n";
}
int main(int argc,char**argv){
  if(argc<2){cerr<<"Usage: midi_generator <spec.board> [output_dir] [seed] [variants]\n";return 1;}
  try{
    string output=argc>2?argv[2]:"output";int seed=argc>3?stoi(argv[3]):7,variants=argc>4?stoi(argv[4]):3;
    if(variants<1||variants>12)throw runtime_error("Number of variations must be 1..12");
    fs::create_directories(output);Spec spec=parse(argv[1]);
    for(int n=0;n<variants;n++){
      Layout l(spec,seed+101*n,n+1);l.tryBuild();Mesh m;m.build(l);
      string name=output+"/design_"+to_string(n+1);
      m.obj(name+".obj");svg(l,name+".svg");json(l,m,name+".json");
      cout<<"Generated "<<name<<" ("<<l.parts.size()<<" parts, "<<m.faceCount<<" triangles, "<<l.spec.width<<"x"<<l.spec.depth<<" mm)\n";
    }
    for(auto &a:spec.advisories)cerr<<"Note: "<<a<<"\n";
  }catch(const exception &e){cerr<<"Error: "<<e.what()<<"\n";return 2;}
}
