#!/usr/bin/env python3
"""Android physical gamepad fallback for SMW TV v10.

Controller discovery on Android does not guarantee SDL 2 events reach libmain.
Bridge button + analog/hat input on Android's Activity event dispatcher into a
separate atomic SNES input mask, then OR it with existing SDL and touch input.
Preserve original SDL joystick/gamepad paths, native touch art and SRAM.
"""
from pathlib import Path

def one(s,a,b):
    n=s.count(a)
    if n!=1: raise RuntimeError("Expected one bridge anchor, found %d: %r" % (n,a[:115]))
    return s.replace(a,b,1)

def apply(root):
    root=Path(root)
    java=root/"app/src/main/java/net/freyta/smw/MainActivity.java"
    cfile=root/"app/jni/SMW_SRC/src/main.c"

    c=cfile.read_text(encoding="utf-8")
    c=one(c,'#include "android_quit_menu.h"',
           '#include "android_quit_menu.h"\n#include <jni.h>')
    c=one(c, "static GamepadInfo g_gamepad[2];", """static GamepadInfo g_gamepad[2];

/* SDL joystick polling still runs. Android dispatch is an independent
   fallback for devices recognized by Android but missing SDL events. */
static uint32 g_android_physical_buttons;

JNIEXPORT void JNICALL
Java_net_freyta_smw_MainActivity_nativePhysicalControllerMask(
    JNIEnv *env, jclass clazz, jint mask) {
  (void)env; (void)clazz;
  __atomic_store_n(&g_android_physical_buttons, (uint32)mask & 0xfffu,
                   __ATOMIC_RELAXED);
}
""")
    c=one(c, "  g_input_state = 0;\n  g_paused = 0;",
             "  g_input_state = 0;\n  __atomic_store_n(&g_android_physical_buttons, 0u, __ATOMIC_RELAXED);\n  g_paused = 0;")
    # Make sure native input is cleared also when SDLActivity can relaunch
    # in the same Linux process.
    c=one(c,"  g_input_state = 0;\n  return 0;",
          "  g_input_state = 0;\n  __atomic_store_n(&g_android_physical_buttons, 0u, __ATOMIC_RELAXED);\n  return 0;")
    c=one(c, "    uint32 inputs = g_input_state | g_gamepad[0].axis_buttons | g_gamepad[1].axis_buttons << 12;",
           """    uint32 physical = __atomic_load_n(&g_android_physical_buttons, __ATOMIC_RELAXED);
    uint32 inputs = g_input_state | physical | g_gamepad[0].axis_buttons |
                    g_gamepad[1].axis_buttons << 12;""")

    # Also support START+SELECT in HID keyboard/gamepad mode where SDL does
    # not deliver any joystick state. The menu overlay must poll every frame.
    begin=c.index("static void Smw_PollPads(void) {")
    end=c.index("static void Smw_AndroidHidFallback",begin)
    pre=c[:begin]
    part=c[begin:end]
    post=c[end:]
    calls=part.count("AndroidQuitMenu_Poll(")
    if calls!=3:
        raise RuntimeError("Expected 3 underlying SDL menu polls, got "+str(calls))
    part=part.replace("AndroidQuitMenu_Poll(", "Smw_AndroidMenuPoll(")
    # Trigger a fallback poll if no suitable SDL joystick is active.
    tail="  }\n}\n\n"
    if not part.endswith(tail):
        raise RuntimeError("Unexpected end to Smw_PollPads")
    part=part[:-len(tail)]+"""  }
  if (!s_android_menu_polled)
    Smw_AndroidMenuPoll(false, false, false, false);
}

"""
    wrapper="""static bool s_android_menu_polled;
static void Smw_AndroidMenuPoll(bool select, bool start,
                                bool accept, bool cancel) {
  uint32 held = __atomic_load_n(&g_android_physical_buttons, __ATOMIC_RELAXED);
  s_android_menu_polled = true;
  AndroidQuitMenu_Poll(select || (held & (1u << 2)) != 0,
                       start || (held & (1u << 3)) != 0,
                       accept || (held & (1u << 0)) != 0,
                       cancel || (held & (1u << 8)) != 0);
}

"""
    part=part.replace("static void Smw_PollPads(void) {",
                      "static void Smw_PollPads(void) {\n  s_android_menu_polled = false;",1)
    c=pre+wrapper+part+post
    cfile.write_text(c,encoding="utf-8")

    s=java.read_text(encoding="utf-8")
    s=one(s, "import android.view.InputDevice;",
          "import android.view.InputDevice;\nimport android.view.MotionEvent;")
    s=one(s, "    private View nativeOverlayView;",
          """    private View nativeOverlayView;

    // Bit order follows the native SMW kKbdRemap mapping, NOT Android's
    // button index: A,X,SELECT,START,UP,DOWN,LEFT,RIGHT,B,Y,L,R.
    private static final int PAD_A=1, PAD_X=2, PAD_SELECT=4, PAD_START=8;
    private static final int PAD_UP=16, PAD_DOWN=32, PAD_LEFT=64, PAD_RIGHT=128;
    private static final int PAD_B=256, PAD_Y=512, PAD_L=1024, PAD_R=2048;
    private int physicalKeyMask, physicalAxisMask, activePhysicalDevice=-1;
    private static native void nativePhysicalControllerMask(int mask);

    private void sendPhysicalInput() {
        nativePhysicalControllerMask(physicalKeyMask | physicalAxisMask);
    }

    private void clearPhysicalInput() {
        physicalKeyMask=physicalAxisMask=0;
        activePhysicalDevice=-1;
        sendPhysicalInput();
    }

    private boolean recognizedPhysicalDevice(int deviceId, int source) {
        InputDevice device=InputDevice.getDevice(deviceId);
        if (device==null || device.isVirtual()) return false;
        String name=device.getName();
        if (name!=null) {
            String lower=name.toLowerCase(java.util.Locale.US);
            if (lower.contains("gpio_ir_recv") ||
                lower.contains("virtual-search") ||
                lower.contains("mtk-kpd") ||
                lower.contains("accdet")) return false;
        }
        int combined=source | device.getSources();
        return (combined & InputDevice.SOURCE_GAMEPAD)==InputDevice.SOURCE_GAMEPAD ||
               (combined & InputDevice.SOURCE_JOYSTICK)==InputDevice.SOURCE_JOYSTICK;
    }

    private int physicalButton(int code) {
        switch(code) {
        case KeyEvent.KEYCODE_BUTTON_A: return PAD_A;
        case KeyEvent.KEYCODE_BUTTON_B: return PAD_B;
        case KeyEvent.KEYCODE_BUTTON_X: return PAD_X;
        case KeyEvent.KEYCODE_BUTTON_Y: return PAD_Y;
        case KeyEvent.KEYCODE_BUTTON_L1: return PAD_L;
        case KeyEvent.KEYCODE_BUTTON_R1: return PAD_R;
        case KeyEvent.KEYCODE_BUTTON_START: return PAD_START;
        case KeyEvent.KEYCODE_BUTTON_SELECT: return PAD_SELECT;
        case KeyEvent.KEYCODE_DPAD_UP: return PAD_UP;
        case KeyEvent.KEYCODE_DPAD_DOWN: return PAD_DOWN;
        case KeyEvent.KEYCODE_DPAD_LEFT: return PAD_LEFT;
        case KeyEvent.KEYCODE_DPAD_RIGHT: return PAD_RIGHT;
        case KeyEvent.KEYCODE_DPAD_CENTER: return PAD_A;
        default: return 0;
        }
    }

    private void restoreGameFocus() {
        // The stock on-screen ImageButtons can steal input focus from SDL.
        // When a Bluetooth gamepad hides the controls, return focus to the
        // actual SDL rendering surface, not to a now-hidden overlay.
        if (mSurface != null) {
            mSurface.setFocusableInTouchMode(true);
            mSurface.requestFocus();
        }
    }
""")
    s=one(s,"        nativeOverlayView.setVisibility(show ? View.VISIBLE : View.GONE);",
          """        nativeOverlayView.setVisibility(show ? View.VISIBLE : View.GONE);
        restoreGameFocus();""")
    s=one(s, "        inflateOverlay();  // original layout; never create another overlay",
          """        inflateOverlay();  // original layout; never create another overlay
        if (nativeOverlayView instanceof ViewGroup) {
            ((ViewGroup)nativeOverlayView).setDescendantFocusability(
                ViewGroup.FOCUS_BLOCK_DESCENDANTS);
        }
        restoreGameFocus();""")
    s=one(s, "        updateNativeOverlayVisibility();\n    }\n\n    @Override protected void onPause()",
          "        updateNativeOverlayVisibility();\n        restoreGameFocus();\n    }\n\n    @Override protected void onPause()")
    s=one(s, "        releaseNativeTouches();\n        if (inputManager != null && devicesRegistered) {",
          "        releaseNativeTouches();\n        clearPhysicalInput();\n        if (inputManager != null && devicesRegistered) {")
    s=one(s, "        @Override public void onInputDeviceRemoved(int id) { updateNativeOverlayVisibility(); }",
          """        @Override public void onInputDeviceRemoved(int id) {
            if (id == activePhysicalDevice) clearPhysicalInput();
            updateNativeOverlayVisibility();
        }""")

    start=s.index("    @Override public boolean dispatchKeyEvent(KeyEvent event) {")
    stop=s.index("    @Override public void onBackPressed()",start)
    s=s[:start]+r'''    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        final int code=event.getKeyCode();
        // System BACK, rather than gamepad Select, requests confirmation.
        if (code==KeyEvent.KEYCODE_BACK) {
            if (event.getAction()==KeyEvent.ACTION_UP && !event.isCanceled())
                onBackPressed();
            return true;
        }
        int button=physicalButton(code);
        boolean physical=recognizedPhysicalDevice(event.getDeviceId(),event.getSource());
        if (physical && button!=0) {
            if (activePhysicalDevice!=-1 && activePhysicalDevice!=event.getDeviceId())
                clearPhysicalInput();
            activePhysicalDevice=event.getDeviceId();
            if (event.getAction()==KeyEvent.ACTION_DOWN)
                physicalKeyMask|=button;
            else if (event.getAction()==KeyEvent.ACTION_UP)
                physicalKeyMask&=~button;
            sendPhysicalInput();
            // Direct native bridge bypasses unreliable SDL2 Android HID
            // dispatch while SDL joystick polling remains enabled.
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    private float readAxis(MotionEvent event, InputDevice device, int axis) {
        InputDevice.MotionRange range=device.getMotionRange(axis,event.getSource());
        if (range==null) range=device.getMotionRange(axis);
        return range==null ? 0f : event.getAxisValue(axis);
    }

    @Override public boolean dispatchGenericMotionEvent(MotionEvent event) {
        int source=event.getSource();
        if (event.getAction()==MotionEvent.ACTION_MOVE &&
            (source & InputDevice.SOURCE_JOYSTICK)==InputDevice.SOURCE_JOYSTICK &&
            recognizedPhysicalDevice(event.getDeviceId(),source)) {
            InputDevice device=InputDevice.getDevice(event.getDeviceId());
            if (device!=null) {
                if (activePhysicalDevice!=-1 && activePhysicalDevice!=event.getDeviceId())
                    clearPhysicalInput();
                activePhysicalDevice=event.getDeviceId();
                float x=readAxis(event,device,MotionEvent.AXIS_X);
                float y=readAxis(event,device,MotionEvent.AXIS_Y);
                float hatX=readAxis(event,device,MotionEvent.AXIS_HAT_X);
                float hatY=readAxis(event,device,MotionEvent.AXIS_HAT_Y);
                final float deadzone=.40f;
                int m=0;
                if (x < -deadzone || hatX < -.50f) m|=PAD_LEFT;
                if (x > deadzone || hatX > .50f) m|=PAD_RIGHT;
                if (y < -deadzone || hatY < -.50f) m|=PAD_UP;
                if (y > deadzone || hatY > .50f) m|=PAD_DOWN;
                physicalAxisMask=m;
                sendPhysicalInput();
            }
            return true;
        }
        return super.dispatchGenericMotionEvent(event);
    }

'''+s[stop:]
    java.write_text(s,encoding="utf-8")

    gradle=root/"app/build.gradle"
    g=gradle.read_text(encoding="utf-8")
    g=one(g, "versionCode 10","versionCode 11")
    g=one(g,'versionName "1.0.10-native-layout"','versionName "1.0.11-pad-bridge"')
    gradle.write_text(g,encoding="utf-8")
    print("PASS controller bridge: Activity key/motion + SDL OR + focus recovery")

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:
        raise SystemExit("usage: patch_android_gamepad_bridge.py PROJECT")
    apply(sys.argv[1])
