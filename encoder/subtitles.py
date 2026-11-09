"""WebVTT/SRT parser and compact GLU1 timed-text compiler."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import html,re,struct,zlib
MAGIC=b'GLU1';VERSION=1;HEADER_SIZE=24;CUE=struct.Struct('<IIIHH');TIMEBASE=8192
@dataclass
class Cue:start:int;end:int;text:str

def timestamp(s:str)->float:
 s=s.strip().replace(',','.');parts=s.split(':')
 if len(parts)==3:h,m,sec=parts
 elif len(parts)==2:h='0';m,sec=parts
 else:raise ValueError(f'bad subtitle timestamp {s}')
 return int(h)*3600+int(m)*60+float(sec)
def clean(text:str)->str:
 text=re.sub(r'<[^>]+>','',html.unescape(text));text=re.sub(r'[ \t]+',' ',text)
 return text.strip().upper().encode('ascii','replace').decode('ascii')
def parse_text(text:str)->list[Cue]:
 text=text.replace('\r\n','\n').replace('\r','\n').lstrip('\ufeff');blocks=re.split(r'\n\s*\n',text);out=[]
 for block in blocks:
  lines=[x.strip() for x in block.split('\n') if x.strip()]
  if not lines or lines[0].startswith(('WEBVTT','NOTE','STYLE','REGION')):continue
  ti=next((i for i,x in enumerate(lines) if '-->' in x),-1)
  if ti<0:continue
  left,right=lines[ti].split('-->',1);right=right.strip().split()[0]
  try:start,end=timestamp(left),timestamp(right)
  except ValueError:continue
  body=clean('\n'.join(lines[ti+1:]));
  if body and end>start:out.append(Cue(round(start*TIMEBASE),round(end*TIMEBASE),body))
 out.sort(key=lambda c:(c.start,c.end));return out
def parse_file(path:str|Path)->list[Cue]:return parse_text(Path(path).read_text(encoding='utf-8-sig',errors='replace'))
def build(cues:list[Cue],style:dict|None=None)->bytes:
 strings=bytearray();records=[];style=style or {};hs=40 if style else HEADER_SIZE
 for c in cues:
  b=c.text.encode('ascii','replace')[:255];off=len(strings);strings+=b;records.append(CUE.pack(c.start,c.end,off,len(b),0))
 string_off=hs+len(records)*CUE.size;total=string_off+len(strings);header=bytearray(struct.pack('<4sHHIIII',MAGIC,VERSION,hs,total,len(records),string_off,0))
 if hs==40:
  effects={'none':0,'outline':1,'shadow':2,'panel':3,'dithered_panel':4};positions={'top':0,'middle':1,'bottom':2,'bottom_safe':3};aligns={'left':0,'center':1}
  def col(v,d):
   if not v:return d
   n=int(v.lstrip('#'),16);return (((n>>16)*7+127)//255<<5)|((((n>>8)&255)*7+127)//255<<2)|((n&255)*3+127)//255
  vals=(int(style.get('font',0)),positions.get(style.get('position','bottom'),2),aligns.get(style.get('align','center'),1),min(3,int(style.get('max_lines',2))),effects.get(style.get('effect','outline'),1),min(2,int(style.get('thickness',1))),col(style.get('text_color'),0xff),col(style.get('effect_color'),0),col(style.get('panel_color'),1),min(8,int(style.get('padding',2))),min(4,int(style.get('line_spacing',2))),int(style.get('dither',1)),0)
  header+=struct.pack('<12BI',*vals)
 blob=header+b''.join(records)+strings;struct.pack_into('<I',blob,20,zlib.crc32(blob)&0xffffffff);return bytes(blob)
def parse(blob:bytes)->dict:
 if len(blob)<HEADER_SIZE:raise ValueError('short GLU1')
 magic,ver,hs,total,count,so,crc=struct.unpack_from('<4sHHIIII',blob)
 if magic!=MAGIC or ver!=VERSION or hs not in (24,40) or total>len(blob) or so>total:raise ValueError('bad GLU1')
 tmp=bytearray(blob[:total]);struct.pack_into('<I',tmp,20,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLU1 CRC')
 cues=[]
 for i in range(count):
  st,en,off,n,flags=CUE.unpack_from(blob,hs+i*CUE.size)
  if so+off+n>total:raise ValueError('subtitle text outside block')
  cues.append(Cue(st,en,blob[so+off:so+off+n].decode('ascii')))
 style=None
 if hs>=40:
  v=struct.unpack_from('<12BI',blob,24);style={'font':v[0],'position':v[1],'align':v[2],'max_lines':v[3],'effect':v[4],'thickness':v[5],'text_color':v[6],'effect_color':v[7],'panel_color':v[8],'padding':v[9],'line_spacing':v[10],'dither':v[11]}
 return {'cues':cues,'style':style,'total_size':total,'crc32':crc}
