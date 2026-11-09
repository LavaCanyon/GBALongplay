#!/usr/bin/env python3
"""Render full-frame nearest-codebook previews for selected source frames."""
from pathlib import Path
import argparse,struct,zlib,binascii,numpy as np
from vq_train import load_frames,split_patches,palette_rgb,W,H

def png(path,rgb):
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',binascii.crc32(t+d)&0xffffffff)
 scan=b''.join(b'\0'+rgb[y].tobytes() for y in range(H));path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(scan,9))+ch(b'IEND',b''))
def main():
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('codebook');p.add_argument('-o','--output',required=True);p.add_argument('--every',type=int,default=60);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 frames=load_frames(a.input,10);book=np.frombuffer(Path(a.codebook).read_bytes(),np.uint8).reshape(256,16);centers=palette_rgb(book).reshape(256,48);cn=(centers*centers).sum(1)
 for fi in range(0,len(frames),a.every):
  ps=split_patches(frames[fi:fi+1])[0];x=palette_rgb(ps).reshape(-1,48);d=(x*x).sum(1)[:,None]+cn[None,:]-2*x@centers.T;rec=book[d.argmin(1)].reshape(H//4,W//4,4,4).transpose(0,2,1,3).reshape(H,W);rgb=palette_rgb(rec).clip(0,255).astype(np.uint8);png(out/f'vq-{fi:06}.png',rgb)
if __name__=='__main__':main()
