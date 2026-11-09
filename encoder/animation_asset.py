"""GLF1 animated RGB332 assets composed of timed GLI1 frames."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct,zlib
try:from .image_asset import build as build_image,rgb332,parse as parse_image
except ImportError:from image_asset import build as build_image,rgb332,parse as parse_image
MAGIC=b'GLF1';VERSION=1;HEADER_SIZE=36;HEADER=struct.Struct('<4sHHHHHHIIIII');INDEX=struct.Struct('<HHII')
@dataclass
class Frame:duration_vblanks:int;image:bytes

def build(frames:list[Frame],width=240,height=160,loop_count=0)->bytes:
 if not frames or len(frames)>65535:raise ValueError('GLF1 frame count')
 index_off=HEADER_SIZE;data_off=index_off+len(frames)*INDEX.size;payload=bytearray();cache={};records=[]
 for f in frames:
  if f.image in cache:off,n=cache[f.image]
  else:off=data_off+len(payload);n=len(f.image);payload+=f.image;cache[f.image]=(off,n)
  records.append(INDEX.pack(max(1,min(65535,f.duration_vblanks)),0,off,n))
 total=data_off+len(payload);head=bytearray(HEADER.pack(MAGIC,VERSION,HEADER_SIZE,width,height,len(frames),0,loop_count,index_off,data_off,total,0));blob=head+b''.join(records)+payload;struct.pack_into('<I',blob,32,zlib.crc32(blob)&0xffffffff);return bytes(blob)
def parse(blob:bytes)->dict:
 if len(blob)<HEADER_SIZE:raise ValueError('short GLF1')
 magic,ver,hs,w,h,count,flags,loops,io,do,total,crc=HEADER.unpack_from(blob)
 if magic!=MAGIC or ver!=VERSION or hs!=HEADER_SIZE or total>len(blob):raise ValueError('bad GLF1')
 tmp=bytearray(blob[:total]);struct.pack_into('<I',tmp,32,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLF1 CRC')
 frames=[]
 for i in range(count):
  dur,ff,off,n=INDEX.unpack_from(blob,io+i*INDEX.size)
  if off+n>total:raise ValueError('GLF1 frame outside asset')
  parse_image(blob[off:off+n]);frames.append({'duration_vblanks':dur,'offset':off,'size':n,'image':blob[off:off+n]})
 return {'width':w,'height':h,'loop_count':loops,'flags':flags,'frames':frames,'total_size':total,'crc32':crc}
def compile_gif(path:str|Path,fps=4,max_seconds=10,fit='cover')->bytes:
 from PIL import Image,ImageSequence
 im=Image.open(path);source=[];time=0.0
 for fr in ImageSequence.Iterator(im):
  duration=max(.01,float(fr.info.get('duration',im.info.get('duration',100)))/1000);source.append((time,time+duration,fr.convert('RGB').copy()));time+=duration
 if not source:raise ValueError('GIF has no frames')
 limit=min(time,max_seconds) if max_seconds>0 else time;step=1/max(1,min(10,fps));frames=[];t=0.0;last=None
 def fit_image(src):
  w,h=src.size
  if fit=='stretch':return src.resize((240,160),Image.Resampling.LANCZOS if hasattr(Image,'Resampling') else Image.LANCZOS)
  scale=max(240/w,160/h) if fit=='cover' else min(240/w,160/h);nw,nh=max(1,round(w*scale)),max(1,round(h*scale));r=src.resize((nw,nh),Image.Resampling.LANCZOS if hasattr(Image,'Resampling') else Image.LANCZOS)
  if fit=='cover':return r.crop(((nw-240)//2,(nh-160)//2,(nw-240)//2+240,(nh-160)//2+160))
  out=Image.new('RGB',(240,160));out.paste(r,((240-nw)//2,(160-nh)//2));return out
 while t<limit-1e-6:
  src=next((fr for a,b,fr in source if a<=t<b),source[-1][2]);asset=build_image(rgb332(fit_image(src).tobytes()))
  if frames and asset==last:frames[-1].duration_vblanks+=round(step*60)
  else:frames.append(Frame(max(1,round(step*60)),asset));last=asset
  t+=step
 return build(frames,loop_count=0)
