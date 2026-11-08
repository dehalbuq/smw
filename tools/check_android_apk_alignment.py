#!/usr/bin/env python3
"""Fail packaging if uncompressed Android native .so files aren't page-aligned.

Android 9 TV can reject APK installation even when apksigner verifies the
signature, if shared libraries extracted directly from the APK aren't aligned
to 4096-byte pages. Check the FINAL signed APK, not just the CI base artifact.

Usage: python3 tools/check_android_apk_alignment.py final_signed.apk
"""
from pathlib import Path
import sys
import struct
import zipfile

if len(sys.argv) != 2:
    sys.exit("usage: check_android_apk_alignment.py final_signed.apk")
apk = Path(sys.argv[1])
count = 0
with zipfile.ZipFile(apk) as z:
    bad = z.testzip()
    if bad:
        raise RuntimeError(f"ZIP corruption: {bad}")
    for item in z.infolist():
        if item.compress_type != zipfile.ZIP_STORED:
            continue
        z.fp.seek(item.header_offset)
        header = z.fp.read(30)
        if len(header) != 30 or header[:4] != b"PK\\x03\\x04":
            raise RuntimeError(f"Bad ZIP local header: {item.filename}")
        namelen, extralen = struct.unpack_from("<HH", header, 26)
        offset = item.header_offset + 30 + namelen + extralen
        is_lib = item.filename.startswith("lib/") and item.filename.endswith(".so")
        alignment = 4096 if is_lib else 4
        if offset % alignment:
            raise RuntimeError(
                f"INVALID APK: {item.filename} starts at {offset}; "
                f"requires {alignment}-byte alignment (found {offset % alignment})")
        if is_lib:
            count += 1
            print(f"4096 OK: {item.filename} at {offset}")
    if not count:
        raise RuntimeError("No uncompressed .so files found")
print(f"PASS: {count} native libraries aligned, stored resources aligned")
