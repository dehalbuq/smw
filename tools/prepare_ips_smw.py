#!/usr/bin/env python3
"""Inspect/apply IPS patches locally to a user-owned SMW ROM. Never patch assets.dat."""
import argparse
import hashlib
from pathlib import Path

KNOWN_SHA1="6B47BB75D16514B6A476AA0C73A683A2A4C18765"

def read_ips(filename):
    data=Path(filename).read_bytes()
    if not data.startswith(b"PATCH"):
        raise ValueError("not an IPS patch (missing PATCH magic)")
    items=[];i=5;max_end=0
    while True:
        if i+3>len(data):raise ValueError("IPS missing EOF")
        hdr=data[i:i+3];i+=3
        if hdr==b"EOF":break
        if i+2>len(data):raise ValueError("IPS truncated record")
        size=int.from_bytes(data[i:i+2],"big");i+=2
        off=int.from_bytes(hdr,"big")
        if size:
            if i+size>len(data):raise ValueError("IPS truncated data")
            val=data[i:i+size];i+=size
        else:
            if i+3>len(data):raise ValueError("IPS truncated RLE")
            n=int.from_bytes(data[i:i+2],"big");v=data[i+2];i+=3
            if not n:raise ValueError("zero-length IPS record")
            val=bytes([v])*n
        if off+len(val)>16*1024*1024:
            raise ValueError("oversized IPS write (>16MiB), refusing")
        max_end=max(max_end,off+len(val))
        items.append((off,val))
    if len(data)-i not in (0,3):
        raise ValueError("unexpected bytes after IPS EOF")
    return items,max_end

def main():
    ap=argparse.ArgumentParser(description="Inspect/apply user-provided SMW IPS locally")
    ap.add_argument("--ips",required=True,help="Your own .ips file")
    ap.add_argument("--inspect",action="store_true",help="Only validate and describe IPS")
    ap.add_argument("--rom",help="Your legally obtained, unmodified US SMW ROM")
    ap.add_argument("--output",help="Output patched ROM .smc; never overwrites source")
    ap.add_argument("--ips-headered",action="store_true",
                    help="IPS offsets are for a 512-byte copier-header ROM (PT-BR patch)")
    ap.add_argument("--allow-unknown-base",action="store_true",
                    help="Allow unverified source ROM (may corrupt data)")
    a=ap.parse_args()
    records,max_end=read_ips(a.ips)
    count=sum(len(x[1]) for x in records)
    print(f"Valid IPS: {len(records)} records, {count} written bytes, end=0x{max_end:X}")
    if a.inspect:return
    if not (a.rom and a.output):ap.error("--rom and --output are both required")
    src=Path(a.rom).resolve()
    dst=Path(a.output).resolve()
    if src==dst or dst.exists():
        raise SystemExit("Refusing to overwrite original ROM or existing output file")
    raw=src.read_bytes()
    base=raw[512:] if len(raw)%1024==512 else raw
    digest=hashlib.sha1(base).hexdigest().upper()
    print("Unheadered original ROM SHA1:",digest)
    if digest!=KNOWN_SHA1 and not a.allow_unknown_base:
        raise SystemExit("Source is not verified SMW USA ROM; no patch applied. "
                         "Use --allow-unknown-base only after verifying IPS target.")
    output=bytearray(raw)
    if a.ips_headered:
        if len(raw)%1024 != 512:output=bytearray(512)+output
    elif len(raw)%1024==512:
        output=output[512:]
    if max_end>len(output):output.extend(b"\x00"*(max_end-len(output)))
    for off,data in records:output[off:off+len(data)]=data
    dst.write_bytes(output)
    print(f"Patched ROM created locally: {dst.name} ({len(output)} bytes)")
    print("NEXT: python3 assets/restool.py -r",str(dst),"-f --no-include-rom")
    print("WARNING: extracted assets may not support custom ASM translation or sprites.")

if __name__=="__main__":
    main()
