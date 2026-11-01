#!/usr/bin/env python3
"""Prepare freyta/smw-android for a distinct ARMv7 build of dehalbuq/smw.
AOSP SDK/NDK build occurs in GitHub Actions, no ROM/assets are packaged.
Android-specific Java, SDL2 and storage/file-loading code are retained.
"""
from pathlib import Path
import shutil, sys, re
if len(sys.argv) != 3:
    sys.exit("usage: port_android_armv7.py ANDROID_PROJECT SMW_FORK")
app=Path(sys.argv[1]).resolve()
fork=Path(sys.argv[2]).resolve()
jni=app/"app/jni/SMW_SRC"
assert (jni/"Android.mk").exists()
assert (fork/"src/smw_00.c").exists()

def rw(path, changes):
    text=path.read_text()
    for old,new in changes:
        if old not in text: raise RuntimeError(f"missing anchor in {path}: {old[:130]!r}")
        text=text.replace(old,new,1)
    path.write_text(text)

# Overwrite only platform-agnostic engine C and core headers.
# Keep Android's main.c, util.c, config.c, and their matching headers as
# these manage Android data directories, SDLActivity and platform controls.
exclude={"main.c","config.c","config.h","util.c","util.h",
         "opengl.c","glsl_shader.c","glsl_shader.h","tracing.c","tracing.h"}
src=fork/"src"
dst=jni/"src"
files=[]
for f in src.glob("*"):
    if f.suffix in (".c",".h") and f.name not in exclude:
        shutil.copy2(f, dst/f.name)
        files.append(f.name)
for f in (src/"snes").glob("*"):
    if f.suffix in (".c",".h"):
        shutil.copy2(f,dst/"snes"/f.name)
# Assets layout matches and user brings the corrected dat, not the ROM.
shutil.copy2(src/"assets/smw_assets.h",dst/"assets/smw_assets.h")
shutil.copy2(src/"assets/smw_assets.c",dst/"assets/smw_assets.c") if (src/"assets/smw_assets.c").exists() else None

# The native C engine avoids running the original ROM interpreter each frame.
cci=dst/"common_cpu_infra.c"
text=cci.read_text()
text,n=re.subn(r"uint8 g_runmode = RM_BOTH;", "uint8 g_runmode = RM_MINE;",text)
if n!=1: raise RuntimeError("couldn't select native SMW engine")
cci.write_text(text)

# Avoid per-frame logging on the Android production build. Android's original
# main.c is kept to preserve Bluetooth controls and app data directory.
mk=jni/"Android.mk"
rw(mk,[("LOCAL_MODULE := main", """LOCAL_MODULE := main
# Generic ARMv7-A target; don't require optional NEON on older devices.
LOCAL_CFLAGS += -O3 -DNDEBUG -fwrapv -fno-strict-aliasing -ffunction-sections -fdata-sections
LOCAL_LDFLAGS += -Wl,--gc-sections
""")])

(jni.parent/"Application.mk").write_text("""APP_ABI := armeabi-v7a
APP_PLATFORM := android-23
APP_STL := c++_shared
APP_OPTIM := release
""")

gradle=app/"app/build.gradle"
g=gradle.read_text()
g=g.replace("abiFilters 'armeabi-v7a', 'arm64-v8a', 'x86', 'x86_64'","abiFilters 'armeabi-v7a'")
g=g.replace("abiFilters 'arm64-v8a'","abiFilters 'armeabi-v7a'")
g=g.replace('arguments "APP_PLATFORM=android-23"', 'arguments "APP_PLATFORM=android-23", "APP_ABI=armeabi-v7a"')
g=g.replace("minSdkVersion 23","minSdkVersion 23")
# NDK pinned for reproducibility on GitHub Ubuntu ARM64 runners
g=g.replace("android {", "android {\n    ndkVersion '25.2.9519653'",1)
# Distinct appId so it does not replace the freyta project on devices.
g=g.replace('applicationId "net.freyta.smw"','applicationId "com.dehalbuq.smw"')
gradle.write_text(g)

# Old upstream launcher can be hardcoded to net.freyta.smw for external dir;
# SDL_AndroidGetExternalStoragePath is tied to applicationId at runtime.
# MainActivity uses its Java package intentionally unchanged to keep SDL
# JNI class/activity references. The APK ID is distinct.
assets=app/"app/src/main/assets/smw.ini"
ini=assets.read_text()
ini=ini.replace("AudioFreq = 44100","AudioFreq = 32000")
ini=ini.replace("AudioSamples = 512","AudioSamples = 1024")
ini=ini.replace("NoSpriteLimits = 1","NoSpriteLimits = 0")
ini=ini.replace("SavePlaythrough = 1","SavePlaythrough = 0")
# SDL accelerated renderer is GLES2-backed on Android, no desktop GL.
ini=ini.replace("#OutputMethod = SDL","OutputMethod = SDL")
assets.write_text(ini)

# No unauthorized game ROMs in installed APK and build outputs.
for p in (jni/"assets/smw.sfc",jni/"src/assets/smw.sfc"):
    if p.exists():p.unlink()

print("Copied",len(files),"SMW core source files to the ARMv7 Android native project")
print("Configured APP_ABI=armeabi-v7a APP_PLATFORM=android-23, GLES2 SDL, gamepad map")
