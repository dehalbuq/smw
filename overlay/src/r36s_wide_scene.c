#include "r36s_wide_scene.h"
#include "r36s_video.h"
#include "r36s_diag.h"
#include "common_rtl.h"
#include "snes/ppu.h"
#include "variables.h"
#include <stdio.h>
#include <string.h>

enum { kNativeWidth=256, kNativeHeight=224, kWideWidth=342 };

static uint16_t read_rom_word(unsigned bank, unsigned addr) {
  if (!g_rom || addr < 0x8000 || addr > 0xfffe || bank > 15) return 0;
  unsigned offset=(bank<<15)|(addr&0x7fff);
  return (uint16_t)(g_rom[offset] | ((uint16_t)g_rom[offset+1]<<8));
}
static unsigned tile_pixel(const uint16_t *vram, unsigned address, int x, int y, int bpp) {
  unsigned a=(address+(unsigned)y)&0x7fff;
  unsigned shift=7-(unsigned)x;
  unsigned v=vram[a]>>shift;
  unsigned pixel=(v&1)|((v>>7)&2);
  if(bpp==4) {
    v=vram[(a+8)&0x7fff]>>shift;
    pixel|=((v&1)<<2)|((v>>5)&8);
  }
  return pixel;
}
static unsigned map16_tile(int layer, int wx, int wy) {
  if(wx<0||wy<0||wy>=432||misc_level_mode_setting>=32) return 0xffff;
  int screen=wx>>8;
  if(screen >= misc_screens_in_lvl) return 0xffff;
  /* SMW's vanilla Map16 pointer table in bank 00 points to WRAM $7E/$7F.
     It is the same level layout used by the original tile streamer. */
  unsigned pointer=read_rom_word(0,0xbda8+32*layer+misc_level_mode_setting*2);
  unsigned lo=read_rom_word(0,pointer+screen*3);
  unsigned index=((unsigned)wy>>4)*16+(((unsigned)wx&255)>>4);
  if(lo<0xc800 || lo+index>0xffff) return 0xffff;
  unsigned addr=lo+index;
  unsigned block=g_ram[addr] | ((unsigned)g_ram[0x10000+addr]<<8);
  if(block>=512) return 0xffff;
  unsigned definition=g_ram[0x0fbe + block*2] | ((unsigned)g_ram[0x0fbf + block*2]<<8);
  /* Map16 definitions are eight bytes per 16x16 block in ROM bank $0D.
     Special animated / extended tiles may have other sources: fallback. */
  if(definition<0x8000||definition>0xfff6) return 0xffff;
  unsigned subtile=(wx&8?4:0)+(wy&8?2:0);
  unsigned word=read_rom_word(13,definition+subtile);
  return word;
}
typedef struct Pixel { unsigned palette_index, priority; } Pixel;
static Pixel bg_pixel(const Ppu *p, int layer, int sx, int sy, int force_map16,
                      int camera_x, int camera_y) {
  Pixel out={0,0};
  if(!(p->screenEnabled[0]&(1u<<layer))) return out;
  if(sy<0||sy>=224) return out;
  int w=PPU_bigTiles(p,layer)?16:8;
  unsigned scroll_x=p->hScroll[layer],scroll_y=p->vScroll[layer];
  int px=sx+(int)scroll_x,py=sy+(int)scroll_y;
  unsigned attr=0xffff, tx=px,ty=py;
  if(force_map16 && w==8) {
    int wx=camera_x+sx;
    int wy=camera_y+sy;
    attr=map16_tile(layer,wx,wy);
    tx=wx;ty=wy;
  } else {
    unsigned ux=(unsigned)px&1023,uy=(unsigned)py&1023;
    unsigned col=ux/(unsigned)w, row=uy/(unsigned)w;
    unsigned adr=((unsigned)p->bgXsc[layer]&0xfc)*256+(col&31)+((row&31)*32);
    if((p->bgXsc[layer]&1) && (col&32)) adr+=1024;
    if((p->bgXsc[layer]&2) && (row&32)) adr+=((p->bgXsc[layer]&1)?2048:1024);
    attr=p->vram[adr&0x7fff];
    tx=px;ty=py;
  }
  if(attr==0xffff) return out;
  unsigned cx=(unsigned)tx&((unsigned)w-1),cy=(unsigned)ty&((unsigned)w-1);
  if(attr&0x4000) cx=(unsigned)w-1-cx;
  if(attr&0x8000) cy=(unsigned)w-1-cy;
  unsigned tile=((attr&1023)+(cx>>3)+((cy>>3)<<4))&1023;
  unsigned base=((p->bgTileAdr>>(layer*4))&15)*4096;
  unsigned bpp=layer==2?2:4;
  unsigned value=tile_pixel(p->vram,base+tile*(bpp*4),cx&7,cy&7,bpp);
  if(value) {
    out.palette_index=(((attr>>10)&7)<<bpp)+value;
    out.priority=(layer==0?8:7)+((attr&0x2000)?4:0);
  }
  return out;
}
static uint32_t to_color(const Ppu *p, unsigned color) {
  unsigned r=color&31, g=(color>>5)&31, b=(color>>10)&31;
  unsigned bright=(p->inidisp&15);
  r=(((r<<3)|(r>>2))*bright)/15;
  g=(((g<<3)|(g>>2))*bright)/15;
  b=(((b<<3)|(b>>2))*bright)/15;
  return 0xff000000u | (r<<16) | (g<<8) | b;
}
static uint32_t background_pixel(const Ppu *p,int x,int y,
                                 int camera_x,int camera_y) {
  /* BG2 is rendered from tilemap/VRAM. BG1 needs world Map16 data beyond
     the 256-pixel streaming window (not present in the current PPU tilemap).
     Vanilla mode-1 priority layering is used for the first prototype. */
  Pixel bg2=bg_pixel(p,1,x,y,0,camera_x,camera_y);
  Pixel bg1=bg_pixel(p,0,x,y,1,camera_x,camera_y);
  Pixel top=bg1.priority>=bg2.priority?bg1:bg2;
  return to_color(p,p->cgram[top.palette_index&255]);
}
void R36SWideScene_Compose(uint8_t *dst,int pitch,int width,int height,
                           const uint8_t *native,int native_pitch) {
  if(!dst||!native||pitch<width*4||native_pitch<kNativeWidth*4||
     width<kNativeWidth||height<kNativeHeight) return;
  static unsigned long frame;
  int expand = r36s_viewport_16_9 && width==kWideWidth &&
      misc_game_mode==0x14 && (g_ppu->bgmode&7)==1 &&
      !(misc_level_layout_flags&1) && misc_screens_in_lvl>=2 && g_rom!=NULL;
  int camera_x=mirror_current_layer1_xpos;
  int camera_y=mirror_current_layer1_ypos;
  int left=(width-kNativeWidth)/2;
  if(expand) {
    /* No nonexistent negative-world pixels at the beginning of a level,
       or beyond its right edge. The stock 256px image always stays intact. */
    int world_width=misc_screens_in_lvl*256;
    if(camera_x<left) left=camera_x;
    if(world_width-camera_x-kNativeWidth < width-kNativeWidth-left)
      left=width-(world_width-camera_x);
    if(left<0)left=0;
    if(left>width-kNativeWidth)left=width-kNativeWidth;
  }
  for(int y=0;y<kNativeHeight;y++) {
    uint8_t *line=dst+(size_t)y*pitch;
    memset(line,0,(size_t)width*4);
    if(expand) {
      uint32_t *output=(uint32_t*)(void*)line;
      for(int x=0;x<left;x++)
        output[x]=background_pixel(g_ppu,x-left,y,camera_x,camera_y);
      for(int x=left+kNativeWidth;x<width;x++)
        output[x]=background_pixel(g_ppu,x-left,y,camera_x,camera_y);
    }
    memcpy(line+(size_t)left*4,native+(size_t)y*native_pitch,kNativeWidth*4);
  }
  if((++frame%180)==1) {
    char message[160];
    snprintf(message,sizeof(message),
       "viewport=%dx%d expand=%d native_left=%d mode=%u bgmode=%u camera=(%d,%d) screens=%u",
       width,height,expand,left,(unsigned)misc_game_mode,
       (unsigned)(g_ppu->bgmode&7),camera_x,camera_y,(unsigned)misc_screens_in_lvl);
    R36SDiag_Message("WIDE_SCENE",message);
  }
}
