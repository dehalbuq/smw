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
endif()"""
    content = replace_once(content, target_anchor, target_new, "JNI target name")

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

    cfile.write_text(content, encoding="utf-8")
    shutil.copy2(port / "android-tv/app/src/main/cpp/android_entry.c",
                 source / "src/port/android_entry.c")

    # Native app owns Android files and frontend. If it later exposes game mods,
    # do so through a TV-compatible selector rather than a touch overlay.
    assert (source / "src/port/gles2_renderer.c").exists()
    print("PASS SMW_ANDROID_TV_SHARED_LIB_GLES2_PREPARED")

if __name__ == "__main__":
    main()
