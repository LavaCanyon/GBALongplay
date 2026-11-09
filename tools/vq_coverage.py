#!/usr/bin/env python3
"""Measure exact recurring 4x4 RGB332 patterns for a prospective VQ mode."""
from __future__ import annotations
import argparse,json,shutil,subprocess
from pathlib import Path
import numpy as np
W,H=240,160

def frames(path:str,fps:float)->np.ndarray:
 if not shutil.which('ffmpeg'):raise SystemExit('ffmpeg not found')
 vf=f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}'
 raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-an','-vf',vf,'-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE,check=True).stdout
 rgb=np.frombuffer(raw,dtype=np.uint8).reshape(-1,H,W,3)
 return ((rgb[...,0]&0xe0)|((rgb[...,1]&0xe0)>>3)|(rgb[...,2]>>6)).astype(np.uint8)

def patches(f:np.ndarray)->np.ndarray:
 n=f.shape[0];return f.reshape(n,H//4,4,W//4,4).transpose(0,1,3,2,4).reshape(-1,16)

def main():
 p=argparse.ArgumentParser();p.add_argument('input',nargs='+');p.add_argument('--fps',type=float,default=10);p.add_argument('--codes',type=int,default=256);p.add_argument('-o','--output');a=p.parse_args()
 result={}
 for fn in a.input:
  f=frames(fn,a.fps);ps=patches(f);unique,counts=np.unique(ps,axis=0,return_counts=True);order=np.argsort(counts)[::-1];book=unique[order[:a.codes]]
  keys={row.tobytes() for row in book};matched=sum(1 for row in ps if row.tobytes() in keys)
  # Coverage excluding completely solid patterns indicates reusable line/detail shapes.
  nonsolid=sum(1 for row in book if np.any(row!=row[0]));top_counts=counts[order[:a.codes]]
  frame_patches=ps.reshape(len(f),-1,16);changed=np.any(frame_patches[1:]!=frame_patches[:-1],axis=2)
  matched_grid=np.array([row.tobytes() in keys for row in ps],dtype=bool).reshape(len(f),-1)
  changed_total=int(changed.sum());changed_matched=int((changed&matched_grid[1:]).sum())
  result[Path(fn).name]={'frames':len(f),'patches':len(ps),'unique_patterns':len(unique),'codebook_entries':len(book),'non_solid_entries':nonsolid,'exact_coverage_percent':100*matched/len(ps),'changed_patches':changed_total,'changed_patch_coverage_percent':100*changed_matched/max(1,changed_total),'top_pattern_uses':int(top_counts[0]),'codebook_uses':int(top_counts.sum())}
 print(json.dumps(result,indent=2));
 if a.output:Path(a.output).write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
