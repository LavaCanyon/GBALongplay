#!/usr/bin/env python3
from pathlib import Path
import argparse,struct,zlib
p=argparse.ArgumentParser();p.add_argument('glv',nargs='+');p.add_argument('--gain',type=float,required=True);a=p.parse_args();q=max(1,min(65535,round(a.gain*256)))
for name in a.glv:
 path=Path(name);data=bytearray(path.read_bytes())
 if data[:4]!=b'GLV2' or len(data)<64:raise SystemExit(f'{name}: not GLV2')
 meta=struct.unpack_from('<I',data,56)[0];struct.pack_into('<I',data,56,(q<<16)|(meta&0xffff));struct.pack_into('<I',data,60,0);struct.pack_into('<I',data,60,zlib.crc32(data)&0xffffffff);path.write_bytes(data);print(f'{name}: gain {q/256:.3f}x')
