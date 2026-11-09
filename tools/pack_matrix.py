#!/usr/bin/env python3
"""Pack a 64 MiB Matrix-compatible GBA image with a high-bank payload."""
from pathlib import Path
import argparse
SIZE=64*1024*1024;PAYLOAD_OFFSET=32*1024*1024
def main():
 p=argparse.ArgumentParser();p.add_argument('boot');p.add_argument('payload');p.add_argument('-o','--output',required=True);a=p.parse_args()
 boot=Path(a.boot).read_bytes();payload=Path(a.payload).read_bytes()
 if len(boot)>PAYLOAD_OFFSET:raise SystemExit('bootstrap overlaps payload')
 if PAYLOAD_OFFSET+len(payload)>SIZE:raise SystemExit('payload exceeds Matrix image')
 image=bytearray(b'\xff')*SIZE;image[:len(boot)]=boot;image[PAYLOAD_OFFSET:PAYLOAD_OFFSET+len(payload)]=payload
 image[0xAC]=ord('M');Path(a.output).write_bytes(image)
 print(f'wrote {a.output}: {len(image)} bytes; payload at 0x{PAYLOAD_OFFSET:08x}')
if __name__=='__main__':main()
