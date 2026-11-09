"""GSA1 reusable mono ADPCM assets for menus and static screens."""
from __future__ import annotations
from array import array
from pathlib import Path
import math,shutil,struct,subprocess,sys,zlib
try:from .adpcm import encode as adpcm_encode,decode as adpcm_decode
except ImportError:from adpcm import encode as adpcm_encode,decode as adpcm_decode
MAGIC=b'GSA1';VERSION=1;HEADER_SIZE=52;RATE=8192;CHUNK=32768;GUARD=16
HEADER=struct.Struct('<4sHHIIIIHHIIIIII');INDEX=struct.Struct('<IIII')
LOOP=1

def extract(path:str|Path)->bytes:
 if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg not found')
 return subprocess.run(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar',str(RATE),'-f','s16le','-'],stdout=subprocess.PIPE,check=True).stdout
def build(pcm_bytes:bytes,*,loop=False,loop_start=0,loop_end=None,gain=0)->bytes:
 vals=array('h');vals.frombytes(pcm_bytes)
 if sys.byteorder!='little':vals.byteswap()
 samples=len(vals);loop_end=samples if loop_end is None else max(1,min(samples,loop_end));loop_start=max(0,min(loop_end-1,loop_start));rms=math.sqrt(sum(int(x)*int(x) for x in vals)/max(1,samples));gain=gain or max(1,min(8,4096/max(1,rms)));gain_q8=round(gain*256);count=(samples+CHUNK-1)//CHUNK;index_off=HEADER_SIZE;data_off=index_off+count*INDEX.size;payload=bytearray();records=[]
 for start in range(0,samples,CHUNK):
  logical=min(CHUNK,samples-start);part=list(vals[start:min(samples,start+CHUNK+GUARD)]);part += [0]*(CHUNK+GUARD-len(part));packet=adpcm_encode(part);off=data_off+len(payload);payload+=packet;records.append(INDEX.pack(start,logical,off,len(packet)))
 total=data_off+len(payload);flags=LOOP if loop else 0;head=bytearray(HEADER.pack(MAGIC,VERSION,HEADER_SIZE,total,RATE,samples,CHUNK,count,flags,gain_q8,loop_start,loop_end,index_off,data_off,0));blob=head+b''.join(records)+payload;struct.pack_into('<I',blob,48,zlib.crc32(blob)&0xffffffff);return bytes(blob)
def parse(blob:bytes,verify=True)->dict:
 if len(blob)<HEADER_SIZE:raise ValueError('short GSA1')
 magic,ver,hs,total,rate,samples,chunk,count,flags,gain,ls,le,io,do,crc=HEADER.unpack_from(blob)
 if magic!=MAGIC or ver!=VERSION or hs!=HEADER_SIZE or total>len(blob) or rate!=RATE:raise ValueError('bad GSA1')
 if verify:
  tmp=bytearray(blob[:total]);struct.pack_into('<I',tmp,48,0)
  if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GSA1 CRC')
 packets=[]
 for i in range(count):
  st,n,off,size=INDEX.unpack_from(blob,io+i*INDEX.size)
  if off+size>total:raise ValueError('audio packet outside asset')
  packets.append({'start':st,'samples':n,'offset':off,'size':size,'data':blob[off:off+size]})
 return {'sample_rate':rate,'sample_count':samples,'chunk_samples':chunk,'flags':flags,'gain_q8':gain,'loop_start':ls,'loop_end':le,'packets':packets,'total_size':total,'crc32':crc}
def decode_pcm(blob:bytes)->list[int]:
 x=parse(blob);out=[]
 for p in x['packets']:out+=adpcm_decode(p['data'],CHUNK+GUARD)[:p['samples']]
 return out
