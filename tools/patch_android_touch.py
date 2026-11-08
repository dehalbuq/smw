#!/usr/bin/env python3
"""Add real multitouch + portrait geometry + double-BACK confirmation to SMW v8."""
from pathlib import Path

def replace_once(text, old, new):
    n=text.count(old)
    if n != 1:
        raise RuntimeError(f"touch adaptation expected one anchor, got {n}: {old[:110]!r}")
    return text.replace(old, new, 1)

def apply(project, fork):
    project=Path(project)
    fork=Path(fork)
    native=project/"app/jni/SMW_SRC/src/main.c"
    s=native.read_text(encoding="utf-8")

    s=replace_once(s, '#include "android_quit_menu.h"',
                   '#include "android_quit_menu.h"\n#include <jni.h>')
    s=replace_once(s, "static GamepadInfo g_gamepad[2];",
'''static GamepadInfo g_gamepad[2];

/* Java touch events arrive on the UI thread, gameplay runs in SDL_main. */
static uint32 g_smw_touch_input;

JNIEXPORT void JNICALL
Java_net_freyta_smw_MainActivity_nativeTouchButtons(JNIEnv *env, jclass clazz, jint mask) {
  (void)env;
  (void)clazz;
  __atomic_store_n(&g_smw_touch_input, (uint32)mask & 0xFFFu, __ATOMIC_RELAXED);
}
''')
    # Android's SDLActivity can reuse libmain.so across sessions.
    # Reset only touch state, NEVER the saved .srm.
    s=s.replace("  g_input_state = 0;",
'''  g_input_state = 0;
  __atomic_store_n(&g_smw_touch_input, 0u, __ATOMIC_RELAXED);''')
    if s.count("__atomic_store_n(&g_smw_touch_input, 0u") != 2:
        raise RuntimeError("Expected touch reset at main entry and graceful shutdown")

    # Keep the integer-pixel SNES image centered, but reserve the bottom 38%
    # for controls in portrait. SDL native window resize handles rotation.
    s=replace_once(s,'''  SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);
  SDL_RenderSetIntegerScale(renderer, SDL_TRUE);
  SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);''',
'''  // Render destination is computed each frame from actual window pixels.
  // This preserves integer 256x224 pixels without distorting portrait mode.
  SDL_RenderSetLogicalSize(renderer, 0, 0);
  SDL_RenderSetDrawColor(renderer, 0, 0, 0, 255);'''.replace("SDL_RenderSetDrawColor", "SDL_SetRenderDrawColor"))
    s=replace_once(s, "  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);",
'''  int out_w = 0, out_h = 0;
  SDL_GetRendererOutputSize(g_renderer, &out_w, &out_h);
  bool portrait = out_h > out_w;
  int available_h = portrait ? out_h * 62 / 100 : out_h;
  int scale = IntMin(out_w / g_snes_width, available_h / g_snes_height);
  if (scale < 1) scale = 1;
  SDL_Rect game_rect = {
      (out_w - g_snes_width * scale) / 2,
      (available_h - g_snes_height * scale) / 2,
      g_snes_width * scale, g_snes_height * scale };
  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, &game_rect);''')

    # All exit menu inputs are sampled exactly once per frame. Combine touch
    # and Bluetooth/USB without replacing the existing controller mapping.
    # Hardware input is still polled independently on the Mediatek projector.
    anchor="static void Smw_PollPads(void) {"
    s=replace_once(s,anchor,
'''static bool s_smw_menu_polled;
static void Smw_PollExitMenu(bool select, bool start, bool accept, bool cancel) {
  uint32 touch = __atomic_load_n(&g_smw_touch_input, __ATOMIC_RELAXED);
  s_smw_menu_polled = true;
  AndroidQuitMenu_Poll(select || (touch & (1u << 2)) != 0,
                       start || (touch & (1u << 3)) != 0,
                       accept || (touch & (1u << 0)) != 0,
                       cancel || (touch & (1u << 8)) != 0);
}
static void Smw_PollPads(void) {''')
    s=replace_once(s,'''  SDL_GameControllerUpdate();
  SDL_JoystickUpdate();
  for (int player = 0; player < 2; ++player) {''',
'''  SDL_GameControllerUpdate();
  SDL_JoystickUpdate();
  s_smw_menu_polled = false;
  for (int player = 0; player < 2; ++player) {''')
    calls=s.count("AndroidQuitMenu_Poll(")
    if calls != 4:
        raise RuntimeError(f"Expected 1 wrapper definition call + 3 hardware calls, got {calls}")
    # Keep the single wrapper's own call intact while rewriting hardware ones.
    wrapper=s.index("static void Smw_PollExitMenu")
    after=s.index("static void Smw_PollPads(void) {",wrapper)
    before=s[:after]
    tail=s[after:]
    if tail.count("AndroidQuitMenu_Poll(")!=3:
        raise RuntimeError("Unexpected hardware poll layout")
    tail=tail.replace("AndroidQuitMenu_Poll(", "Smw_PollExitMenu(")
    s=before+tail
    s=replace_once(s,'''      if (SDL_JoystickNumHats(raw) > 0)
        Smw_HandleRawHat(gi, SDL_JoystickGetHat(raw, 0));
    }
  }
}

static void Smw_AndroidHidFallback''',
'''      if (SDL_JoystickNumHats(raw) > 0)
        Smw_HandleRawHat(gi, SDL_JoystickGetHat(raw, 0));
    }
  }
  // Touch-only device or Bluetooth controller currently disconnected.
  if (!s_smw_menu_polled)
    Smw_PollExitMenu(false, false, false, false);
}

static void Smw_AndroidHidFallback''')
    s=replace_once(s,'''    uint32 inputs = g_input_state | g_gamepad[0].axis_buttons | g_gamepad[1].axis_buttons << 12;''',
'''    // Touch + physical Bluetooth controller can play at the same time.
    uint32 touch = __atomic_load_n(&g_smw_touch_input, __ATOMIC_RELAXED);
    uint32 inputs = g_input_state | touch | g_gamepad[0].axis_buttons |
                    g_gamepad[1].axis_buttons << 12;''')
    native.write_text(s, encoding="utf-8")

    activity=project/"app/src/main/java/net/freyta/smw/MainActivity.java"
    j=activity.read_text()
    j=replace_once(j, "import android.view.KeyEvent;",
                   "import android.view.KeyEvent;\nimport android.os.SystemClock;\nimport android.content.pm.PackageManager;")
    j=replace_once(j, '        setupFiles();\n        super.onCreate(savedInstanceState);',
                   '        setupFiles();\n        super.onCreate(savedInstanceState);\n        installTouchControls();')
    # The upstream legacy overlay has disabled ABXY handlers; do not invoke it.
    # Full-screen transparent custom view is installed ONLY on touch devices.
    insert=r'''
    private TouchControlsView touchControls;
    private long lastBackUptime;

    private static native void nativeTouchButtons(int mask);

    void updateTouchButtons(int mask) {
        nativeTouchButtons(mask);
    }

    private void installTouchControls() {
        PackageManager pm = getPackageManager();
        if (!pm.hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN))
            return; // Android TV/projector uses only a real Bluetooth/USB pad
        android.view.ViewGroup content =
            (android.view.ViewGroup) findViewById(android.R.id.content);
        if (content == null) return;
        touchControls = new TouchControlsView(this);
        content.addView(touchControls, new android.view.ViewGroup.LayoutParams(
            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
            android.view.ViewGroup.LayoutParams.MATCH_PARENT));
        touchControls.bringToFront();
    }

    @Override protected void onPause() {
        if (touchControls != null) touchControls.clearButtons();
        super.onPause();
    }

    @Override public void onBackPressed() {
        long now = SystemClock.uptimeMillis();
        // First press asks, second press confirms, preserving normal SDL
        // shutdown and SRAM. Times out to prevent accidental later exits.
        if (lastBackUptime != 0 && now - lastBackUptime <= 2800) {
            lastBackUptime = 0;
            if (touchControls != null) touchControls.clearButtons();
            finish();
            return;
        }
        lastBackUptime = now;
        Toast.makeText(this, "Sair do jogo? Pressione VOLTAR novamente para confirmar.",
                Toast.LENGTH_LONG).show();
    }
'''
    end=j.rfind("\n}")
    if end<0: raise RuntimeError("MainActivity missing final class brace")
    j=j[:end]+"\n"+insert+j[end:]
    activity.write_text(j, encoding="utf-8")
    overlay_dest=project/"app/src/main/java/net/freyta/smw/TouchControlsView.java"
    overlay_dest.write_text((fork/"tools/TouchControlsView.java").read_text(encoding="utf-8"), encoding="utf-8")

    manifest=project/"app/src/main/AndroidManifest.xml"
    m=manifest.read_text()
    m=replace_once(m, 'android:screenOrientation="landscape"',
                   'android:screenOrientation="fullSensor"')
    manifest.write_text(m, encoding="utf-8")

    gradle=project/"app/build.gradle"
    g=gradle.read_text()
    g=replace_once(g, "versionCode 8", "versionCode 9")
    g=replace_once(g, 'versionName "1.0.8-tv"', 'versionName "1.0.9-tv-touch"')
    gradle.write_text(g, encoding="utf-8")
    print("PASS: Android TV + touchscreen controller + portrait 62% layout + BACK twice")

if __name__ == "__main__":
    import sys
    if len(sys.argv)!=3:
        raise SystemExit("usage: patch_android_touch.py ANDROID_PROJECT SMW_FORK")
    apply(sys.argv[1],sys.argv[2])
