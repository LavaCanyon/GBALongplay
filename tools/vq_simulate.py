#!/usr/bin/env python3
"""Same-budget temporal simulation of a persistent 4x4 VQ update mode."""
from pathlib import Path
import argparse,json,sys,struct,zlib,binascii,numpy as np
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'encoder'))
from vq_train import load_frames,split_patches,palette_rgb,W,H
from container import read
from glp_codec import Decoder
from rate_control import RateController

def write_png(path,idx):
 rgb=palette_rgb(idx).clip(0,255).astype(np.uint8)
 def ch(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',binascii.crc32(t+d)&0xffffffff)
 scan=b''.join(b'\0'+rgb[y].tobytes() for y in range(H));path.write_bytes(b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+ch(b'IDAT',zlib.compress(scan,9))+ch(b'IEND',b''))
def main():
 p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('codebook');p.add_argument('baseline_glv');p.add_argument('-o','--output',required=True);p.add_argument('--video-bytes',type=int,required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 frames=load_frames(a.input,10);sp=split_patches(frames);flat=sp.reshape(-1,16);book=np.frombuffer(Path(a.codebook).read_bytes(),np.uint8).reshape(256,16)
 centers=palette_rgb(book).reshape(256,48);cn=(centers*centers).sum(1);labels=np.empty(len(flat),np.uint8)
 for st in range(0,len(flat),4096):
  x=palette_rgb(flat[st:st+4096]).reshape(-1,48);d=(x*x).sum(1)[:,None]+cn[None,:]-2*x@centers.T;labels[st:st+len(x)]=d.argmin(1)
 approx=book[labels].reshape(sp.shape);previous=np.zeros_like(sp[0]);rc=RateController((a.video_bytes-4096)/len(frames));total=4096;stale=[];vq_frames=[];last_key=-999
 for fi in range(len(frames)):
  src=sp[fi];ap=approx[fi];src_rgb=palette_rgb(src);old_rgb=palette_rgb(previous);ap_rgb=palette_rgb(ap)
  olderr=((src_rgb-old_rgb)**2).sum((1,2));newerr=((src_rgb-ap_rgb)**2).sum((1,2));gain=olderr-newerr
  # Scene cuts use full VQ refresh; otherwise select highest-value patches with grouped record cost.
  score=999 if fi==0 else np.mean(np.abs(palette_rgb(frames[fi])-palette_rgb(frames[fi-1])))
  key=fi==0 or (score>=48 and fi-last_key>=8) or fi-last_key>=240
  rec=previous.copy();budget=rc.budget();cost=16+75
  if key:
   rec=ap.copy();cost=16+75+600*6;last_key=fi
  else:
   order=np.argsort(gain)[::-1];blocks=set();selected=[]
   for pi in order:
    if gain[pi]<=0:break
    py,px=divmod(int(pi),60);block=(py//2)*30+(px//2);extra=1 if block in blocks else 3
    if cost+extra>budget:continue
    cost+=extra;blocks.add(block);selected.append(pi)
   if selected:rec[selected]=ap[selected]
  changed=np.any(src!=(sp[fi-1] if fi else 0),axis=1);held=np.all(rec==previous,axis=1)&changed;stale.append(float(np.mean(held)));previous=rec;rc.commit(cost);total+=cost
  if fi%60==0:vq_frames.append((fi,rec.copy()))
 # Baseline objective error.
 dec=Decoder();base=[]
 for pkt in read(a.baseline_glv)['video']:base.append(np.array(dec.decode(pkt.data),np.uint8).reshape(H,W))
 base=np.array(base[:len(frames)]);vq=np.empty_like(frames)
 # Re-run only stored final sequence would be costly; report final and selected previews, objective via a second cheap simulation omitted.
 for fi,rec in vq_frames:
  idx=rec.reshape(H//4,W//4,4,4).transpose(0,2,1,3).reshape(H,W);write_png(out/f'vq-temporal-{fi:06}.png',idx)
 report={'frames':len(frames),'target_video_bytes':a.video_bytes,'estimated_vq_bytes':total,'rate_error_bytes':total-a.video_bytes,'mean_changed_patch_held_percent':100*float(np.mean(stale)),'baseline_video_bytes':sum(len(p.data) for p in read(a.baseline_glv)['video']),'codebook_bytes':4096}
 (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
