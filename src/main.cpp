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
struct Group {string type,zone,color; int count=0,cols=0; double w=0,d=0,h=0,space=8;};
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
          if(normal)s.groups.push_back({"button",get(a,"zone","auto"),"cyan",normal,cols,21,16,4,7});
          if(clicky)s.groups.push_back({"clicky",get(a,"zone","auto"),"purple",clicky,0,20,18,8,7});
          continue;
        }
        if(type=="display"){
          string size=get(a,"size","medium");if(size=="small"){w=62;d=37;}else if(size=="large"){w=120;d=67;}
        }
        w=getDouble(a,"width",w);d=getDouble(a,"depth",d);space=getDouble(a,"spacing",space);
        positive(count,type);
        if(w<4||d<4||w>400||d>300||space<0||space>80)throw runtime_error("Component sizes or spacing out of range");
        if(count>0)s.groups.push_back({type,get(a,"zone",zone),get(a,"color",color),count,cols,w,d,h,space});
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
    if(!spec.keys)return;
    const int n=spec.keys;
    double side=(spec.pitch+spec.mod)?80:24;
    double x=side, z=spec.depth*.55;
    double w=spec.width-side-20,d=spec.depth*.39;
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
    int wheelCount=spec.pitch+spec.mod;
    if(wheelCount){
      double wz=z+min(15.,d*.08),wh=min(29.,(d-30.)/max(1,wheelCount));
      for(int i=0;i<wheelCount;i++){
        double zz=wz+i*(wh+10);Rect r{19,zz,35,wh};
        if(zz+wh>spec.depth-10)throw runtime_error("Wheel area too small");
        used.push_back(r);add("wheel","wheels",i<spec.pitch?"cyan":"purple",19,zz,35,wh,12);
      }
    }
  }
  pair<double,double> preferred(string zone,double gw,double gd) const {
    string z=lower(zone);double x=(spec.width-gw)/2.,y=17;
    if(z.find("left")!=string::npos)x=17;
    if(z.find("right")!=string::npos)x=spec.width-gw-17;
    if(z.find("bottom")!=string::npos)y=spec.depth-gd-17;
    if(z.find("center")!=string::npos)y=(spec.keys?spec.depth*.50:spec.depth-gd)/2.;
    if(z=="auto")x=18;
    // Deliberate design alternatives, not just sub-millimeter jitter.
    // These shifts are preferences, never hard constraints: collision checks still win.
    if(id%3==2)y+=max(20.,gd*.26);
    if(id%3==0){
      if(z.find("right")!=string::npos)x-=42;
      else if(z.find("left")!=string::npos||z=="auto")x+=42;
      else y+=26;
    }
    return {x,y};
  }
  void addGroup(const Group &g){
    if(g.count<=0)return;
    vector<int> colOptions;
    if(g.cols)colOptions={g.cols};
    else {
      int guess=g.type=="fader"?min(6,g.count):g.type=="display"?1:g.type=="footswitch"?min(4,g.count):min(6,g.count);
      // Different valid packings, while keeping controls together as a group.
      colOptions={guess};if(g.count>1)colOptions.push_back(max(1,guess-1));
      if(g.count>2)colOptions.push_back(min(g.count,guess+1));
      shuffle(colOptions.begin(),colOptions.end(),rng);
    }
    double topLimit=spec.keys?spec.depth*.53:spec.depth-margin;
    struct Candidate {double score,x,z;int cols;};vector<Candidate> candidates;
    for(int cols:colOptions){
      int rows=(g.count+cols-1)/cols;
      double gw=cols*g.w+(cols-1)*g.space,gd=rows*g.d+(rows-1)*g.space;
      if(gw>spec.width-2*margin||gd>topLimit-2*margin)continue;
      auto [px,pz]=preferred(g.zone,gw,gd);
      uniform_real_distribution<double> fuzz(0,7);
      for(double zz=margin;zz+gd<=topLimit-margin+1e-6;zz+=6){
        for(double xx=margin;xx+gw<=spec.width-margin+1e-6;xx+=6){
          Rect r{xx,zz,gw,gd};bool clear=true;
          for(auto q:used)if(overlaps(r,q,4)){clear=false;break;}
          if(!clear)continue;
          double score=hypot((xx-px)/2.0,(zz-pz)*1.5)+fuzz(rng);
          if(g.cols==0)score+=abs(cols-min(g.count,6))*1.2;
          candidates.push_back({score,xx,zz,cols});
        }
      }
    }
    if(candidates.empty())throw runtime_error("Not enough usable room to place "+to_string(g.count)+" "+g.type+"(s). Try a bigger body or fewer controls.");
    auto best=min_element(candidates.begin(),candidates.end(),[](const Candidate&a,const Candidate&b){return a.score<b.score;});
    int rows=(g.count+best->cols-1)/best->cols;
    double gw=best->cols*g.w+(best->cols-1)*g.space,gd=rows*g.d+(rows-1)*g.space;
    used.push_back({best->x,best->z,gw,gd});
    for(int i=0;i<g.count;i++){
      double x=best->x+(i%best->cols)*(g.w+g.space),z=best->z+(i/best->cols)*(g.d+g.space);
      add(g.type,g.type,g.color,x,z,g.w,g.d,g.h);
    }
    if(g.zone!="auto"){
      auto [px,pz]=preferred(g.zone,gw,gd);
      if(hypot(best->x-px,best->z-pz)>80)warnings.push_back(g.type+" group moved away from requested '"+g.zone+"' zone to avoid overlaps.");
    }
  }
  void build(){
    add("body","chassis",spec.color,0,0,spec.width,spec.depth,17);
    addKeys();
    // Prioritize large groups first. Layout is generated by the same rules, regardless of demo "complexity".
    vector<Group> gs=spec.groups;
    stable_sort(gs.begin(),gs.end(),[](const Group&a,const Group&b){
      auto area=[](const Group &v){int c=v.cols?v.cols:min(v.count,(v.type=="display"?1:6));return (c*v.w+(c-1)*v.space)*(((v.count+c-1)/c)*v.d+(((v.count+c-1)/c)-1)*v.space);};
      return area(a)>area(b);
    });
    for(const Group&g:gs)addGroup(g);
  }
  bool tryBuild(){
    for(int attempt=0;attempt<14;attempt++){
      parts.clear();used.clear();warnings.clear();
      try{build();if(attempt>0)warnings.push_back("Automatically enlarged enclosure to fit all controls.");return true;}
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
  void tri(Vec3 a,Vec3 b,Vec3 c,Vec3 rgb){
    Vec3 u{b.x-a.x,b.y-a.y,b.z-a.z},v{c.x-a.x,c.y-a.y,c.z-a.z};
    Vec3 n{u.y*v.z-u.z*v.y,u.z*v.x-u.x*v.z,u.x*v.y-u.y*v.x};
    double l=sqrt(n.x*n.x+n.y*n.y+n.z*n.z);if(l>1e-9){n.x/=l;n.y/=l;n.z/=l;}
    for(auto p:{a,b,c}) vertices.push_back({p,n,rgb});
    faceCount++;
  }
  void quad(Vec3 a,Vec3 b,Vec3 c,Vec3 d,Vec3 rgb){tri(a,b,c,rgb);tri(a,c,d,rgb);}
  void cube(double x,double y,double z,double w,double h,double d,Vec3 c){
    Vec3 a{x,y,z},b{x+w,y,z},cc{x+w,y,z+d},dd{x,y,z+d},A{x,y+h,z},B{x+w,y+h,z},C{x+w,y+h,z+d},D{x,y+h,z+d};
    quad(A,B,C,D,c);quad(dd,cc,b,a,c);quad(a,b,B,A,c);quad(b,cc,C,B,c);quad(cc,dd,D,C,c);quad(dd,a,A,D,c);
  }
  void cylinder(double x,double y,double z,double rad,double h,Vec3 col,int seg=20){
    for(int i=0;i<seg;i++){
      double p=2*PI*i/seg,q=2*PI*(i+1)/seg;
      Vec3 a{x+cos(p)*rad,y,z+sin(p)*rad},b{x+cos(q)*rad,y,z+sin(q)*rad};
      Vec3 A{a.x,y+h,a.z},B{b.x,y+h,b.z};
      quad(a,b,B,A,col);tri({x,y+h,z},A,B,col);
    }
  }
  void build(const Layout &l){
    angle=l.spec.tilt*PI/180.;
    for(const Part&p:l.parts){auto c=color(p.color);double y=p.type=="body"?0:17;
      if(p.type=="knob"||p.type=="led"||p.type=="footswitch"||p.type=="joystick")cylinder(p.x+p.w/2,y,p.z+p.d/2,min(p.w,p.d)*.42,p.h,c);
      else if(p.type=="fader"){
        cube(p.x+p.w*.39,y,p.z,p.w*.22,1,p.d,color("dark"));
        cube(p.x-2,y+2,p.z+p.d*.42,p.w+4,4,p.d*.14,c);
      }else if(p.type=="switch"){
        cube(p.x+3,y,p.z+2,p.w-6,2,p.d-4,color("steel"));cylinder(p.x+p.w/2,y+2,p.z+p.d/2,2,p.h,c);
      }else if(p.type=="wheel"){
        cube(p.x,y,p.z,p.w,p.h,p.d,color("black"));cube(p.x+5,y+4,p.z+2,p.w-10,p.h*.55,p.d-4,c);
      }else if(p.type=="body")cube(p.x,0,p.z,p.w,p.h,p.d,c);
      else cube(p.x,y,p.z,p.w,p.h,p.d,c);
    }
  }
  void obj(const string&path)const{
    ofstream o(path);if(!o)throw runtime_error("Cannot write OBJ: "+path);
    o<<"# C++ procedural MIDI generator; units=mm; vertex colors embedded\n";
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
  f<<"<rect x=\"-18\" y=\"-18\" width=\""<<w+36<<"\" height=\""<<d+36<<"\" fill=\"#0b1022\"/>\n";
  for(const Part&p:l.parts){string c=css(p.color);
    if(p.type=="knob"||p.type=="led"||p.type=="footswitch"||p.type=="joystick")f<<"<circle cx=\""<<p.x+p.w/2<<"\" cy=\""<<p.z+p.d/2<<"\" r=\""<<min(p.w,p.d)*.42<<"\" fill=\""<<c<<"\" stroke=\"#8394b7\" stroke-width=\"1\"/>\n";
    else if(p.type=="fader"){
      f<<"<rect x=\""<<p.x+p.w*.39<<"\" y=\""<<p.z<<"\" width=\""<<p.w*.22<<"\" height=\""<<p.d<<"\" fill=\"#3d4c6b\"/>\n";
      f<<"<rect x=\""<<p.x-2<<"\" y=\""<<p.z+p.d*.42<<"\" width=\""<<p.w+4<<"\" height=\"8\" rx=\"2\" fill=\""<<c<<"\"/>\n";
    }else f<<"<rect x=\""<<p.x<<"\" y=\""<<p.z<<"\" width=\""<<p.w<<"\" height=\""<<p.d<<"\" rx=\""<<(p.type=="body"?14:2)<<"\" fill=\""<<c<<"\" stroke=\"#7487aa\" stroke-width=\"0.75\"/>\n";
  }
  f<<"</svg>\n";
}
void json(const Layout &l,const Mesh &mesh,const string &path){
  ofstream o(path);if(!o)throw runtime_error("Cannot write JSON: "+path);
  o<<fixed<<setprecision(3);
  o<<"{\"kind\":\""<<jsonEscape(l.spec.kind)<<"\",\"width\":"<<l.spec.width<<",\"depth\":"<<l.spec.depth<<",\"tilt\":"<<l.spec.tilt;
  o<<",\"material\":\""<<jsonEscape(l.spec.material)<<"\",\"bodyColor\":\""<<jsonEscape(l.spec.color)<<"\",\"variant\":"<<l.id;
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
