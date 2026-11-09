#!/usr/bin/env python3
from pathlib import Path
import argparse
SIZE=64*1024*1024;RUNTIME_OFFSET=0x20000
def main():
 p=argparse.ArgumentParser();p.add_argument('boot');p.add_argument('runtime');p.add_argument('album');p.add_argument('--album-offset',type=lambda x:int(x,0),default=0x80000);p.add_argument('-o','--output',required=True);a=p.parse_args();album_offset=a.album_offset
 boot=Path(a.boot).read_bytes();runtime=Path(a.runtime).read_bytes();album=Path(a.album).read_bytes()
 if len(boot)>RUNTIME_OFFSET or RUNTIME_OFFSET+len(runtime)>album_offset:raise SystemExit('low-ROM regions overlap')
 if album_offset+len(album)>SIZE:raise SystemExit('album exceeds 64 MiB image')
 image=bytearray(b'\xff')*SIZE;image[:len(boot)]=boot;image[RUNTIME_OFFSET:RUNTIME_OFFSET+len(runtime)]=runtime;image[album_offset:album_offset+len(album)]=album
 image[0xAC]=ord('M');Path(a.output).write_bytes(image)
 print(f'wrote {a.output}: runtime {len(runtime)} bytes at 0x{RUNTIME_OFFSET:x}, album {len(album)} bytes at 0x{album_offset:x}')
if __name__=='__main__':main()
