#define STBI_ONLY_PNG
#define STBI_NO_HDR
#define STBI_NO_LINEAR
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#include "r36s_backdrop.h"
#include <stdio.h>
#include <string.h>
#include <strings.h>

int r36s_use_backdrop = 1;
char r36s_background_image[256] = "background.png";
static unsigned char *s_pixels;

bool R36SBackdrop_ParseUse(const char *s) {
  if (!s) return false;
  if (!strcasecmp(s,"true") || !strcasecmp(s,"yes") || !strcasecmp(s,"on") || !strcmp(s,"1")) {
    r36s_use_backdrop=1;return true;
  }
  if (!strcasecmp(s,"false") || !strcasecmp(s,"no") || !strcasecmp(s,"off") || !strcmp(s,"0")) {
    r36s_use_backdrop=0;return true;
  }
  return false;
}
bool R36SBackdrop_ParseImage(const char *s) {
  if (!s || !*s || strlen(s) >= sizeof(r36s_background_image)) return false;
  strncpy(r36s_background_image,s,sizeof(r36s_background_image)-1);
  r36s_background_image[sizeof(r36s_background_image)-1]=0;
  return true;
}
const unsigned char *R36SBackdrop_LoadRGBA(int *width,int *height) {
  if (width) *width=0;
  if (height) *height=0;
  R36SBackdrop_FreePixels();
  if (!r36s_use_backdrop) {
    fprintf(stderr,"[BACKDROP] disabled in smw.ini\n");
    return NULL;
  }
  int w=0,h=0,components=0;
  if (!stbi_info(r36s_background_image,&w,&h,&components)) {
    fprintf(stderr,"[BACKDROP] no readable PNG: %s (%s), using black borders\n",
            r36s_background_image,stbi_failure_reason());
    return NULL;
  }
  /* Avoid allocating unbounded memory from malformed PNGs on the R36S. */
  if (w<16 || h<16 || w>2048 || h>2048 || (long long)w*h>2400000LL) {
    fprintf(stderr,"[BACKDROP] image dimensions rejected: %dx%d\n",w,h);
    return NULL;
  }
  s_pixels=stbi_load(r36s_background_image,&w,&h,&components,4);
  if (!s_pixels) {
    fprintf(stderr,"[BACKDROP] PNG decoding failed (%s), keeping black borders\n",
            stbi_failure_reason());
    return NULL;
  }
  if(width)*width=w;
  if(height)*height=h;
  fprintf(stderr,"[BACKDROP] image loaded=%s size=%dx%d fit=stretch pixelperfect=preserved\n",
          r36s_background_image,w,h);
  return s_pixels;
}
void R36SBackdrop_FreePixels(void) {
  if(s_pixels){stbi_image_free(s_pixels);s_pixels=NULL;}
}
