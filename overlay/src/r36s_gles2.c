#ifdef R36S_GLES2_SUPPORT
#include <SDL.h>
#include <GLES2/gl2.h>
#include "r36s_gles2.h"
#include "r36s_fast_video.h"
#include "config.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

static SDL_Window *s_window;
static SDL_GLContext s_context;
static GLuint s_program,s_vbo,s_texture;
static GLint s_uniform;
static unsigned char *s_argb,*s_rgba;
static size_t s_capacity;
static int s_width,s_height,s_texture_w,s_texture_h;

static GLuint compile_shader(GLenum kind,const char *source) {
  GLuint shader=glCreateShader(kind);
  if (!shader) return 0;
  glShaderSource(shader,1,&source,NULL);
  glCompileShader(shader);
  GLint ok=0;glGetShaderiv(shader,GL_COMPILE_STATUS,&ok);
  if (!ok) {
    char info[512]={0};glGetShaderInfoLog(shader,sizeof(info),NULL,info);
    fprintf(stderr,"[GLES2] shader compile failed: %s\n",info);
    glDeleteShader(shader);return 0;
  }
  return shader;
}
static bool initialize(SDL_Window *window) {
  s_window=window;
  s_context=SDL_GL_CreateContext(window);
  if (!s_context) {
    fprintf(stderr,"[GLES2] SDL_GL_CreateContext: %s\n", SDL_GetError());
    return false;
  }
  int swap_status=SDL_GL_SetSwapInterval(r36s_vsync ? 1 : 0);
  fprintf(stderr,"[GLES2] requested_vsync=%d swap_interval_result=%d error=%s\n",
          r36s_vsync,swap_status,swap_status==0 ? "none" : SDL_GetError());
  const char *vert=
    "attribute vec2 a_position;\n"
    "attribute vec2 a_uv;\n"
    "varying vec2 v_uv;\n"
    "void main(){ gl_Position=vec4(a_position,0.0,1.0); v_uv=a_uv; }\n";
  const char *frag=
    "precision mediump float;\n"
    "varying vec2 v_uv;\n"
    "uniform sampler2D u_texture;\n"
    "void main(){ gl_FragColor=texture2D(u_texture,v_uv); }\n";
  GLuint vs=compile_shader(GL_VERTEX_SHADER,vert);
  GLuint fs=compile_shader(GL_FRAGMENT_SHADER,frag);
  if (!vs || !fs) { if(vs)glDeleteShader(vs); if(fs)glDeleteShader(fs);return false; }
  s_program=glCreateProgram();
  glAttachShader(s_program,vs);glAttachShader(s_program,fs);
  glBindAttribLocation(s_program,0,"a_position");
  glBindAttribLocation(s_program,1,"a_uv");
  glLinkProgram(s_program);
  glDeleteShader(vs);glDeleteShader(fs);
  GLint linked=0;glGetProgramiv(s_program,GL_LINK_STATUS,&linked);
  if (!linked) {
    char info[512]={0};glGetProgramInfoLog(s_program,sizeof(info),NULL,info);
    fprintf(stderr,"[GLES2] program link failed: %s\n",info);
    return false;
  }
  s_uniform=glGetUniformLocation(s_program,"u_texture");
  glGenTextures(1,&s_texture);
  glBindTexture(GL_TEXTURE_2D,s_texture);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  /* ES2 has no desktop VAO requirement or #version 330 shaders. */
  static const GLfloat quad[]={
    -1.f,-1.f,0.f,1.f, 1.f,-1.f,1.f,1.f,
    -1.f, 1.f,0.f,0.f, 1.f, 1.f,1.f,0.f,
  };
  glGenBuffers(1,&s_vbo);
  glBindBuffer(GL_ARRAY_BUFFER,s_vbo);
  glBufferData(GL_ARRAY_BUFFER,sizeof(quad),quad,GL_STATIC_DRAW);
  fprintf(stderr,"[GLES2] renderer initialized: %s\n",glGetString(GL_VERSION));
  return true;
}
static void destroy(void) {
  if(s_texture) glDeleteTextures(1,&s_texture);
  if(s_vbo) glDeleteBuffers(1,&s_vbo);
  if(s_program) glDeleteProgram(s_program);
  if(s_context) SDL_GL_DeleteContext(s_context);
  free(s_argb);free(s_rgba);
  s_context=NULL;s_argb=s_rgba=NULL;s_capacity=0;s_texture=s_program=s_vbo=0;
}
static void begin_draw(int w,int h,uint8 **pixels,int *pitch) {
  s_width=w;s_height=h;
  size_t need=(size_t)w*h*4;
  if(w<=0 || h<=0 || w>4096 || h>4096 || need>64*1024*1024) {
    fprintf(stderr,"[GLES2] invalid frame size: %dx%d\n",w,h);
    *pixels=NULL;*pitch=0;return;
  }
  if(need>s_capacity) {
    unsigned char *new_argb=(unsigned char*)malloc(need);
    unsigned char *new_rgba=(unsigned char*)malloc(need);
    if(!new_argb||!new_rgba){free(new_argb);free(new_rgba);fprintf(stderr,"[GLES2] out of memory\n");*pixels=NULL;*pitch=0;return;}
    free(s_argb);free(s_rgba);
    s_argb=new_argb;s_rgba=new_rgba;s_capacity=need;
  }
  *pixels=s_argb;*pitch=w*4;
}
static void end_draw(void) {
  if(!s_argb||!s_rgba||s_width<=0||s_height<=0)return;
  /* SDL PIXELFORMAT_ARGB8888 is B,G,R,A in little-endian memory. ES2 must
     accept GL_RGBA; convert explicitly, not via desktop-only GL_BGRA. */
  for(int i=0,n=s_width*s_height;i<n;i++) {
    s_rgba[4*i+0]=s_argb[4*i+2];
    s_rgba[4*i+1]=s_argb[4*i+1];
    s_rgba[4*i+2]=s_argb[4*i+0];
    s_rgba[4*i+3]=255;
  }
  glBindTexture(GL_TEXTURE_2D,s_texture);
  if(s_texture_w!=s_width || s_texture_h!=s_height) {
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,s_width,s_height,0,GL_RGBA,GL_UNSIGNED_BYTE,s_rgba);
    s_texture_w=s_width;s_texture_h=s_height;
  } else glTexSubImage2D(GL_TEXTURE_2D,0,0,0,s_width,s_height,GL_RGBA,GL_UNSIGNED_BYTE,s_rgba);
  int out_w=0,out_h=0;
  SDL_GL_GetDrawableSize(s_window,&out_w,&out_h);
  R36SRect dst;R36SFast_ContentRect(out_w,out_h,s_width,s_height,&dst);
  glViewport(0,0,out_w,out_h);
  glClearColor(0,0,0,1);glClear(GL_COLOR_BUFFER_BIT);
  glViewport(dst.x,out_h-(dst.y+dst.h),dst.w,dst.h);
  glUseProgram(s_program);
  glActiveTexture(GL_TEXTURE0);glBindTexture(GL_TEXTURE_2D,s_texture);
  glUniform1i(s_uniform,0);
  glBindBuffer(GL_ARRAY_BUFFER,s_vbo);
  glEnableVertexAttribArray(0);glEnableVertexAttribArray(1);
  glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,4*sizeof(GLfloat),(void*)0);
  glVertexAttribPointer(1,2,GL_FLOAT,GL_FALSE,4*sizeof(GLfloat),(void*)(2*sizeof(GLfloat)));
  glDrawArrays(GL_TRIANGLE_STRIP,0,4);
  glDisableVertexAttribArray(0);glDisableVertexAttribArray(1);
  SDL_GL_SwapWindow(s_window);
}
void R36SGLES2Renderer_Create(struct RendererFuncs *funcs) {
  funcs->Initialize=initialize;funcs->Destroy=destroy;
  funcs->BeginDraw=begin_draw;funcs->EndDraw=end_draw;
}
#endif
