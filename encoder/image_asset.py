"""GLI1 full-screen/static RGB332 image assets with row-aware PackBits RLE."""
from __future__ import annotations
import struct,zlib
from pathlib import Path
MAGIC=b'GLI1';VERSION=1;HEADER_SIZE=28
RAW=0;RLE8=1;SOLID=2
HEADER=struct.Struct('<4sHHHHBBHIII')

def rgb332(rgb:bytes)->bytes:
 if len(rgb)%3:raise ValueError('RGB24 length')
 out=bytearray(len(rgb)//3)
 for i in range(len(out)):
  r,g,b=rgb[i*3:i*3+3];out[i]=((r*7+127)//255<<5)|((g*7+127)//255<<2)|((b*3+127)//255)
 return bytes(out)
def encode_row(row:bytes)->bytes:
 out=bytearray();i=0
 while i<len(row):
  run=1
  while i+run<len(row) and row[i+run]==row[i] and run<128:run+=1
  if run>=3:out+=bytes((0x80|(run-1),row[i]));i+=run;continue
  start=i;i+=run
  while i<len(row) and i-start<128:
   r=1
   while i+r<len(row) and row[i+r]==row[i] and r<128:r+=1
   if r>=3:break
   i+=r
  literal=row[start:i];out.append(len(literal)-1);out+=literal
 return bytes(out)
def decode_row(data:bytes,width:int)->bytes:
 out=bytearray();p=0
 while p<len(data) and len(out)<width:
  c=data[p];p+=1;n=(c&127)+1
  if c&128:
   if p>=len(data):raise ValueError('short run')
   out+=bytes((data[p],))*n;p+=1
  else:
   if p+n>len(data):raise ValueError('short literal')
   out+=data[p:p+n];p+=n
 if len(out)!=width or p!=len(data):raise ValueError('bad row')
 return bytes(out)
def build(indexed:bytes,width:int=240,height:int=160)->bytes:
 if len(indexed)!=width*height:raise ValueError('image dimensions')
 if len(set(indexed))==1:codec=SOLID;payload=indexed[:1]
 else:
  rle=bytearray()
  for y in range(height):
   row=encode_row(indexed[y*width:(y+1)*width]);rle+=struct.pack('<H',len(row))+row
  if len(rle)<len(indexed):codec=RLE8;payload=bytes(rle)
  else:codec=RAW;payload=indexed
 header=bytearray(HEADER.pack(MAGIC,VERSION,HEADER_SIZE,width,height,codec,0,0,len(indexed),len(payload),0));crc=zlib.crc32(header+payload)&0xffffffff;struct.pack_into('<I',header,24,crc);return bytes(header)+payload
def parse(blob:bytes,verify=True)->dict:
 if len(blob)<HEADER_SIZE:raise ValueError('short GLI1')
 magic,ver,hs,w,h,codec,flags,res,raw_n,payload_n,crc=HEADER.unpack_from(blob)
 if magic!=MAGIC or ver!=VERSION or hs!=HEADER_SIZE or raw_n!=w*h or hs+payload_n>len(blob):raise ValueError('bad GLI1')
 if verify:
  tmp=bytearray(blob[:hs+payload_n]);struct.pack_into('<I',tmp,24,0)
  if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLI1 CRC')
 p=blob[hs:hs+payload_n]
 if codec==SOLID:data=p*raw_n
 elif codec==RAW:data=p
 elif codec==RLE8:
  out=bytearray();q=0
  for _ in range(h):
   if q+2>len(p):raise ValueError('short row header')
   n=struct.unpack_from('<H',p,q)[0];q+=2;out+=decode_row(p[q:q+n],w);q+=n
  if q!=len(p):raise ValueError('trailing RLE')
  data=bytes(out)
 else:raise ValueError('GLI1 codec')
 return {'width':w,'height':h,'codec':codec,'flags':flags,'data':data,'payload_bytes':payload_n,'crc32':crc}
def compile_file(source:str|Path,fit='cover')->bytes:
 from PIL import Image
 # Pillow <9.1 exposes LANCZOS as Image.LANCZOS/ANTIALIAS; newer releases
 # moved it under Image.Resampling.
 if hasattr(Image,'Resampling'):resample=Image.Resampling.LANCZOS
 elif hasattr(Image,'LANCZOS'):resample=Image.LANCZOS
 else:resample=Image.ANTIALIAS
 im=Image.open(source).convert('RGB');w,h=im.size
 if fit=='stretch':im=im.resize((240,160),resample)
 else:
  scale=max(240/w,160/h) if fit=='cover' else min(240/w,160/h);nw,nh=max(1,round(w*scale)),max(1,round(h*scale));im=im.resize((nw,nh),resample)
  if fit=='cover':im=im.crop(((nw-240)//2,(nh-160)//2,(nw-240)//2+240,(nh-160)//2+160))
  else:
   bg=Image.new('RGB',(240,160));bg.paste(im,((240-nw)//2,(160-nh)//2));im=bg
 return build(rgb332(im.tobytes()))
