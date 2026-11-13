#!/usr/bin/env python3
"""Compile all real non-ROM-generated SuperMarioWorld Android host objects.

This is NOT a playable game build. src/gen/*.c generated from the owner's
private ROM is deliberately excluded. CMake must already be configured.
"""
import concurrent.futures
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time


def compile_one(job):
    src, row, out = job
    cmd = row.get("arguments") or shlex.split(row["command"])
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(cmd, cwd=row["directory"], capture_output=True,
                       text=True, errors="replace", timeout=180)
    ok = p.returncode == 0 and out.is_file()
    return (src, ok, p.stderr[-4500:] if not ok else "")


def main():
    if len(sys.argv) != 2:
        print("Usage: compile-all-host-objects.py build-dir", file=sys.stderr)
        return 2
    build = Path(sys.argv[1]).resolve()
    rows = json.loads((build / "compile_commands.json").read_text("utf-8"))
    jobs = []
    for row in rows:
        raw = row.get("command", "") + " " + " ".join(row.get("arguments", []))
        if "SuperMarioWorldSNESRecomp.dir" not in raw:
            continue
        src = row["file"].replace("\\", "/")
        if "/src/gen/" in src or "/src/gen-coop/" in src:
            continue
        cmd = row.get("arguments") or shlex.split(row["command"])
        if "-o" not in cmd:
            raise SystemExit("Compile command lacking -o for " + src)
        output = Path(cmd[cmd.index("-o") + 1])
        if not output.is_absolute():
            output = Path(row["directory"]) / output
        jobs.append((src, row, output))
    if len(jobs) < 60:
        raise SystemExit(f"FAIL: expected >60 host units, found {len(jobs)}")
    print(f"Android native host objects to compile: {len(jobs)}", flush=True)
    max_workers = min(int(os.environ.get("JOBS", "4")), 8)
    errors = []
    total = 0
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        for src, ok, err in ex.map(compile_one, jobs):
            total += 1
            if not ok:
                errors.append((src, err))
                print(f"FAIL [{total}/{len(jobs)}] {src}\n{err}", flush=True)
            elif total % 25 == 0:
                print(f"PASS {total}/{len(jobs)} host objects", flush=True)
    print(f"Host objects: total={len(jobs)}, passed={len(jobs)-len(errors)}, errors={len(errors)}, seconds={time.monotonic()-started:.1f}", flush=True)
    if errors:
        return 1
    print("PASS ALL_ANDROID_SMW_HOST_OBJECTS_NO_ROM", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
