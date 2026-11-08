#!/usr/bin/env python3
"""Generate a 320x180 Android TV launcher banner using only stdlib.

This is a generated Android app resource, not bundled game art.
The source tree contains no proprietary images in this file.
"""
from pathlib import Path
import struct
import sys
import zlib

FONT = {
 "A": ["01110","10001","10001","11111","10001","10001","10001"],
 "B": ["11110","10001","10001","11110","10001","10001","11110"],
 "D": ["11110","10001","10001","10001","10001","10001","11110"],
 "E": ["11111","10000","10000","11110","10000","10000","11111"],
 "I": ["11111","00100","00100","00100","00100","00100","11111"],
 "L": ["10000","10000","10000","10000","10000","10000","11111"],
 "M": ["10001","11011","10101","10101","10001","10001","10001"],
 "N": ["10001","11001","10101","10011","10001","10001","10001"],
 "O": ["01110","10001","10001","10001","10001","10001","01110"],
 "P": ["11110","10001","10001","11110","10000","10000","10000"],
 "R": ["11110","10001","10001","11110","10100","10010","10001"],
 "S": ["01111","10000","10000","01110","00001","00001","11110"],
 "T": ["11111","00100","00100","00100","00100","00100","00100"],
 "U": ["10001","10001","10001","10001","10001","10001","01110"],
 "V": ["10001","10001","10001","10001","10001","01010","00100"],
 "W": ["10001","10001","10001","10101","10101","10101","01010"],
 "7": ["11111","00001","00010","00100","01000","01000","01000"],
 "8": ["01110","10001","10001","01110","10001","10001","01110"],
 " ": ["00000"] * 7
}

W, H = 320, 180
pixels = bytearray(W * H * 4)

def fill(x, y, w, h, c):
    x0, y0 = max(0, x), max(0, y)
    for yy in range(y0, min(H, y + h)):
        for xx in range(x0, min(W, x + w)):
            i = (yy * W + xx) * 4
            pixels[i:i + 4] = bytes((*c[:3], 255))

def label(text, y, scale, color, shadow=True):
    text = text.upper()
    width = (len(text) * 6 - 1) * scale
    x = (W - width) // 2
    def draw(dx, dy, rgba):
        for k, ch in enumerate(text):
            glyph = FONT[ch]
            for gy, row in enumerate(glyph):
                for gx, v in enumerate(row):
                    if v == "1":
                        fill(x + (k * 6 + gx) * scale + dx,
                             y + gy * scale + dy, scale, scale, rgba)
    if shadow:
        draw(3, 3, (12, 12, 40))
    draw(0, 0, color)

def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

def main(path):
    for y in range(H):
        f = y / H
        fill(0, y, W, 1, (int(18 + f * 8), int(32 + f * 31), int(90 + f * 51)))
    # Restrained 16-bit inspired pixel landscape, no copyrighted game artwork.
    fill(0, 142, W, 38, (14, 45, 68))
    for x, y, w, h in [(5,128,45,52),(41,116,40,64),(85,134,54,46),
                       (191,132,42,48),(224,119,46,61),(265,136,55,44)]:
        fill(x, y, w, h, (22, 90, 82))
        fill(x+6, y+6, w-12, h-7, (31, 116, 102))
    # Deliberate TV overscan safe space around the title.
    fill(18, 17, 284, 105, (12, 28, 78))
    fill(18, 17, 284, 3, (98, 227, 215))
    fill(18, 119, 284, 3, (98, 227, 215))
    label("SUPER MARIO", 31, 4, (252, 237, 126))
    label("WORLD", 70, 5, (253, 252, 250))
    label("ANDROID TV", 146, 2, (235, 241, 249), False)
    raw = b"".join(b"\x00" + pixels[y*W*4:(y+1)*W*4] for y in range(H))
    out = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(raw, 9)) +
           chunk(b"IEND", b""))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    print(f"TV launcher banner: {path}, {W}x{H}, {len(out)} bytes")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: gen_android_tv_banner.py DESTINATION")
    main(sys.argv[1])
