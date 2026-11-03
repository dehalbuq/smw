#!/usr/bin/env python3
"""Prepare freyta/smw-android for a distinct ARMv7 build of dehalbuq/smw.
AOSP SDK/NDK build occurs in GitHub Actions; private assets are added locally after CI.
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
# The extracted asset IDs are unchanged. Adapt source-relative include for
# the Android project layout (src/assets vs repo-root assets).
asset_header=(fork/"assets/smw_assets.h").read_text()
asset_header=asset_header.replace('#include "../src/types.h"', '#include "../types.h"')
(dst/"assets/smw_assets.h").write_text(asset_header)


# The native C engine avoids running the original ROM interpreter each frame.
cci=dst/"common_cpu_infra.c"
text=cci.read_text()
text,n=re.subn(r"uint8 g_runmode = RM_BOTH;", "uint8 g_runmode = RM_MINE;",text)
if n!=1: raise RuntimeError("couldn't select native SMW engine")
# This Android package runs native-only SMW: SMB1/SMBLL are deliberately
# absent from the Android.mk library target. Eliminate unreachable alternate
# game selections so the link does not require their GameInfo structs.
for unused in ("kSmb1GameInfo", "kSmbllGameInfo"):
    text=text.replace("&"+unused, "&kSmwGameInfo")
cci.write_text(text)

# Avoid per-frame logging on the Android production build. Android's original
# main.c is kept to preserve Bluetooth controls and app data directory.
mk=jni/"Android.mk"
rw(mk,[("LOCAL_MODULE := main", """LOCAL_MODULE := main
# Generic ARMv7-A target; don't require optional NEON on older devices.
LOCAL_CFLAGS += -O2 -DNDEBUG -g0 -fwrapv -fno-strict-aliasing -ffunction-sections -fdata-sections
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

# The personal-use APK bundles smw_assets.dat in Android APK assets.
# Android's game engine reads the copied file from app-specific storage.
# No broad storage permissions are needed for getExternalFilesDir().
activity=app/"app/src/main/java/net/freyta/smw/MainActivity.java"
j=activity.read_text()
old="""        if (hasStoragePermission()) {
            setupFiles();
        } else {
            requestStoragePermission();
        }"""
if old not in j: raise RuntimeError("MainActivity setup anchor missing")
# Stage game data BEFORE SDLActivity.onCreate starts the native game thread.
j=j.replace(old,"",1)
old_oncreate="        super.onCreate(savedInstanceState);"
if old_oncreate not in j: raise RuntimeError("MainActivity onCreate anchor missing")
j=j.replace(old_oncreate,"        setupFiles();\n        super.onCreate(savedInstanceState);",1)
# setupFiles() used to add overlay itself (twice!). Keep it only in onCreate.
overlay_anchor="""        inflateOverlay();
    }
    public void inflateOverlay()"""
if overlay_anchor not in j: raise RuntimeError("overlay anchor missing")
j=j.replace(overlay_anchor,"""    }
    public void inflateOverlay()""",1)
j=j.replace('                // File smwAssets = new File(externalDir, "smw_assets.dat");',
            '                File smwAssets = new File(externalDir, "smw_assets.dat");',1)
start=j.index('                    // Copy the smw_assets.dat to the external dir')
end=j.index('\n                } catch (IOException e)',start) + 1
j=j[:start]+"""                    // Install bundled game data on the first launch.
                    if (!smwAssets.isFile() || smwAssets.length() == 0) {
                        InputStream inputStream = getAssets().open("smw_assets.dat");
                        writeDataToFile(smwAssets, inputStream);
                    }

"""+j[end:]
activity.write_text(j)
manifest=app/"app/src/main/AndroidManifest.xml"
m=manifest.read_text()
m=m.replace('android:allowBackup="true"','android:allowBackup="false"')
# App-specific storage on Android 6+ does not require broad filesystem access.
m=re.sub(r'(?m)^\s*<uses-permission android:name="android.permission.(?:WRITE_EXTERNAL_STORAGE|READ_EXTERNAL_STORAGE|MANAGE_EXTERNAL_STORAGE)"\s*/>\s*\n','',m)
manifest.write_text(m)
# Prevent creating a debuggable or multi-ABI APK, and keep game assets uncompressed.
gradle=app/"app/build.gradle"
g=gradle.read_text()
g=g.replace('release {\n            minifyEnabled false','release {\n            debuggable false\n            jniDebuggable false\n            minifyEnabled false',1)
gradle.write_text(g)

# No unauthorized game ROMs in installed APK and build outputs.
for p in (jni/"assets/smw.sfc",jni/"src/assets/smw.sfc"):
    if p.exists():p.unlink()

from patch_android_projector import apply as patch_projector
patch_projector(app)

print("Copied",len(files),"SMW core source files to the ARMv7 Android native project")
print("Configured APP_ABI=armeabi-v7a APP_PLATFORM=android-23, GLES2 SDL, gamepad map")
