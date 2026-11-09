"""GLA1 multi-episode cartridge directory."""
from __future__ import annotations
from dataclasses import dataclass
import struct,zlib
MAGIC=b'GLA1';VERSION=1;HEADER_SIZE=32;ENTRY_SIZE=64
HEADER=struct.Struct('<4sHHHH5I');ENTRY=struct.Struct('<32s8I')
@dataclass
class Episode:
 title:str
 stream:bytes
 thumbnail:bytes=b''
 flags:int=0
 extras:bytes=b''

def build(episodes:list[Episode],flags:int=0,theme:bytes=b'',global_screens:bytes=b'',music_resources:bytes=b'',menu_music_id:int=0)->bytes:
 if not 1<=len(episodes)<=32:raise ValueError('album needs 1..32 episodes')
 flags|=(menu_music_id&0xff)<<8
 directory=HEADER_SIZE;data_offset=directory+len(episodes)*ENTRY_SIZE
 payload=bytearray();cache={};entries=[]
 def add(blob:bytes)->tuple[int,int]:
  if not blob:return 0,0
  if blob in cache:return cache[blob]
  off=data_offset+len(payload);payload.extend(blob);cache[blob]=(off,len(blob));return off,len(blob)
 music_offset=0
 if music_resources:music_offset,_=add(music_resources);flags|=4
 global_offset=0
 if global_screens:global_offset,_=add(global_screens);flags|=2
 theme_offset=0
 if theme:theme_offset,_=add(theme);flags|=1
 for ep in episodes:
  so,ss=add(ep.stream);to,ts=add(ep.thumbnail);xo,xs=add(ep.extras)
  title=ep.title.encode('ascii','replace')[:31]
  title+=b'\0'*(32-len(title))
  # Duration is duplicated for fast menu display when this is a GLV2 stream.
  duration=struct.unpack_from('<I',ep.stream,24)[0] if ep.stream[:4]==b'GLV2' else 0
  entries.append(ENTRY.pack(title,so,ss,duration,to,ts,ep.flags,xo,xs))
 image_size=data_offset+len(payload)
 header=bytearray(HEADER.pack(MAGIC,VERSION,HEADER_SIZE,len(episodes),flags,
                              directory,data_offset,image_size,0,theme_offset))
 body=b''.join(entries)+payload
 crc=zlib.crc32(header+body)&0xffffffff;struct.pack_into('<I',header,24,crc)
 return bytes(header)+body

def parse(data:bytes,verify_crc:bool=True)->dict:
 if len(data)<HEADER_SIZE:raise ValueError('short GLA1')
 magic,ver,hs,count,flags,directory,data_off,image_size,crc,res=HEADER.unpack_from(data)
 if magic!=MAGIC or ver!=VERSION or hs!=HEADER_SIZE or image_size>len(data):raise ValueError('bad GLA1 header')
 if verify_crc:
  tmp=bytearray(data[:image_size]);struct.pack_into('<I',tmp,24,0)
  if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLA1 CRC mismatch')
 cursor=data_off;music_resources=b''
 if flags&4:
  if cursor+20>image_size or data[cursor:cursor+4]!=b'GMR1':raise ValueError('bad music resources')
  music_size=struct.unpack_from('<I',data,cursor+8)[0]
  if cursor+music_size>image_size:raise ValueError('music resources outside image')
  music_resources=data[cursor:cursor+music_size];cursor+=music_size
 global_screens=b''
 if flags&2:
  if cursor+20>image_size or data[cursor:cursor+4]!=b'GLS1':raise ValueError('bad global screens')
  global_size=struct.unpack_from('<I',data,cursor+8)[0]
  if cursor+global_size>image_size:raise ValueError('global screens outside image')
  global_screens=data[cursor:cursor+global_size]
 theme=b''
 if flags&1:
  if not res or res+8>image_size:raise ValueError('bad theme offset')
  theme_size=struct.unpack_from('<H',data,res+6)[0];bg_rel=struct.unpack_from('<I',data,res+312)[0] if theme_size>=320 and res+316<=image_size else 0
  if bg_rel:
   if res+bg_rel+28>image_size:raise ValueError('theme background outside image')
   magic=data[res+bg_rel:res+bg_rel+4]
   asset_size=(28+struct.unpack_from('<I',data,res+bg_rel+20)[0]) if magic==b'GLI1' else (struct.unpack_from('<I',data,res+bg_rel+28)[0] if magic==b'GLF1' else 0)
   if not asset_size:raise ValueError('unknown theme background asset')
   theme_size=max(theme_size,bg_rel+asset_size)
  if res+theme_size>image_size:raise ValueError('theme outside image')
  theme=data[res:res+theme_size]
 episodes=[]
 for i in range(count):
  title,so,ss,dur,to,ts,ef,r0,r1=ENTRY.unpack_from(data,directory+i*ENTRY_SIZE)
  if so+ss>image_size or (ts and to+ts>image_size):raise ValueError('album object outside image')
  episodes.append({'title':title.split(b'\0',1)[0].decode('ascii'), 'stream_offset':so,
   'stream_size':ss,'duration':dur,'thumbnail_offset':to,'thumbnail_size':ts,'flags':ef,'extras_offset':r0,'extras_size':r1,'extras':data[r0:r0+r1] if r0 and r0+r1<=image_size else b''})
 return {'version':ver,'flags':flags,'image_size':image_size,'crc32':crc,'theme':theme,'theme_offset':res,'music_resources':music_resources,'global_screens':global_screens,'episodes':episodes}
