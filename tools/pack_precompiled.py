#!/usr/bin/env python3
"""Create a Matrix64 ROM from a GLA1 album and precompiled player template."""
from pathlib import Path
import argparse,hashlib,json,sys
SIZE=64*1024*1024
p=argparse.ArgumentParser();p.add_argument('album');p.add_argument('-o','--output',required=True);p.add_argument('--template',default=str(Path(__file__).parents[1]/'converter/templates'));a=p.parse_args();t=Path(a.template);meta=json.loads((t/'matrix64-template.json').read_text());boot=(t/'matrix64-boot.gba').read_bytes();runtime=(t/'matrix64-runtime.bin').read_bytes();album=Path(a.album).read_bytes();off=meta['album_offset'];ro=meta['runtime_offset']
for name,data in [('matrix64-boot.gba',boot),('matrix64-runtime.bin',runtime)]:
 if hashlib.sha256(data).hexdigest()!=meta['sha256'][name]:raise SystemExit(f'template checksum failed: {name}')
if len(album)>SIZE-off:raise SystemExit(f'album is {len(album)-(SIZE-off)} bytes over capacity')
image=bytearray(b'\xff')*SIZE;image[:len(boot)]=boot;image[ro:ro+len(runtime)]=runtime;image[off:off+len(album)]=album;image[0xac]=ord('M');Path(a.output).write_bytes(image)
print(json.dumps({'output':a.output,'rom_bytes':len(image),'album_bytes':len(album),'free_bytes':SIZE-off-len(album),'album_offset':off},indent=2))
