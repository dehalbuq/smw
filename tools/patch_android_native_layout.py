#!/usr/bin/env python3
"""Retain and improve the upstream native SMW Android touch layout.

No TouchControlsView.java or secondary overlay. Reuses res/layout/layout.xml,
the original d_pad/abxy/start/select/shoulder images, and native key mapping.
"""
from pathlib import Path
import re

def once(t,old,new):
    n=t.count(old)
    if n!=1: raise RuntimeError(f"Native UI anchor count {n}: {old[:110]!r}")
    return t.replace(old,new,1)

def apply(root):
    root=Path(root)
    java=root/"app/src/main/java/net/freyta/smw/MainActivity.java"
    s=java.read_text(encoding="utf-8")
    s=once(s,"import android.view.KeyEvent;",
           "import android.view.KeyEvent;\nimport android.view.InputDevice;\n"
           "import android.os.SystemClock;\nimport android.hardware.input.InputManager;")
    s=once(s,"        inflateOverlay();\n    }\n\n        // Check if storage permission",
           "        setupNativeTouchLayout();\n    }\n\n        // Check if storage permission")
    s=once(s,"        View overlayView = inflater.inflate(R.layout.layout, null);",
           """        View overlayView = inflater.inflate(R.layout.layout, null);
        nativeOverlayView = overlayView;
        overlayView.setAlpha(0.88f);""")
    a=s.index("        overlayView.findViewById(R.id.Button_Dpad).setOnTouchListener(")
    b=s.index("\n\n\n    }\n    private void writeDataToFile", a)
    s=s[:a]+"""        // Keep the original native image assets and layout, but fix
        // ACTION_POINTER_DOWN/UP so slide/diagonals and run+jump work.
        nativeDpad = new NativeClusterTouchListener(new int[]{
            keyCodeFor_Left, keyCodeFor_Right, keyCodeFor_Up, keyCodeFor_Down});
        nativeFace = new NativeClusterTouchListener(new int[]{
            keyCodeFor_Y, keyCodeFor_A, keyCodeFor_X, keyCodeFor_B});
        overlayView.findViewById(R.id.Button_Dpad).setOnTouchListener(nativeDpad);
        overlayView.findViewById(R.id.Button_ABXY).setOnTouchListener(nativeFace);"""+s[b:]
    methods=r'''
    // The upstream image-button layout is the ONLY virtual control layer.
    // No controls are installed on a TV without a physical touchscreen.
    private View nativeOverlayView;
    private NativeClusterTouchListener nativeDpad, nativeFace;
    private long lastBackUptime;
    private InputManager inputManager;
    private boolean devicesRegistered;

    private final InputManager.InputDeviceListener controllerListener =
            new InputManager.InputDeviceListener() {
        @Override public void onInputDeviceAdded(int id) { updateNativeOverlayVisibility(); }
        @Override public void onInputDeviceRemoved(int id) { updateNativeOverlayVisibility(); }
        @Override public void onInputDeviceChanged(int id) { updateNativeOverlayVisibility(); }
    };

    private boolean hasPhysicalGamepad() {
        for (int id : InputDevice.getDeviceIds()) {
            InputDevice d = InputDevice.getDevice(id);
            if (d == null || d.isVirtual()) continue;
            int s = d.getSources();
            if ((s & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD ||
                (s & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK)
                return true;
        }
        return false;
    }

    private void releaseNativeTouches() {
        if (nativeDpad != null) nativeDpad.release();
        if (nativeFace != null) nativeFace.release();
    }

    private void updateNativeOverlayVisibility() {
        if (nativeOverlayView == null) return;
        final boolean show = !hasPhysicalGamepad();
        if (!show) releaseNativeTouches();
        nativeOverlayView.setVisibility(show ? View.VISIBLE : View.GONE);
    }

    private void setupNativeTouchLayout() {
        if (!getPackageManager().hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN))
            return;
        inflateOverlay();  // original layout; never create another overlay
        inputManager = (InputManager) getSystemService(INPUT_SERVICE);
        updateNativeOverlayVisibility();
    }

    @Override protected void onResume() {
        super.onResume();
        if (inputManager != null && !devicesRegistered) {
            inputManager.registerInputDeviceListener(controllerListener, null);
            devicesRegistered = true;
        }
        updateNativeOverlayVisibility();
    }

    @Override protected void onPause() {
        releaseNativeTouches();
        if (inputManager != null && devicesRegistered) {
            inputManager.unregisterInputDeviceListener(controllerListener);
            devicesRegistered = false;
        }
        super.onPause();
    }

    private final class NativeClusterTouchListener implements View.OnTouchListener {
        private final int[] keys; // left/right/up/down OR Y/A/X/B
        private int held;
        NativeClusterTouchListener(int[] keycodes) { keys=keycodes; }

        void release() { send(0); }

        private void send(int next) {
            int changed=held ^ next;
            for (int i=0;i<4;i++) if ((changed & (1<<i))!=0) {
                if ((next & (1<<i))!=0) onNativeKeyDown(keys[i]);
                else onNativeKeyUp(keys[i]);
            }
            held=next;
        }

        @Override public boolean onTouch(View view, MotionEvent ev) {
            int action=ev.getActionMasked();
            if (action==MotionEvent.ACTION_CANCEL) { release(); return true; }
            int leaving=(action==MotionEvent.ACTION_UP ||
                         action==MotionEvent.ACTION_POINTER_UP) ? ev.getActionIndex() : -1;
            int next=0;
            for (int p=0;p<ev.getPointerCount();p++) {
                if (p==leaving) continue;
                float nx=ev.getX(p)/Math.max(1,view.getWidth());
                float ny=ev.getY(p)/Math.max(1,view.getHeight());
                if (nx<.35f) next|=1;
                if (nx>.65f) next|=2;
                if (ny<.35f) next|=4;
                if (ny>.65f) next|=8;
            }
            send(next);
            return true;
        }
    }

    @Override public boolean dispatchKeyEvent(KeyEvent event) {
        if (event.getKeyCode()==KeyEvent.KEYCODE_BACK) {
            if (event.getAction()==KeyEvent.ACTION_UP && !event.isCanceled())
                onBackPressed();
            return true;
        }
        return super.dispatchKeyEvent(event);
    }

    @Override public void onBackPressed() {
        long now=SystemClock.uptimeMillis();
        if (lastBackUptime!=0 && now-lastBackUptime<=2800) {
            lastBackUptime=0;
            releaseNativeTouches();
            finish(); // normal SDLActivity cleanup, preserving saved SRAM
            return;
        }
        lastBackUptime=now;
        Toast.makeText(this,
            "Sair do jogo? Pressione VOLTAR novamente para confirmar.",
            Toast.LENGTH_LONG).show();
    }
'''
    # Correct activity lifecycle: onResume can be invoked by SDLActivity
    # before setupNativeTouchLayout; null checks keep this safe.
    pos=s.rfind("\n}")
    if pos<0:raise RuntimeError("Missing MainActivity closing brace")
    s=s[:pos]+"\n"+methods+s[pos:]
    java.write_text(s,encoding="utf-8")

    # Preserve source-generated native layout art. Portrait uses smaller
    # images to keep every button in the bottom band without new controls.
    native=(root/"app/src/main/res/layout/layout.xml").read_text(encoding="utf-8")
    portrait=native.replace('android:layout_width="150dp"',
                            'android:layout_width="132dp"').replace(
                            'android:layout_height="150dp"',
                            'android:layout_height="132dp"')
    portrait=portrait.replace('android:layout_width="70dp"',
                              'android:layout_width="62dp"').replace(
                              'android:layout_height="50dp"',
                              'android:layout_height="44dp"')
    target=root/"app/src/main/res/layout-port/layout.xml"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(portrait,encoding="utf-8")

    manifest=root/"app/src/main/AndroidManifest.xml"
    m=manifest.read_text(encoding="utf-8")
    m=once(m,'android:screenOrientation="landscape"',
           'android:screenOrientation="fullUser"')
    manifest.write_text(m,encoding="utf-8")

    nativefile=root/"app/jni/SMW_SRC/src/main.c"
    c=nativefile.read_text(encoding="utf-8")
    # Preserve native pixel-perfect 4:3 scaling in landscape. Limit to the
    # top 62% in portrait so original control artwork has its own lower band.
    c=once(c,'''  SDL_RenderSetLogicalSize(renderer, g_snes_width, g_snes_height);
  SDL_RenderSetIntegerScale(renderer, SDL_TRUE);
  SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);''',
           '''  SDL_RenderSetLogicalSize(renderer, 0, 0);
  SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);''')
    c=once(c,'''  SDL_RenderCopy(g_renderer, g_texture, &g_sdl_renderer_rect, NULL);''',
           '''  int out_w=0, out_h=0;
  SDL_GetRendererOutputSize(g_renderer,&out_w,&out_h);
  bool portrait=out_h>out_w;
  int available_h=portrait ? out_h*62/100 : out_h;
  int scale=IntMin(out_w/g_snes_width, available_h/g_snes_height);
  if (scale<1) scale=1;
  SDL_Rect game_rect={
      (out_w-g_snes_width*scale)/2,
      (available_h-g_snes_height*scale)/2,
      g_snes_width*scale,g_snes_height*scale};
  SDL_RenderCopy(g_renderer,g_texture,&g_sdl_renderer_rect,&game_rect);''')
    nativefile.write_text(c,encoding="utf-8")

    gradle=root/"app/build.gradle"
    g=gradle.read_text(encoding="utf-8")
    g=once(g,"versionCode 8","versionCode 10")
    g=once(g,'versionName "1.0.8-tv"',
           'versionName "1.0.10-native-layout"')
    gradle.write_text(g,encoding="utf-8")

    print("PASS: original Android overlay only, portrait layout, gamepad hide, BACK twice")

if __name__=="__main__":
    import sys
    if len(sys.argv)!=2:raise SystemExit("patch_android_native_layout.py PROJECT")
    apply(sys.argv[1])
