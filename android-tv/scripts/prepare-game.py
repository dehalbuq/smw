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
    cfile.write_text(content, encoding="utf-8")
    shutil.copy2(port / "android-tv/app/src/main/cpp/android_entry.c",
                 source / "src/port/android_entry.c")

    # Native app owns Android files and frontend. If it later exposes game mods,
    # do so through a TV-compatible selector rather than a touch overlay.
    assert (source / "src/port/gles2_renderer.c").exists()
    print("PASS SMW_ANDROID_TV_SHARED_LIB_GLES2_PREPARED")

if __name__ == "__main__":
    main()
