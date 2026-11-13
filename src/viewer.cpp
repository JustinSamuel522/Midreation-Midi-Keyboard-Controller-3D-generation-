// Optional interactive OpenGL 3.3 viewer for generated OBJ files.
// macOS: brew install cmake glfw glew; cmake -S . -B build -DBUILD_VIEWER=ON
#include <GL/glew.h>
#include <GLFW/glfw3.h>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace std;
struct Vec {float x,y,z;};
struct Mat {float a[16];};
Mat identity(){Mat m{};for(int i=0;i<4;i++)m.a[i*4+i]=1;return m;}
Mat mul(const Mat& x,const Mat& y){Mat z{};for(int c=0;c<4;c++)for(int r=0;r<4;r++)for(int k=0;k<4;k++)z.a[c*4+r]+=x.a[k*4+r]*y.a[c*4+k];return z;}
Mat perspective(float fovy,float aspect,float n,float f){Mat m{};float t=1/tanf(fovy*.5f);m.a[0]=t/aspect;m.a[5]=t;m.a[10]=-(f+n)/(f-n);m.a[11]=-1;m.a[14]=-2*f*n/(f-n);return m;}
Mat translate(float x,float y,float z){Mat m=identity();m.a[12]=x;m.a[13]=y;m.a[14]=z;return m;}
Mat rotateX(float a){Mat m=identity();m.a[5]=cosf(a);m.a[9]=-sinf(a);m.a[6]=sinf(a);m.a[10]=cosf(a);return m;}
Mat rotateY(float a){Mat m=identity();m.a[0]=cosf(a);m.a[8]=sinf(a);m.a[2]=-sinf(a);m.a[10]=cosf(a);return m;}
GLuint shader(GLenum type,const char*src){GLuint id=glCreateShader(type);glShaderSource(id,1,&src,nullptr);glCompileShader(id);GLint ok=0;glGetShaderiv(id,GL_COMPILE_STATUS,&ok);if(!ok){char log[4096];glGetShaderInfoLog(id,sizeof(log),nullptr,log);throw runtime_error(log);}return id;}
GLuint program(){
 const char *vert=R"(#version 330 core
layout(location=0) in vec3 pos;
layout(location=1) in vec3 col;
uniform mat4 uMVP;
out vec3 vColor;
void main(){vColor=col;gl_Position=uMVP*vec4(pos,1.0);})";
 const char *frag=R"(#version 330 core
in vec3 vColor;
out vec4 color;
void main(){color=vec4(vColor,1.0);})";
 GLuint a=shader(GL_VERTEX_SHADER,vert),b=shader(GL_FRAGMENT_SHADER,frag),p=glCreateProgram();
 glAttachShader(p,a);glAttachShader(p,b);glLinkProgram(p);glDeleteShader(a);glDeleteShader(b);
 GLint ok;glGetProgramiv(p,GL_LINK_STATUS,&ok);if(!ok)throw runtime_error("OpenGL shader link failure");return p;
}
struct Mesh{vector<float> data;float cx=0,cy=0,cz=0,scale=1;};
Mesh load(const string&path){
 ifstream f(path);if(!f)throw runtime_error("Cannot open OBJ: "+path);
 vector<Vec> pos,col;vector<unsigned> indices;string line;
 while(getline(f,line)){
  istringstream ss(line);string tag;ss>>tag;
  if(tag=="v") {Vec a{},c{};if(ss>>a.x>>a.y>>a.z>>c.x>>c.y>>c.z){pos.push_back(a);col.push_back(c);}}
  else if(tag=="f"){string v;while(ss>>v){auto slash=v.find('/');int ix=stoi(v.substr(0,slash));indices.push_back(unsigned(ix-1));}}
 }
 if(pos.empty()||indices.size()%3)throw runtime_error("Invalid or empty generated OBJ");
 Mesh m;float mnx=1e9f,mny=1e9f,mnz=1e9f,mxx=-1e9f,mxy=-1e9f,mxz=-1e9f;
 for(auto&p:pos){mnx=min(mnx,p.x);mny=min(mny,p.y);mnz=min(mnz,p.z);mxx=max(mxx,p.x);mxy=max(mxy,p.y);mxz=max(mxz,p.z);}
 m.cx=(mnx+mxx)*.5f;m.cy=(mny+mxy)*.5f;m.cz=(mnz+mxz)*.5f;m.scale=max({mxx-mnx,mxy-mny,mxz-mnz});
 for(auto ix:indices){if(ix>=pos.size())throw runtime_error("OBJ index out of bounds"); auto p=pos[ix],c=col[ix];m.data.insert(m.data.end(),{p.x,p.y,p.z,c.x,c.y,c.z});}
 return m;
}
int main(int argc,char**argv){
 if(argc<2){cerr<<"Usage: midi_viewer <generated.obj>\n";return 1;}
 try{
 Mesh mesh=load(argv[1]);if(!glfwInit())throw runtime_error("Unable to initialize GLFW");
 glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,3);
 glfwWindowHint(GLFW_OPENGL_PROFILE,GLFW_OPENGL_CORE_PROFILE);
 #ifdef __APPLE__
 glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT,GL_TRUE);
 #endif
 GLFWwindow *w=glfwCreateWindow(1200,750,"Procedural MIDI - 3D Viewer",nullptr,nullptr);
 if(!w){glfwTerminate();throw runtime_error("Could not create OpenGL 3.3 window");}
 glfwMakeContextCurrent(w);glewExperimental=GL_TRUE;
 if(glewInit()!=GLEW_OK)throw runtime_error("Failed to initialize GLEW");glGetError();
 GLuint prog=program(),vao,vbo;glGenVertexArrays(1,&vao);glGenBuffers(1,&vbo);
 glBindVertexArray(vao);glBindBuffer(GL_ARRAY_BUFFER,vbo);
 glBufferData(GL_ARRAY_BUFFER,mesh.data.size()*sizeof(float),mesh.data.data(),GL_STATIC_DRAW);
 glVertexAttribPointer(0,3,GL_FLOAT,GL_FALSE,6*sizeof(float),(void*)0);glEnableVertexAttribArray(0);
 glVertexAttribPointer(1,3,GL_FLOAT,GL_FALSE,6*sizeof(float),(void*)(3*sizeof(float)));glEnableVertexAttribArray(1);
 glEnable(GL_DEPTH_TEST);glfwSwapInterval(1);float yaw=-.24f,pitch=.75f,zoom=1.75f;
 cout<<"Controls: A/D rotate, W/S tilt, +/- zoom, R reset, ESC quit.\n";
 while(!glfwWindowShouldClose(w)){
  glfwPollEvents();if(glfwGetKey(w,GLFW_KEY_ESCAPE)==GLFW_PRESS)glfwSetWindowShouldClose(w,true);
  if(glfwGetKey(w,GLFW_KEY_A)==GLFW_PRESS)yaw-=.023f;
  if(glfwGetKey(w,GLFW_KEY_D)==GLFW_PRESS)yaw+=.023f;
  if(glfwGetKey(w,GLFW_KEY_W)==GLFW_PRESS)pitch=min(1.55f,pitch+.018f);
  if(glfwGetKey(w,GLFW_KEY_S)==GLFW_PRESS)pitch=max(.06f,pitch-.018f);
  if(glfwGetKey(w,GLFW_KEY_EQUAL)==GLFW_PRESS)zoom=max(.8f,zoom-.025f);
  if(glfwGetKey(w,GLFW_KEY_MINUS)==GLFW_PRESS)zoom=min(5.f,zoom+.025f);
  if(glfwGetKey(w,GLFW_KEY_R)==GLFW_PRESS){yaw=-.24f;pitch=.75f;zoom=1.75f;}
  int width,height;glfwGetFramebufferSize(w,&width,&height);if(height<1)height=1;
  glViewport(0,0,width,height);glClearColor(.039f,.052f,.10f,1);glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT);
  // Normalize to roughly unit scale, center on the model, orbit camera.
  Mat center=translate(-mesh.cx,-mesh.cy,-mesh.cz);
  Mat model=mul(rotateX(pitch),mul(rotateY(yaw),center));
  Mat view=translate(0,0,-mesh.scale*zoom);
  Mat proj=perspective(.85f,float(width)/height,.01f*mesh.scale,20*mesh.scale);
  Mat mvp=mul(proj,mul(view,model));
  glUseProgram(prog);glUniformMatrix4fv(glGetUniformLocation(prog,"uMVP"),1,GL_FALSE,mvp.a);
  glBindVertexArray(vao);glDrawArrays(GL_TRIANGLES,0,GLsizei(mesh.data.size()/6));glfwSwapBuffers(w);
 }
 glDeleteBuffers(1,&vbo);glDeleteVertexArrays(1,&vao);glDeleteProgram(prog);glfwDestroyWindow(w);glfwTerminate();
 }catch(const exception&e){cerr<<"Error: "<<e.what()<<"\n";return 2;}
}
