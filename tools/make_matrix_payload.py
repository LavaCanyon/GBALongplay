#!/usr/bin/env python3
from pathlib import Path
import sys
W,H=240,160
p=bytearray(W*H)
for y in range(H):
 for x in range(W):
  c=((x//30)<<5)|((y//20)<<2)|((x+y)//64&3)
  if 8<x<232 and 8<y<152 and (x in (9,230) or y in (9,150)):c=0xff
  # Central M: two vertical stems and diagonals meeting near the centre.
  diag1=76+(y-66) if 66<=y<=108 else -99
  diag2=163-(y-66) if 66<=y<=108 else -99
  if 65<y<125 and (72<=x<80 or 160<=x<168 or abs(x-diag1)<3 or abs(x-diag2)<3):c=0xff
  p[y*W+x]=c
Path(sys.argv[1] if len(sys.argv)>1 else 'matrix-payload.bin').write_bytes(p)
print(f'wrote {len(p)}-byte Matrix test payload')
