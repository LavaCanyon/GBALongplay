#!/usr/bin/env python3
"""Generate a deterministic GLV2 stream embedded by the GBA conformance ROM."""
from __future__ import annotations
import math,sys
from pathlib import Path
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'encoder'))
from glp_codec import Encoder,WIDTH,HEIGHT
from adpcm import encode as adpcm_encode
from container import VideoPacket,AudioPacket,build as build_glv,TIMEBASE
from album import Episode,build as build_album
from subtitles import Cue,build as build_subtitles

FRAMES=120;CHUNK=32768;GUARD=16;AUDIO_CHUNKS=3;CYCLE=32768

def frame(t:int)->bytearray:
 f=bytearray(WIDTH*HEIGHT)
 for y in range(HEIGHT):
  for x in range(WIDTH):
   c=((x//30)<<5)|((y//20)<<2)|((x+y)//64&3);dx=x-(28+t*5)%280+20;dy=y-78
   if dx*dx+dy*dy<22*22:c=0xE3
   if 8<y<14 and x<6*t:c=0xFF
   f[y*WIDTH+x]=c
 return f

def main(out:Path):
 enc=Encoder();video=[VideoPacket(round(i*TIMEBASE/10),enc.encode_indexed(frame(i%40))) for i in range(FRAMES)]
 total=CHUNK*AUDIO_CHUNKS;notes=(262,330,392,523);samples=[]
 for i in range(total):
  phase=i%CYCLE;sec=phase//8192;hz=notes[sec]
  v=9000*math.sin(2*math.pi*hz*phase/8192)+3500*math.sin(2*math.pi*(hz/2)*phase/8192)
  samples.append(int(v))
 audio=[]
 for start in range(0,total,CHUNK):
  part=[samples[(start+i)%total] for i in range(CHUNK+GUARD)]
  audio.append(AudioPacket(start,CHUNK,adpcm_encode(part)))
 cues=[Cue(1*TIMEBASE,3*TIMEBASE,'THIS IS A VTT STYLE SUBTITLE.'),Cue(4*TIMEBASE,7*TIMEBASE,'SUBTITLES FOLLOW THE AUDIO CLOCK.'),Cue(8*TIMEBASE,11*TIMEBASE,'SEEKING ALSO UPDATES THE ACTIVE CUE.')]
 styles=[{'position':'top','align':'left','effect':'none','text_color':'#ffffff'},{'position':'bottom','align':'center','effect':'outline','thickness':2,'text_color':'#ffffff','effect_color':'#000000'},{'position':'middle','align':'center','effect':'shadow','thickness':2,'text_color':'#ffff00','effect_color':'#000000'},{'position':'bottom_safe','align':'center','effect':'dithered_panel','text_color':'#ffffff','panel_color':'#202040'}]
 glvs=[build_glv(video,audio,10,1,CHUNK,flags=1,subtitles=build_subtitles(cues,s)) for s in styles]
 def thumbnail(number,base):
  t=bytearray(80*48)
  for y in range(48):
   for x in range(80):t[y*80+x]=base if ((x//8+y//8)&1)==0 else (base^0x24)
  # Large seven-segment episode number.
  segs={1:'bc',2:'abdeg',3:'abcdg',4:'bcfg'}[number]
  rects={'a':(31,6,18,4),'b':(47,9,4,13),'c':(47,26,4,13),'d':(31,38,18,4),
         'e':(28,26,4,13),'f':(28,9,4,13),'g':(31,22,18,4)}
  for s in segs:
   x,y,w,h=rects[s]
   for yy in range(y,y+h):t[yy*80+x:yy*80+x+w]=bytes([0xff])*w
  return bytes(t)
 titles=['EPISODE 1 ORANGE','EPISODE 2 BLUE','EPISODE 3 GREEN','EPISODE 4 PURPLE']
 bases=[0xe3,0x63,0x1c,0x93]
 blob=build_album([Episode(titles[i],glvs[i],thumbnail(i+1,bases[i])) for i in range(4)])
 out.parent.mkdir(parents=True,exist_ok=True)
 if out.suffix.lower() in ('.gla','.bin'):
  out.write_bytes(blob)
 else:
  lines=['#include "test_assets.h"','__attribute__((aligned(4),section(".rodata.assets")))','const unsigned char glp_test_asset[] = {']
  for i in range(0,len(blob),16):lines.append('  '+','.join(f'0x{x:02x}' for x in blob[i:i+16])+',')
  lines+=['};',f'const unsigned glp_test_asset_size = {len(blob)};','']
  out.write_text('\n'.join(lines))
 print(f'generated GLA1 album {out}: {len(blob)} bytes, 4 subtitle-style streams')
if __name__=='__main__':main(Path(sys.argv[1] if len(sys.argv)>1 else ROOT/'player/source/test_assets.c'))
