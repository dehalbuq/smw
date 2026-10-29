#include "r36s_wide_scene.h"
#include "r36s_video.h"
#include "r36s_diag.h"
#include "common_rtl.h"
#include "snes/ppu.h"
#include "smw_rtl.h"
#include "src/funcs.h"
#include "variables.h"
#include <stdio.h>
#include <string.h>

enum { kOriginalW = 256, kOriginalH = 224, kExpandedW = 342 };

typedef struct WideLine {
  uint16_t h[3],v[3],tileBase;
  uint8_t bgMap[3], mode, enabled, brightness, valid;
} WideLine;
static WideLine scan[kOriginalH];
static unsigned bg1ok,bg2ok,bg3ok,bg1miss,scan_count;

void R36SWideScene_BeginFrame(void) {
  memset(scan,0,sizeof(scan));
  scan_count=0;
}
void R36SWideScene_CaptureLine(int y,const Ppu *p) {
  if(!p || y<0 || y>=kOriginalH)return;
  WideLine *s=&scan[y];
  for(int i=0;i<3;i++) {
    s->h[i]=p->hScroll[i];
    s->v[i]=p->vScroll[i];
    s->bgMap[i]=p->bgXsc[i];
  }
  s->tileBase=p->bgTileAdr;
  s->mode=p->bgmode;
  s->enabled=p->screenEnabled[0];
  s->brightness=p->inidisp;
  s->valid=1;
  scan_count++;
}
typedef struct BgPixel {
  unsigned index, priority;
} BgPixel;

/* Read SMW's ACTUAL level layout, as used by BufferScrollingTiles_Layer1.
 * Tables are pre-extracted game assets, NOT ROM addresses or PPU addresses.
 * At a world X, each 256px screen is stored as 16 columns x 27 Map16 rows. */
static int map16_attr(int wx,int wy) {
  if(wx<0 || wy<0 || wy>=432 || misc_level_mode_setting>=32) return -1;
  const uint16 *layout=GetLayerLayoutPtr(0,misc_level_mode_setting);
  if(!layout || g_lunar_magic)return -1;
  unsigned screen=(unsigned)wx>>8;
  if(screen>=misc_screens_in_lvl || screen>=32)return -1;
  unsigned addr=layout[screen];
  unsigned idx=((unsigned)wy>>4)*16+(((unsigned)wx&255)>>4);
  if(addr<0xc800 || (addr+idx)>0xffff)return -1;
  unsigned block=g_ram[addr+idx]|((unsigned)g_ram[0x10000+addr+idx]<<8);
  if(block>=0x8000)return -1;
  const uint16 *tiles=Lm_GetMap16RomAddr((uint16)block);
  if(!tiles)return -1;
  unsigned quadrant=((unsigned)(wy&8)>>2)|((unsigned)(wx&8)>>3);
  return tiles[quadrant];
}

/* SNES tilemap addressing and bitplanes exactly follow ppu_old.c.
 * For mode 1: BG1/BG2 = 4bpp, BG3 = 2bpp. Horizontal and vertical
 * high map bits are mutually arranged in 0x400-word blocks. */
static int tilemap_attr(const Ppu *p,const WideLine *s,int layer,int px,int py) {
  int size=(s->mode&(0x10<<layer))?16:8;
  int col=(px>> (size==16?4:3))&31;
  int row=(py>> (size==16?4:3))&31;
  unsigned adr=(unsigned)(s->bgMap[layer]&0xfc)<<8;
  adr+=(unsigned)(row*32+col);
  if((px&(size==16?0x200:0x100))&&(s->bgMap[layer]&1))adr+=0x400;
  if((py&(size==16?0x200:0x100))&&(s->bgMap[layer]&2))
    adr+=(s->bgMap[layer]&1)?0x800:0x400;
  return p->vram[adr&0x7fff];
}
static BgPixel get_bg(const Ppu *p,const WideLine *s,int layer,int view_x,int y,
                      int cam_x,int cam_y,int is_map16) {
  BgPixel out={0,0};
  if(!(s->enabled&(1<<layer)) || !(s->brightness&15))return out;
  int px=view_x+(int)s->h[layer];
  int py=y+(int)s->v[layer];
  int attr;
  if(is_map16) {
    px=cam_x+view_x;
    py=cam_y+y;
    attr=map16_attr(px,py);
    if(attr>=0)bg1ok++;else bg1miss++;
  } else attr=tilemap_attr(p,s,layer,px,py);
  if(attr<0)return out;

  int wide=(s->mode&(0x10<<layer))!=0;
  int xi=px&7, yi=py&7;
  if(attr&0x4000)xi=7-xi;
  if(attr&0x8000)yi=7-yi;

  unsigned tile=(unsigned)attr&0x3ff;
  if(wide) {
    if(((px&8)!=0)^((attr&0x4000)!=0))tile++;
    if(((py&8)!=0)^((attr&0x8000)!=0))tile+=0x10;
  }
  int bpp=layer==2?2:4;
  unsigned base=((unsigned)(s->tileBase>>(4*layer))&15)<<12;
  unsigned pos=(base+((tile&0x3ff)*(unsigned)(4*bpp))+(unsigned)yi)&0x7fff;
  unsigned shift=7-(unsigned)xi;
  uint16_t p01=p->vram[pos];
  unsigned color=(p01>>shift&1)|((p01>>(shift+8)&1)<<1);
  if(bpp==4) {
    uint16_t p23=p->vram[(pos+8)&0x7fff];
    color|=((p23>>shift&1)<<2)|((p23>>(shift+8)&1)<<3);
  }
  if(color) {
    out.index=(((unsigned)attr>>10)&7)*((unsigned)1<<bpp)+color;
    out.priority=(layer==0?8:layer==1?7:1)+((attr&0x2000)?(layer==2?2:4):0);
    if(layer==1)bg2ok++;
    if(layer==2)bg3ok++;
  }
  return out;
}
static uint32_t pack_rgb(const Ppu *p,const WideLine *s,unsigned index) {
  unsigned color=p->cgram[index&255];
  unsigned intensity=(unsigned)(s->brightness&15);
  unsigned red=(((color&31)<<3)|((color&31)>>2))*intensity/15;
  unsigned green=((((color>>5)&31)<<3)|(((color>>5)&31)>>2))*intensity/15;
  unsigned blue=((((color>>10)&31)<<3)|(((color>>10)&31)>>2))*intensity/15;
  return 0xff000000u|(red<<16)|(green<<8)|blue;
}
static uint32_t side_pixel(const Ppu *p,const WideLine *s,int view_x,int y,
                           int cam_x,int cam_y) {
  BgPixel top={0,0};
  BgPixel bg1=get_bg(p,s,0,view_x,y,cam_x,cam_y,1);
  BgPixel bg2=get_bg(p,s,1,view_x,y,cam_x,cam_y,0);
  BgPixel bg3=get_bg(p,s,2,view_x,y,cam_x,cam_y,0);
  /* Mode 1: priority BG1 hi/lo 12/8, BG2 11/7, BG3 3/1;
     special BG3 priority bit raises its high-priority tiles. */
  if((s->mode&8) && bg3.priority==3)bg3.priority=15;
  if(bg1.priority>top.priority)top=bg1;
  if(bg2.priority>top.priority)top=bg2;
  if(bg3.priority>top.priority)top=bg3;
  return pack_rgb(p,s,top.index);
}

void R36SWideScene_Compose(uint8_t *dst,int pitch,int width,int height,
                           const uint8_t *native,int native_pitch) {
  if(!dst||!native||width<kOriginalW||height<kOriginalH||
     pitch<width*4||native_pitch<kOriginalW*4)return;
  static unsigned frame;
  bg1ok=bg2ok=bg3ok=bg1miss=0;
  int supported=r36s_viewport_16_9 && width==kExpandedW &&
    misc_game_mode==0x14 && !(misc_level_layout_flags&1) &&
    misc_screens_in_lvl>=2 && g_ppu && scan_count==kOriginalH &&
    !g_lunar_magic && GetLayerLayoutPtr(0,misc_level_mode_setting)!=NULL;
  int cam_x=mirror_current_layer1_xpos,cam_y=mirror_current_layer1_ypos;
  int offset=(width-kOriginalW)/2;
  if(supported) {
    int world_width=(int)misc_screens_in_lvl*256;
    if(cam_x<offset)offset=cam_x;
    if(world_width-cam_x-kOriginalW < width-kOriginalW-offset)
      offset=width-(world_width-cam_x);
    if(offset<0)offset=0;
    if(offset>width-kOriginalW)offset=width-kOriginalW;
  }
  for(int y=0;y<kOriginalH;y++) {
    uint8_t *row=dst+(size_t)y*pitch;
    memset(row,0,(size_t)width*4);
    if(supported && (scan[y].mode&7)==1) {
      uint32_t *pix=(uint32_t*)(void*)row;
      for(int x=0;x<offset;x++)
        pix[x]=side_pixel(g_ppu,&scan[y],x-offset,y,cam_x,cam_y);
      for(int x=offset+kOriginalW;x<width;x++)
        pix[x]=side_pixel(g_ppu,&scan[y],x-offset,y,cam_x,cam_y);
    }
    memcpy(row+(size_t)offset*4,native+(size_t)y*native_pitch,kOriginalW*4);
  }
  if((++frame%180)==1) {
    char msg[256];
    snprintf(msg,sizeof(msg),
      "viewport=%dx%d expand=%d offset=%d game=%u levelmode=%u cam=(%d,%d) lines=%u Map16=%u missing=%u BG2=%u BG3=%u",
      width,height,supported,offset,(unsigned)misc_game_mode,
      (unsigned)misc_level_mode_setting,cam_x,cam_y,scan_count,
      bg1ok,bg1miss,bg2ok,bg3ok);
    R36SDiag_Message("WIDE_SCENE",msg);
  }
}
