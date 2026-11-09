#!/usr/bin/env python3
"""Train and evaluate a 256-entry 4x4 RGB332 VQ codebook."""
from __future__ import annotations
import argparse,json,shutil,subprocess
from pathlib import Path
import numpy as np
from sklearn.cluster import MiniBatchKMeans
W,H=240,160

def load_frames(path:str,fps:float):
 if not shutil.which('ffmpeg'):raise SystemExit('ffmpeg not found')
 vf=f'scale=trunc(iw*sar/2)*2:ih,setsar=1,scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}'
 raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-an','-vf',vf,'-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE,check=True).stdout
 rgb=np.frombuffer(raw,np.uint8).reshape(-1,H,W,3)
 idx=((rgb[...,0]&0xe0)|((rgb[...,1]&0xe0)>>3)|(rgb[...,2]>>6)).astype(np.uint8)
 return idx

def split_patches(frames):
 n=len(frames);return frames.reshape(n,H//4,4,W//4,4).transpose(0,1,3,2,4).reshape(n,-1,16)

def palette_rgb(idx):
 v=np.asarray(idx,dtype=np.uint8);r=(v>>5).astype(np.float32)*(255/7);g=((v>>2)&7).astype(np.float32)*(255/7);b=(v&3).astype(np.float32)*85
 return np.stack((r,g,b),axis=-1)

def quantize_centers(c):
 p=c.reshape(-1,16,3);r=np.rint(p[...,0]*7/255).clip(0,7).astype(np.uint8);g=np.rint(p[...,1]*7/255).clip(0,7).astype(np.uint8);b=np.rint(p[...,2]*3/255).clip(0,3).astype(np.uint8)
 return ((r<<5)|(g<<2)|b).reshape(-1,16)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('-o','--output',required=True);ap.add_argument('--fps',type=float,default=10);ap.add_argument('--samples',type=int,default=80000);ap.add_argument('--edge-fraction',type=float,default=.5);a=ap.parse_args()
 frames=load_frames(a.input,a.fps);patches=split_patches(frames);flat=patches.reshape(-1,16);rng=np.random.default_rng(0)
 # Reserve part of training for line-rich patches so flat backgrounds do not monopolize the codebook.
 grid=flat.reshape(-1,4,4).astype(np.int16);r=grid>>5;g=(grid>>2)&7;b=grid&3
 edge=(np.abs(np.diff(r,axis=1)).sum((1,2))+np.abs(np.diff(r,axis=2)).sum((1,2))+np.abs(np.diff(g,axis=1)).sum((1,2))+np.abs(np.diff(g,axis=2)).sum((1,2))+2*np.abs(np.diff(b,axis=1)).sum((1,2))+2*np.abs(np.diff(b,axis=2)).sum((1,2)))
 edge_n=min(int(a.samples*a.edge_fraction),len(flat));uniform_n=min(a.samples-edge_n,len(flat));uniform=rng.choice(len(flat),uniform_n,replace=False)
 pool=np.flatnonzero(edge>=np.percentile(edge,70));edge_take=rng.choice(pool,min(edge_n,len(pool)),replace=False);take=np.unique(np.concatenate((uniform,edge_take)))
 train=palette_rgb(flat[take]).reshape(len(take),48)
 km=MiniBatchKMeans(n_clusters=256,batch_size=2048,max_iter=120,n_init=1,random_state=0,reassignment_ratio=.01,verbose=0).fit(train)
 book=quantize_centers(km.cluster_centers_);Path(a.output).write_bytes(book.astype(np.uint8).tobytes())
 # Evaluate all patches against quantized codebook in manageable batches.
 centers=palette_rgb(book).reshape(256,48);cn=(centers*centers).sum(1);errors=np.empty(len(flat),np.float32);labels=np.empty(len(flat),np.uint8)
 for start in range(0,len(flat),4096):
  x=palette_rgb(flat[start:start+4096]).reshape(-1,48);d=(x*x).sum(1)[:,None]+cn[None,:]-2*x@centers.T;lab=d.argmin(1);labels[start:start+len(x)]=lab;errors[start:start+len(x)]=np.sqrt(np.maximum(0,d[np.arange(len(x)),lab]/48))
 changed=np.zeros(patches.shape[:2],bool);changed[1:]=np.any(patches[1:]!=patches[:-1],axis=2);chg=errors[changed.reshape(-1)]
 changed_edge_values=edge[changed.reshape(-1)];edge_cut=np.percentile(changed_edge_values,70);edge_chg=errors[changed.reshape(-1)&(edge>=edge_cut)]
 report={'input':str(a.input),'frames':len(frames),'training_samples':len(take),'edge_training_fraction':a.edge_fraction,'codebook_bytes':len(book.tobytes()),'all_patch_rmse_mean':float(errors.mean()),'changed_patch_rmse_mean':float(chg.mean()),'high_edge_changed_rmse_mean':float(edge_chg.mean()),'changed_patches':int(len(chg))}
 for t in (8,12,16,24,32):report[f'changed_within_{t}_rgb_percent']=float(100*np.mean(chg<=t))
 Path(str(a.output)+'.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
