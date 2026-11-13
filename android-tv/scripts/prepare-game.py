#!/usr/bin/env python3
"""Prepare PINNED SNESRecomp SMW for Android shared-library SDL2 build.

Run AFTER the same EmuELEC GLES2 overlay as the working R36S port.
Only modifies a disposable checkout, never commits generated ROM code.
"""
from pathlib import Path
import argparse
import shutil

def replace_once(text: str, old: str, new: str, where: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"FAIL Android preparation {where}: anchor count {n}")
    return text.replace(old, new, 1)

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--port", required=True, type=Path)
    args = ap.parse_args()
    source = args.source.resolve()
    port = args.port.resolve()
    cfile = source / "CMakeLists.txt"
    content = cfile.read_text(encoding="utf-8")
    before = """function(smw_add_recomp_target target_name generated_sources)
    add_executable(${target_name}
        ${SMW_RUNTIME_SOURCES}
        ${generated_sources}
    )
"""
    after = """function(smw_add_recomp_target target_name generated_sources)
    if(ANDROID)
        add_library(${target_name} SHARED
            ${SMW_RUNTIME_SOURCES}
            ${generated_sources}
            src/port/android_entry.c
        )
    else()
        add_executable(${target_name}
            ${SMW_RUNTIME_SOURCES}
            ${generated_sources}
        )
    endif()
"""
    content = replace_once(content, before, after, "native main shared library")
    # Original engine uses CMAKE_SOURCE_DIR extensively for its pinned
    # submodules and game files. Configure game as TOP-LEVEL rather than
    # add_subdirectory() from the Android wrapper; create SDL2 target first.
    project_old = "project(SuperMarioWorldSNESRecomp C)"
    project_new = """project(SuperMarioWorldSNESRecomp C)
if(ANDROID)
    if(NOT EXISTS "$ENV{SMW_ANDROID_SDL2}/CMakeLists.txt")
        message(FATAL_ERROR "SMW_ANDROID_SDL2 must identify SDL2 Android source")
    endif()
    set(SDL_SHARED ON CACHE BOOL "" FORCE)
    set(SDL_STATIC OFF CACHE BOOL "" FORCE)
    set(SDL_TEST OFF CACHE BOOL "" FORCE)
    set(SDL_TESTS OFF CACHE BOOL "" FORCE)
    set(SDL_INSTALL OFF CACHE BOOL "" FORCE)
    add_subdirectory("$ENV{SMW_ANDROID_SDL2}" "${CMAKE_BINARY_DIR}/android-sdl2")
    list(PREPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
endif()"""
    content = replace_once(content, project_old, project_new, "SDL2 bootstrap")

    target_anchor = """smw_add_recomp_target(SuperMarioWorldSNESRecomp
    "${SMW_STOCK_GEN_SOURCES}")"""
    target_new = target_anchor + """
if(ANDROID)
    set_target_properties(SuperMarioWorldSNESRecomp PROPERTIES OUTPUT_NAME main)
    target_link_libraries(SuperMarioWorldSNESRecomp PRIVATE android log EGL GLESv2)
    target_include_directories(SuperMarioWorldSNESRecomp PRIVATE "$ENV{SMW_ANDROID_SDL2}/include")
endif()"""
    content = replace_once(content, target_anchor, target_new, "JNI target name")

    # Android TV is offline-only. Stock upstream forces recomp-net/
    # retcomm-rbengine even when SNESRECOMP_ENABLE_NET=OFF.
    # Bionic does not expose getifaddrs/freeifaddrs until API 24; our
    # minimum API 21 needs to avoid recomp-net entirely.
    net_call = "snesrecomp_enable_recomp_net(SuperMarioWorldSNESRecomp)"
    content = replace_once(
        content, net_call,
        "if(NOT ANDROID)" + chr(10) + "  " + net_call + chr(10) + "endif()",
        "disable desktop netcode on Android API 21"
    )


    # The bundled SDL2 defines SDL2::SDL2 target but does not install
    # a package config during the same CMake configure invocation.
    # Make find_package(SDL2) reuse that target without host libraries.
    moddir = source / "cmake"
    moddir.mkdir(exist_ok=True)
    findmod = moddir / "FindSDL2.cmake"
    if findmod.exists():
        raise SystemExit("FAIL: original source already contains FindSDL2.cmake")
    findmod.write_text("""if(NOT TARGET SDL2::SDL2)
  message(FATAL_ERROR "Android SDL2 native target was not created")
endif()
set(SDL2_FOUND TRUE)
""", encoding="utf-8")

    # On Android /proc/self/exe identifies app_process in /system/bin,
    # not the APK native library. Anchor configs/saves to the private app
    # directory provided by our JNI entry via HOME, preserving save writes.
    host_paths = source / "snesrecomp/runner/src/host_paths.c"
    hp = host_paths.read_text(encoding="utf-8")
    hp = replace_once(
        hp,
        "#elif defined(__linux__)\n",
        """#elif defined(__ANDROID__)
    const char *app_data = getenv("HOME");
    if (!app_data || !*app_data)
        return 0;
    return snprintf(out, max_len, "%s/SMWRecompAndroidTV", app_data) < (int)max_len;
#elif defined(__linux__)
""",
        "Android private storage for config/saves",
    )
    host_paths.write_text(hp, encoding="utf-8")

    # Fullscreen is guaranteed regardless of any imported desktop config.
    # The Android Activity also runs immersive, without a touch overlay.
    game_main = source / "src/main.c"
    game_text = game_main.read_text(encoding="utf-8")
    game_text = replace_once(
        game_text,
        "  // Window scale (1=100%, 2=200%, 3=300%, etc.)",
        """#ifdef __ANDROID__
  g_win_flags |= SDL_WINDOW_FULLSCREEN;
#endif

  // Window scale (1=100%, 2=200%, 3=300%, etc.)""",
        "Android TV forced native fullscreen"
    )
    game_main.write_text(game_text, encoding="utf-8")

    cfile.write_text(content, encoding="utf-8")
    shutil.copy2(port / "android-tv/app/src/main/cpp/android_entry.c",
                 source / "src/port/android_entry.c")

    # Native app owns Android files and frontend. If it later exposes game mods,
    # do so through a TV-compatible selector rather than a touch overlay.
    assert (source / "src/port/gles2_renderer.c").exists()
    print("PASS SMW_ANDROID_TV_SHARED_LIB_GLES2_PREPARED")

if __name__ == "__main__":
    main()
