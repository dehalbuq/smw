#!/usr/bin/env python3
"""Compile real ARM64 host engine translation units without game-generated CPU C.

Uses the exact target flags from the CMake preflight. No ROM, linking or game
binary is involved; this catches ABI/header/backend integration breakage.
"""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import subprocess
import sys

WANTED = [
    "src/port/gles2_renderer.c",
    "src/main.c",
    "src/config.c",
    "src/smw_video.c",
    "src/smw_renderer.c",
    "src/smw_renderer_hooks.c",
    "src/smw_netplay_lobby.c",
    "src/foreign_controller.c",
    "src/smw_replay.c",
    "src/mod_external_rom_compat.c",
    "src/smw_spc_player.c",
    "src/mods/coop/coop_runtime.c",
    "src/mods/coop/coop_simulation.c",
    "src/mods/falcon/falcon_locomotion.c",
    "src/mods/falcon/smw_falcon_audio.c",
]

def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: compile_host_objects.py /path/to/CMake-build", file=sys.stderr)
        return 2
    build = Path(sys.argv[1]).resolve()
    entries = json.loads((build / "compile_commands.json").read_text(encoding="utf-8"))
    selected: dict[str, dict] = {}
    for file in WANTED:
        matching = [
            row for row in entries
            if row["file"].replace("\\", "/").endswith("/" + file)
            and "SuperMarioWorldSNESRecomp.dir" in
            (row.get("command", "") + " ".join(row.get("arguments", [])))
        ]
        if len(matching) != 1:
            print(f"FAIL object target: {file} => {len(matching)} matches", file=sys.stderr)
            return 1
        selected[file] = matching[0]

    for index, (file, row) in enumerate(selected.items(), start=1):
        args = row.get("arguments") or shlex.split(row["command"])
        if "-c" not in args:
            print("FAIL missing compiler -c flag: " + file, file=sys.stderr)
            return 1
        if "-o" not in args:
            print("FAIL missing -o compiler output: " + file, file=sys.stderr)
            return 1
        out = Path(args[args.index("-o") + 1])
        if not out.is_absolute():
            out = Path(row["directory"]) / out
        out.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{index:02d}/{len(selected)}] AArch64 host compile {file}", flush=True)
        proc = subprocess.run(args, cwd=row["directory"], check=False, timeout=180)
        if proc.returncode:
            print(f"FAIL SMW_ARM64_HOST_OBJECTS: {file} (compiler exit {proc.returncode})", file=sys.stderr)
            return 1
        if not out.exists():
            print(f"FAIL object missing: {out}", file=sys.stderr)
            return 1

    print(f"PASS SMW_ARM64_HOST_OBJECTS: {len(selected)} real host translation units")
    print("NOTE: no ROM, no generated CPU C, no executable linking")
    return 0


if __name__ == "__main__":
    sys.exit(main())
