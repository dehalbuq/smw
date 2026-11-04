#!/usr/bin/env python3
"""Apply projector-safe Android input and integer pixel scaling to freyta SDL2 SMW.

Based on the Chanuo A1 / PG-9068 diagnostic findings in FITD-R36S:
IR input 'gpio_ir_recv', 'virtual-search' and MTK virtual devices must not
consume player controller slots before physical Bluetooth/USB joysticks.
Only changes the transient Android project built in CI, not desktop/R36S.
"""
from pathlib import Path

MAIN = Path("app/jni/SMW_SRC/src/main.c")


def one(s, old, new):
    n = s.count(old)
    if n != 1:
        raise RuntimeError(f"expected exactly one Android C anchor ({n}): {old[:90]!r}")
    return s.replace(old, new, 1)


def apply(android_project):
    main = Path(android_project) / MAIN
    s = main.read_text(encoding="utf-8")

    s = one(s, '#include "android_logging.h"', '#include "android_logging.h"\\n#include "android_quit_menu.h"')

    s = one(s, "static void OpenOneGamepad(int i);",
            """static void Smw_AttachBestPads(void);
static void Smw_ClosePad(int player);
static int Smw_RawButtonToGameButton(int button);
static void Smw_HandleRawHat(GamepadInfo *gi, Uint8 hat);
static void Smw_PollPads(void);
static void Smw_AndroidHidFallback(SDL_Keycode key, bool pressed);
static SDL_GameController *s_smw_pad[2] = {NULL, NULL};
static SDL_Joystick *s_smw_raw_pad[2] = {NULL, NULL};""")

    start = s.index("static void OpenOneGamepad(int i) {")
    end = s.index("static int RemapSdlButton(int button) {", start)
    code = r'''
// Chanuo A1: SDL marks the infrared remote and virtual-search inputs as
// GameControllers. Prefer physical pads by name and capabilities, not index.
static SDL_GameController *s_smw_pad[2] = {NULL, NULL};
static SDL_Joystick *s_smw_raw_pad[2] = {NULL, NULL};

static bool Smw_IsVirtualInput(const char *name) {
  static const char *bad[] = {
    "gpio_ir_recv", "virtual-search", "Android Accelerometer",
    "Lm_Misc", "ACCDET", "mtk-kpd"
  };
  if (!name || !name[0]) return true;
  for (int i = 0; i < (int)(sizeof(bad) / sizeof(bad[0])); ++i)
    if (SDL_strcasecmp(name, bad[i]) == 0) return true;
  return false;
}

static int Smw_PhysicalScore(int device) {
  if (Smw_IsVirtualInput(SDL_JoystickNameForIndex(device))) return -1;
  SDL_Joystick *joy = SDL_JoystickOpen(device);
  if (!joy) return -1;
  int axes = SDL_JoystickNumAxes(joy);
  int buttons = SDL_JoystickNumButtons(joy);
  int hats = SDL_JoystickNumHats(joy);
  SDL_JoystickClose(joy);
  // Reject remote-like devices with few/no gamepad controls.
  if (buttons < 2 && hats < 1) return -1;
  if (axes < 2 && buttons < 6 && hats < 1) return -1;
  int score = 0;
  if (axes >= 2) score += 100;
  if (axes >= 4) score += 20;
  if (buttons >= 4) score += 50;
  if (buttons >= 8) score += 10;
  if (hats > 0) score += 10;
  if (SDL_IsGameController(device)) score += 20;
  if (SDL_JoystickGetDeviceVendor(device) &&
      SDL_JoystickGetDeviceProduct(device)) score += 10;
  return score;
}

static void Smw_ClosePad(int player) {
  if (player < 0 || player >= 2) return;
  GamepadInfo *gi = &g_gamepad[player];
  for (int button = 0; button < kGamepadBtn_Count; ++button)
    if (gi->modifiers & (1u << button))
      HandleGamepadInput(gi, button, false);
  if (s_smw_pad[player]) {
    SDL_GameControllerClose(s_smw_pad[player]);
    s_smw_pad[player] = NULL;
  }
  if (s_smw_raw_pad[player]) {
    SDL_JoystickClose(s_smw_raw_pad[player]);
    s_smw_raw_pad[player] = NULL;
  }
  memset(gi, 0, sizeof(*gi));
  gi->index = (uint8)player;
  gi->joystick_id = -1;
}

static void Smw_AttachBestPads(void) {
  for (int player = 0; player < 2; ++player) {
    if (!g_config.enable_gamepad[player] ||
        g_gamepad[player].joystick_id != -1) continue;
    int best_device = -1, best_score = -1;
    SDL_JoystickID chosen_id = -1;
    for (int device = 0; device < SDL_NumJoysticks(); ++device) {
      SDL_JoystickID id = SDL_JoystickGetDeviceInstanceID(device);
      if (id < 0 || id == g_gamepad[0].joystick_id ||
                    id == g_gamepad[1].joystick_id) continue;
      int score = Smw_PhysicalScore(device);
      if (score > best_score) {
        best_score = score;
        best_device = device;
        chosen_id = id;
      }
    }
    if (best_device < 0) return;
    SDL_GameController *pad = NULL;
    SDL_Joystick *raw = NULL;
    SDL_Joystick *joystick = NULL;
    if (SDL_IsGameController(best_device)) {
      pad = SDL_GameControllerOpen(best_device);
      if (pad) joystick = SDL_GameControllerGetJoystick(pad);
    }
    if (!joystick) {
      raw = SDL_JoystickOpen(best_device);
      joystick = raw;
    }
    if (!joystick) {
      if (pad) SDL_GameControllerClose(pad);
      return;
    }
    GamepadInfo *gi = &g_gamepad[player];
    memset(gi, 0, sizeof(*gi));
    gi->index = (uint8)player;
    gi->joystick_id = SDL_JoystickInstanceID(joystick);
    s_smw_pad[player] = pad;
    s_smw_raw_pad[player] = raw;
    fprintf(stderr, "SMW Android physical pad P%d: %s (score %d, id %d)\n",
            player + 1, SDL_JoystickNameForIndex(best_device), best_score,
            (int)chosen_id);
  }
}

// Fallback for older Bluetooth devices without SDL GameController mapping.
static int Smw_RawButtonToGameButton(int button) {
  // Chanuo A1 / PG-9068 mapping confirmed by FITD's Android HID report:
  // 6 axes, 19 buttons, zero hats; DPAD is buttons 11..14.
  switch (button) {
    case 0: return kGamepadBtn_A;
    case 1: return kGamepadBtn_B;
    case 2: return kGamepadBtn_X;
    case 3: return kGamepadBtn_Y;
    case 4: return kGamepadBtn_Back;
    case 6: return kGamepadBtn_Start;
    case 7: return kGamepadBtn_L3;
    case 8: return kGamepadBtn_R3;
    case 9: return kGamepadBtn_L1;
    case 10: return kGamepadBtn_R1;
    case 11: return kGamepadBtn_DpadUp;
    case 12: return kGamepadBtn_DpadDown;
    case 13: return kGamepadBtn_DpadLeft;
    case 14: return kGamepadBtn_DpadRight;
    default: return -1;
  }
}

static void Smw_HandleRawHat(GamepadInfo *gi, Uint8 hat) {
  HandleGamepadInput(gi, kGamepadBtn_DpadUp,    (hat & SDL_HAT_UP) != 0);
  HandleGamepadInput(gi, kGamepadBtn_DpadDown,  (hat & SDL_HAT_DOWN) != 0);
  HandleGamepadInput(gi, kGamepadBtn_DpadLeft,  (hat & SDL_HAT_LEFT) != 0);
  HandleGamepadInput(gi, kGamepadBtn_DpadRight, (hat & SDL_HAT_RIGHT) != 0);
}

// Some Android HID controllers report DPAD as keyboard arrow keys. Do not
// consume remote arrow events as an extra player while a real pad is active.
// FITD's working Chanuo A1 test polls the actual controller state.
// Android TV firmware may enumerate devices without sending button events.
static void Smw_PollPads(void) {
  SDL_GameControllerUpdate();
  SDL_JoystickUpdate();
  for (int player = 0; player < 2; ++player) {
    GamepadInfo *gi = &g_gamepad[player];
    if (gi->joystick_id < 0) continue;
    SDL_GameController *pad = s_smw_pad[player];
    if (pad) {
      if (!SDL_GameControllerGetAttached(pad)) {
        Smw_ClosePad(player);
        continue;
      }
      // Prefer raw HID readings for the PG-9068 on this Mediatek Android TV:
      // its SDL GameController button events may be lost behind the IR remote.
      SDL_Joystick *joy = SDL_GameControllerGetJoystick(pad);
      const char *rawname = joy ? SDL_JoystickName(joy) : NULL;
      bool is_ipega = rawname && SDL_strcasecmp(rawname, "PG-9068") == 0;
      if (is_ipega) {
        if (player == 0) {
          // FITD diagnosis: PG-9068 raw SELECT=b4, START=b6,
          // A=b0, B=b1. Poll rather than waiting for Android TV events.
          AndroidQuitMenu_Poll(SDL_JoystickGetButton(joy, 4) != 0,
                               SDL_JoystickGetButton(joy, 6) != 0,
                               SDL_JoystickGetButton(joy, 0) != 0,
                               SDL_JoystickGetButton(joy, 1) != 0);
        }
        if (AndroidQuitMenu_IsOpen()) {
          for (int b = 0; b < kGamepadBtn_Count; ++b)
            if (gi->modifiers & (1u << b)) HandleGamepadInput(gi, b, false);
          gi->axis_buttons = 0;
          continue;
        }
        for (int b = 0; b < SDL_JoystickNumButtons(joy); ++b) {
          int key = Smw_RawButtonToGameButton(b);
          if (key >= 0)
            HandleGamepadInput(gi, key, SDL_JoystickGetButton(joy, b) != 0);
        }
        if (SDL_JoystickNumAxes(joy) > 1) {
          HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTX, SDL_JoystickGetAxis(joy, 0));
          HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTY, SDL_JoystickGetAxis(joy, 1));
        }
        continue;
      }
      if (player == 0) {
        AndroidQuitMenu_Poll(
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_BACK) != 0,
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_START) != 0,
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_A) != 0,
            SDL_GameControllerGetButton(pad, SDL_CONTROLLER_BUTTON_B) != 0);
      }
      if (AndroidQuitMenu_IsOpen()) {
        for (int b = 0; b < kGamepadBtn_Count; ++b)
          if (gi->modifiers & (1u << b)) HandleGamepadInput(gi, b, false);
        gi->axis_buttons = 0;
        continue;
      }
      for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX; ++b) {
        int mapped = RemapSdlButton(b);
        if (mapped >= 0)
          HandleGamepadInput(gi, mapped,
                             SDL_GameControllerGetButton(pad, (SDL_GameControllerButton)b) != 0);
      }
      HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTX,
                             SDL_GameControllerGetAxis(pad, SDL_CONTROLLER_AXIS_LEFTX));
      HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTY,
                             SDL_GameControllerGetAxis(pad, SDL_CONTROLLER_AXIS_LEFTY));
      HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_TRIGGERLEFT,
                             SDL_GameControllerGetAxis(pad, SDL_CONTROLLER_AXIS_TRIGGERLEFT));
      HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_TRIGGERRIGHT,
                             SDL_GameControllerGetAxis(pad, SDL_CONTROLLER_AXIS_TRIGGERRIGHT));
    } else if (s_smw_raw_pad[player]) {
      SDL_Joystick *raw = s_smw_raw_pad[player];
      if (!SDL_JoystickGetAttached(raw)) {
        Smw_ClosePad(player);
        continue;
      }
      if (player == 0)
        AndroidQuitMenu_Poll(SDL_JoystickGetButton(raw, 4) != 0,
                             SDL_JoystickGetButton(raw, 6) != 0,
                             SDL_JoystickGetButton(raw, 0) != 0,
                             SDL_JoystickGetButton(raw, 1) != 0);
      if (AndroidQuitMenu_IsOpen()) {
        for (int b = 0; b < kGamepadBtn_Count; ++b)
          if (gi->modifiers & (1u << b)) HandleGamepadInput(gi, b, false);
        gi->axis_buttons = 0;
        continue;
      }
      for (int b = 0; b < SDL_JoystickNumButtons(raw); ++b) {
        int mapped = Smw_RawButtonToGameButton(b);
        if (mapped >= 0)
          HandleGamepadInput(gi, mapped, SDL_JoystickGetButton(raw, b) != 0);
      }
      if (SDL_JoystickNumAxes(raw) >= 2) {
        HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTX, SDL_JoystickGetAxis(raw, 0));
        HandleGamepadAxisInput(gi, SDL_CONTROLLER_AXIS_LEFTY, SDL_JoystickGetAxis(raw, 1));
      }
      if (SDL_JoystickNumHats(raw) > 0)
        Smw_HandleRawHat(gi, SDL_JoystickGetHat(raw, 0));
    }
  }
}

static void Smw_AndroidHidFallback(SDL_Keycode key, bool pressed) {
  if (g_gamepad[0].joystick_id != -1) return;
  int direction = -1;
  if (key == SDLK_UP) direction = 0;
  else if (key == SDLK_DOWN) direction = 1;
  else if (key == SDLK_LEFT) direction = 2;
  else if (key == SDLK_RIGHT) direction = 3;
  if (direction >= 0) HandleCommand(kKeys_Controls + direction, pressed);
}
'''
    code = code.replace("""static SDL_GameController *s_smw_pad[2] = {NULL, NULL};
static SDL_Joystick *s_smw_raw_pad[2] = {NULL, NULL};""", "")
    s = s[:start] + code + "\n" + s[end:]

    s = one(s, "  ParseConfigFile(config_file);",
            """  ParseConfigFile(config_file);
  // Keep original 256x224 pixels square: no stretched 4:3 or filtering.
  g_config.output_method = kOutputMethod_SDL;
  g_config.extended_aspect_ratio = 0;
  g_config.ignore_aspect_ratio = false;
  g_config.linear_filtering = false;
  g_config.enable_gamepad[0] = true;
  g_config.enable_gamepad[1] = true;
  g_config.has_keyboard_controls |= 1;
  SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");""")

    s = one(s, """  bool custom_size = g_config.window_width != 0 && g_config.window_height != 0;""", """  // Known working PG-9068 GUID and button layout from FITD Android hardware
  // diagnostic (Chanuo A1): 6473:1026, D-pad on raw buttons 11..14.
  SDL_GameControllerAddMapping(
    "050013054919000002040000ffff3f00,PG-9068,"
    "a:b0,b:b1,x:b2,y:b3,back:b4,start:b6,leftstick:b7,rightstick:b8,"
    "leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,"
    "dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,"
    "lefttrigger:a4,righttrigger:a5,platform:Android,");
  bool custom_size = g_config.window_width != 0 && g_config.window_height != 0;""")

    s = one(s,
      """  if (!g_config.ignore_aspect_ratio)
    SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);
  if (g_config.linear_filtering)
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "best");""",
      """  // Nearest neighbour at integer multiples; SDL centers black borders.
  SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);
  SDL_RenderSetIntegerScale(renderer, SDL_TRUE);
  SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);""")

    s = one(s, """  for (int i = 0; i < SDL_NumJoysticks(); i++)
    OpenOneGamepad(i);""", """  Smw_AttachBestPads();""")

    evstart=s.index("      case SDL_CONTROLLERDEVICEADDED:")
    evend=s.index("      case SDL_CONTROLLERAXISMOTION:", evstart)
    s=s[:evstart]+r'''      case SDL_CONTROLLERDEVICEADDED:
      case SDL_JOYDEVICEADDED:
        // Never trust the newly added index: IR/virtual inputs may come first.
        Smw_AttachBestPads();
        break;
      case SDL_CONTROLLERDEVICEREMOVED:
      case SDL_JOYDEVICEREMOVED: {
        SDL_JoystickID removed = event.type == SDL_CONTROLLERDEVICEREMOVED ?
            event.cdevice.which : event.jdevice.which;
        for (int player = 0; player < 2; ++player)
          if (g_gamepad[player].joystick_id == removed)
            Smw_ClosePad(player);
        Smw_AttachBestPads();
        break;
      }
''' +s[evend:]

    s = one(s, """      case SDL_MOUSEWHEEL:""", r'''      case SDL_JOYAXISMOTION:
        gi = GetGamepadInfo(event.jaxis.which);
        if (gi && s_smw_raw_pad[gi->index] && event.jaxis.axis < 2)
          HandleGamepadAxisInput(gi, event.jaxis.axis, event.jaxis.value);
        break;
      case SDL_JOYBUTTONDOWN:
      case SDL_JOYBUTTONUP:
        gi = GetGamepadInfo(event.jbutton.which);
        if (gi && s_smw_raw_pad[gi->index]) {
          int button = Smw_RawButtonToGameButton(event.jbutton.button);
          if (button >= 0)
            HandleGamepadInput(gi, button, event.type == SDL_JOYBUTTONDOWN);
        }
        break;
      case SDL_JOYHATMOTION:
        gi = GetGamepadInfo(event.jhat.which);
        if (gi && s_smw_raw_pad[gi->index] && event.jhat.hat == 0)
          Smw_HandleRawHat(gi, event.jhat.value);
        break;
      case SDL_MOUSEWHEEL:''')

    s = one(s, """    if (g_paused != audiopaused) {""", """    // Poll the actual pad state, instead of depending only on SDL events.
    if ((frameCtr & 63u) == 0) Smw_AttachBestPads();
    Smw_PollPads();

    if (g_paused != audiopaused) {""")

    s = one(s,
"""      case SDL_KEYDOWN:
        HandleInput(event.key.keysym.sym, event.key.keysym.mod, true);
        break;
      case SDL_KEYUP:
        HandleInput(event.key.keysym.sym, event.key.keysym.mod, false);
        break;""",
"""      case SDL_KEYDOWN:
        Smw_AndroidHidFallback(event.key.keysym.sym, true);
        HandleInput(event.key.keysym.sym, event.key.keysym.mod, true);
        break;
      case SDL_KEYUP:
        Smw_AndroidHidFallback(event.key.keysym.sym, false);
        HandleInput(event.key.keysym.sym, event.key.keysym.mod, false);
        break;""")

    # Disallow deliberate render skipping even during turbo or replay-turbo.
    # Keep the original 60 Hz pacing: under load the game slows down instead
    # of silently dropping sprites/animation frames. Video frames are presented
    # once per simulation frame, with no fixed FPS cap below 60.
    s = one(s, """    g_snes->disableRender = (g_turbo ^ (is_replay & g_replay_turbo)) && (frameCtr & (g_turbo ? 0xf : 0x7f)) != 0;

    if (!g_snes->disableRender)
      DrawPpuFrameWithPerf();""",
        """    // Chanuo SMW ARMv7: intentional frame skipping disabled.
    // One visible render per executed game frame. Slowdown is preferable
    // to losing transformation/animation frames.
    g_snes->disableRender = false;
    DrawPpuFrameWithPerf();""")

    # Render exactly the same compact font/overlay as the R36S menu,
    # directly into the native 256x224 pixel buffer before SDL presents it.
    s = one(s, "  g_renderer_funcs.EndDraw();",
            """  if (AndroidQuitMenu_IsOpen()) {
    AndroidQuitMenu_Draw(pixel_buffer, pitch, g_snes_width * render_scale,
                         g_snes_height * render_scale, render_scale);
  }
  g_renderer_funcs.EndDraw();""")

    # Keep audio paused and game logic frozen while the exit menu is visible.
    # Return through the normal SDL cleanup path rather than calling exit().
    s = one(s, """    if (g_paused != audiopaused) {
      audiopaused = g_paused;""",
      """    if (AndroidQuitMenu_WantsExit()) {
      running = false;
      break;
    }
    bool paused_for_menu = AndroidQuitMenu_IsOpen();
    bool should_pause_audio = g_paused || paused_for_menu;
    if (should_pause_audio != audiopaused) {
      audiopaused = should_pause_audio;""")

    s = one(s, """    if (g_paused) {
      SDL_Delay(16);
      continue;
    }""", """    if (paused_for_menu) {
      // Draw menu over the last game frame without advancing simulation.
      DrawPpuFrameWithPerf();
      SDL_Delay(16);
      continue;
    }
    if (g_paused) {
      SDL_Delay(16);
      continue;
    }""")

    # SDL button events may still be delivered before raw polling. Ignore
    # them while the menu is up, but keep hot-plug and SDL_QUIT functioning.
    s = one(s, """    while (SDL_PollEvent(&event)) {
      switch (event.type) {""",
      """    while (SDL_PollEvent(&event)) {
      if (AndroidQuitMenu_IsOpen() &&
          (event.type == SDL_CONTROLLERBUTTONDOWN ||
           event.type == SDL_CONTROLLERBUTTONUP ||
           event.type == SDL_CONTROLLERAXISMOTION ||
           event.type == SDL_JOYBUTTONDOWN ||
           event.type == SDL_JOYBUTTONUP ||
           event.type == SDL_JOYAXISMOTION ||
           event.type == SDL_JOYHATMOTION ||
           event.type == SDL_KEYDOWN || event.type == SDL_KEYUP))
        continue;
      switch (event.type) {""")

    # SDL2 calls from the original Android host require no new library.
    main.write_text(s, encoding="utf-8")
    print("Android TV gamepad selector, raw joystick fallback, and pixel-perfect SDL2 scaling applied")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("usage: patch_android_projector.py ANDROID_PROJECT")
    apply(sys.argv[1])
