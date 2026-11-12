/*
 * Real SDL2/GLES2 presenter smoke test (ROM-free).
 * Uses the production renderer file and lightweight host-state stubs.
 * It validates shader compilation, BGRA->RGBA swizzle, viewport scissor
 * and the non-widescreen aspect override on an AArch64 Mesa/Xvfb runner.
 * This is not a complete game integration test or EmuELEC ABI certification.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <SDL.h>
#include <GLES2/gl2.h>
#include "smw_renderer.h"
#include "util.h"
#include "config.h"

SmwVideoSettings g_smw_video = { .enabled = true };
SmwViewport g_smw_viewport = { 0 };
Config g_config = { false, false, NULL };
static int g_geometry_calls = 0;
static int g_swap_calls = 0;

void SmwDestination(SmwViewport view, int screen_w, int screen_h,
                    int *x, int *y, int *w, int *h) {
  (void)view;
  ++g_geometry_calls;
  /* Fixed 512-wide viewport with 64px border each side on a 640px screen.
     The production code computes these values using the game's actual logic. */
  *x = (screen_w - (screen_w * 4 / 5)) / 2;
  *y = 0;
  *w = screen_w * 4 / 5;
  *h = screen_h;
}

void smw_test_swap(SDL_Window *window) {
  /* Suppress the real swap so readback measures the just-drawn back buffer. */
  (void)window;
  ++g_swap_calls;
}

void OpenGLRenderer_Create(struct RendererFuncs *funcs);

static void fail(const char *message) {
  fprintf(stderr, "FAIL SMW_GLES2_SMOKE: %s (GL error 0x%x, SDL: %s)\n",
          message, (unsigned)glGetError(), SDL_GetError());
  exit(1);
}

static void check_color(int x, int y, bool red, const char *message) {
  unsigned char px[4] = {0, 0, 0, 0};
  glFinish();
  glReadPixels(x, y, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, px);
  if (glGetError() != GL_NO_ERROR) fail("glReadPixels");
  if (red) {
    if (!(px[0] >= 180 && px[1] <= 80 && px[2] <= 80 && px[3] >= 230)) {
      fprintf(stderr, "pixel (%d,%d): R=%u G=%u B=%u A=%u\n",
              x, y, px[0], px[1], px[2], px[3]);
      fail(message);
    }
  } else {
    if (!(px[0] <= 10 && px[1] <= 10 && px[2] <= 10)) {
      fprintf(stderr, "pixel (%d,%d): R=%u G=%u B=%u\n",
              x, y, px[0], px[1], px[2]);
      fail(message);
    }
  }
}

int main(void) {
  if (SDL_Init(SDL_INIT_VIDEO) != 0) fail("SDL_Init");
  struct RendererFuncs renderer = {0};
  OpenGLRenderer_Create(&renderer);
  if (!renderer.Initialize || !renderer.BeginDraw || !renderer.EndDraw ||
      !renderer.GetOutputSize || !renderer.Destroy) fail("vtable incomplete");

  SDL_Window *window = SDL_CreateWindow("SMW GLES2 smoke", SDL_WINDOWPOS_UNDEFINED,
                                       SDL_WINDOWPOS_UNDEFINED, 640, 360,
                                       SDL_WINDOW_OPENGL | SDL_WINDOW_SHOWN);
  if (!window) fail("SDL_CreateWindow");
  if (!renderer.Initialize(window)) fail("renderer.Initialize");

  const char *gl_ver = (const char *)glGetString(GL_VERSION);
  if (!gl_ver || !strstr(gl_ver, "OpenGL ES")) fail("not OpenGL ES context");
  fprintf(stdout, "GL context: %s\n", gl_ver);
  if (getenv("SMW_TEST_REQUIRE_ES2") && strncmp(gl_ver, "OpenGL ES 2.0", 13) != 0)
    fail("GLES2-only Mesa profile not enforced");
  int out_w = 0, out_h = 0;
  renderer.GetOutputSize(&out_w, &out_h);
  if (out_w != 640 || out_h != 360) fail("drawable dimensions mismatch");

  for (int test = 0; test < 3; ++test) {
    const int width = (test == 2) ? 800 : 256;
    const int height = 224;
    unsigned char *data = NULL;
    int pitch = 0;
    renderer.BeginDraw(width, height, &data, &pitch);
    if (!data || pitch != width * 4) fail("BeginDraw allocation/pitch");
    for (int i = 0; i < width * height; ++i) {
      /* BGRA byte order: red 220, green 30, blue 20. */
      data[i * 4 + 0] = 20;
      data[i * 4 + 1] = 30;
      data[i * 4 + 2] = 220;
      data[i * 4 + 3] = 255;
    }
    g_smw_video.enabled = test != 1;
    g_config.ignore_aspect_ratio = test == 1;
    renderer.EndDraw();
    check_color(320, 180, true, "GLES2 fragment BGRA swizzle");
    check_color(10, 180, test == 1, "widescreen viewport / aspect override");
    if (glGetError() != GL_NO_ERROR) fail("GL state after draw");
  }
  if (g_geometry_calls != 3) fail("SmwDestination not called");
  if (g_swap_calls != 3) fail("SwapWindow not requested");
  renderer.Destroy();
  SDL_DestroyWindow(window);
  SDL_Quit();
  puts("PASS SMW_GLES2_SMOKE: 3 frames, texture resizing, swizzle, viewport, SDL2/OpenGL ES2");
  return 0;
}
