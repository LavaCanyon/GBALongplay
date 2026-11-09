"""GLS1 startup splash sets and GLE1 per-episode static screens."""
from __future__ import annotations
from dataclasses import dataclass
import struct,zlib
TIMED=0;WAIT_BUTTON=1;TIMED_SKIPPABLE=2
@dataclass
class Splash:
 image:bytes
 mode:int=TIMED_SKIPPABLE
 duration_frames:int=180
 fade:bool=False
 music_id:int=0

def build_splashes(items:list[Splash])->bytes:
 if len(items)>3:raise ValueError('maximum three splashes')
 header=bytearray(20+16*len(items));payload=bytearray();struct.pack_into('<4sHHIB3xI',header,0,b'GLS1',1,20,0,len(items),0)
 for i,s in enumerate(items):
  off=len(header)+len(payload);struct.pack_into('<BBHIII',header,20+i*16,s.mode,1 if s.fade else 0,s.duration_frames,off,len(s.image),s.music_id);payload+=s.image
 blob=header+payload;struct.pack_into('<I',blob,8,len(blob));struct.pack_into('<I',blob,16,0);struct.pack_into('<I',blob,16,zlib.crc32(blob)&0xffffffff);return bytes(blob)

def parse_splashes(data:bytes)->list[dict]:
 if len(data)<20 or data[:4]!=b'GLS1' or struct.unpack_from('<H',data,4)[0]!=1:raise ValueError('bad GLS1')
 size=struct.unpack_from('<I',data,8)[0];count=data[12]
 if size>len(data) or count>3:raise ValueError('bad GLS1 size')
 tmp=bytearray(data[:size]);crc=struct.unpack_from('<I',tmp,16)[0];struct.pack_into('<I',tmp,16,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLS1 CRC')
 out=[]
 for i in range(count):
  mode,flags,duration,off,n,music_id=struct.unpack_from('<BBHIII',data,20+i*16)
  if off+n>size:raise ValueError('splash image outside block')
  out.append({'mode':mode,'fade':bool(flags&1),'duration_frames':duration,'music_id':music_id,'image':data[off:off+n]})
 return out

def build_episode_extras(*,pre_image:bytes=b'',pre_mode:int=WAIT_BUTTON,pre_duration:int=180,pre_fade:bool=False,description_image:bytes=b'',description_fade:bool=False,pre_music_id:int=0,description_music_id:int=0,menu_background:bytes=b'',title:str='',body:str='',text_rect=(12,24,216,112),text_color=0xff,panel_color=None)->bytes:
 flags=(1 if pre_image else 0)|(2 if description_image or title or body else 0)|((description_music_id&0xffff)<<16);header=bytearray(64);payload=bytearray()
 def add(b):
  if not b:return 0,0
  off=64+len(payload);payload.extend(b);return off,len(b)
 pre_off,pre_n=add(pre_image);desc_off,desc_n=add(description_image);menu_off,menu_n=add(menu_background);title_b=title.upper().encode('ascii','replace')[:63]+b'\0';title_off,_=add(title_b);body_b=body.upper().encode('ascii','replace')[:511]+b'\0';body_off,body_n=add(body_b)
 x,y,w,h=text_rect
 if panel_color is None:panel_color=255 if description_image else 0x01
 struct.pack_into('<4sHHII',header,0,b'GLE1',1,64,64+len(payload),flags);struct.pack_into('<BBHII',header,16,pre_mode,1 if pre_fade else 0,pre_duration,pre_off,pre_n);struct.pack_into('<II',header,28,desc_off,desc_n);header[36:44]=bytes((x,y,w,h,text_color,panel_color,0,1 if description_fade else 0));struct.pack_into('<IIH',header,44,title_off,body_off,body_n);struct.pack_into('<H',header,54,pre_music_id&0xffff);struct.pack_into('<I',header,56,0);struct.pack_into('<I',header,60,menu_off);blob=header+payload;struct.pack_into('<I',blob,56,zlib.crc32(blob)&0xffffffff);return bytes(blob)

def parse_episode_extras(data:bytes)->dict:
 if len(data)<64 or data[:4]!=b'GLE1':raise ValueError('bad GLE1')
 total,flags=struct.unpack_from('<II',data,8)
 if total>len(data):raise ValueError('short GLE1')
 tmp=bytearray(data[:total]);crc=struct.unpack_from('<I',tmp,56)[0];struct.pack_into('<I',tmp,56,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLE1 CRC')
 mode,pf,dur,po,pn=struct.unpack_from('<BBHII',data,16);do,dn=struct.unpack_from('<II',data,28);to,bo,bn=struct.unpack_from('<IIH',data,44);mo=struct.unpack_from('<I',data,60)[0]
 get=lambda o,n:data[o:o+n] if o and o+n<=total else b''
 mn=0
 if mo and mo+28<=total:
  magic=data[mo:mo+4];mn=28+struct.unpack_from('<I',data,mo+20)[0] if magic==b'GLI1' else (struct.unpack_from('<I',data,mo+28)[0] if magic==b'GLF1' else 0)
 return {'flags':flags&0xffff,'pre_music_id':struct.unpack_from('<H',data,54)[0],'description_music_id':flags>>16,'pre_mode':mode,'pre_duration':dur,'pre_fade':bool(pf&1),'description_fade':bool(data[43]&1),'pre_image':get(po,pn),'description_image':get(do,dn),'menu_background':get(mo,mn),'text_rect':tuple(data[36:40]),'text_color':data[40],'panel_color':data[41],'title':get(to,(data[to:].find(b'\0')+1) if to else 0).rstrip(b'\0').decode('ascii'),'body':get(bo,bn).rstrip(b'\0').decode('ascii')}
