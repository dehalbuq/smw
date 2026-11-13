# Super Mario World Recomp — Android TV experimental (ARM64)

Android TV port of the SAME mstan/SuperMarioWorldRecomp engine used by our
verified R36S dArkOSRE build. This is **native Android NDK** (not the Linux
R36S ELF repackaged).

Features planned for private APK:
- Android TV/Google TV launcher (LEANBACK_LAUNCHER), also visible on phones;
- landscape and immersive fullscreen, screen ratio 16:9 with native adaptive
  widescreen render (not artificially stretched 4:3 video);
- USB/Bluetooth gamepad and TV remote through SDL2, **no touch overlay**;
- GLES2 and SDL2 native ARM64, persistent saves in internal app storage;
- a private ROM asset bundled only into the owner's PRIVATE CI artifact.

ROM note: ROM belongs exclusively in the user-owned PRIVATE repo
`dehalbuq/smw-rom-private` and the privately generated APK. Never publish
an APK containing copyrighted game ROMs publicly. The CI copies it into
the APK assets for PERSONAL testing. The code repo is ROM-free.

Android API min: 21 (Android 5.0); target TV ARM64 first. ARMv7 32-bit can be
added once the arm64 build runs on real Android and native ABI compatibility
is established.

The launch bridge copies the private ROM to the app-internal directory on first
run, enables adaptive 16:9 via SMW_RENDER_ASPECT=16:9, and invokes the original
SMW engine directly without a desktop file picker. Some SNES title/transition
scenes remain native 4:3 by engine design.

**STATUS:** work in progress; APK must compile AND be tested on a real Android
TV before claiming working graphics, gamepad, audio, and saves.
Check GitHub Actions private workflow:
https://github.com/dehalbuq/smw-rom-private/actions

Local diagnostics: Android `adb logcat -d -s SDL AndroidRuntime` and
`adb shell dumpsys package com.dehalbuq.smwrecomp`.
