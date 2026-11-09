#!/usr/bin/env python3
"""GLP development CLI: encode, inspect, and preview GLV2 streams."""
from __future__ import annotations
import argparse,json,shutil,struct,subprocess,sys,tempfile,math
from array import array
from pathlib import Path
try:
 from .glp_codec import Encoder,Decoder,Profile,WIDTH,HEIGHT,indexed_to_rgb
 from .adpcm import encode as adpcm_encode
 from .container import VideoPacket,AudioPacket,build,parse,TIMEBASE,HEADER_SIZE,VIDEO_INDEX,AUDIO_INDEX
 from .rate_control import RateController,video_budget
 from .subtitles import parse_file as parse_subtitles,build as build_subtitles
 from . import ppm
except ImportError:
 from glp_codec import Encoder,Decoder,Profile,WIDTH,HEIGHT,indexed_to_rgb
 from adpcm import encode as adpcm_encode
 from container import VideoPacket,AudioPacket,build,parse,TIMEBASE,HEADER_SIZE,VIDEO_INDEX,AUDIO_INDEX
 from rate_control import RateController,video_budget
 from subtitles import parse_file as parse_subtitles,build as build_subtitles
 import ppm

AUDIO_RATE=8192; AUDIO_CHUNK=32768; FIFO_GUARD=16

def _require_ffmpeg():
 if not shutil.which("ffmpeg"):raise SystemExit("ffmpeg was not found on PATH")

def _raw_frames(source:str,fps:float,start:float=0,duration:float=0):
 _require_ffmpeg();vf=f"scale=trunc(iw*sar/2)*2:ih,setsar=1,scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,fps={fps}"
 cmd=["ffmpeg","-v","error"]
 if start>0:cmd += ["-ss",str(start)]
 cmd += ["-i",source]
 if duration>0:cmd += ["-t",str(duration)]
 cmd += ["-an","-vf",vf,"-pix_fmt","rgb24","-f","rawvideo","-"]
 p=subprocess.Popen(cmd,stdout=subprocess.PIPE);n=WIDTH*HEIGHT*3
 try:
  while True:
   data=p.stdout.read(n)
   if not data:break
   if len(data)!=n:raise RuntimeError("truncated ffmpeg video frame")
   yield data
 finally:
  if p.stdout:p.stdout.close()
  if p.wait():raise RuntimeError("video ffmpeg failed")

def _extract_audio(source:str,start:float=0,duration:float=0)->bytes:
 _require_ffmpeg();cmd=["ffmpeg","-v","error"]
 if start>0:cmd += ["-ss",str(start)]
 cmd += ["-i",source]
 if duration>0:cmd += ["-t",str(duration)]
 cmd += ["-vn","-ac","1","-ar",str(AUDIO_RATE),"-f","s16le","-"]
 p=subprocess.run(cmd,stdout=subprocess.PIPE,check=True);return p.stdout

def _audio_packets(raw:bytes)->list[AudioPacket]:
 total=len(raw)//2;out=[]
 for start in range(0,total,AUDIO_CHUNK):
  logical=min(AUDIO_CHUNK,total-start);need=AUDIO_CHUNK+FIFO_GUARD
  part=raw[start*2:min(total,start+need)*2]
  vals=array('h');vals.frombytes(part)
  if sys.byteorder!='little':vals.byteswap()
  vals.extend([0]*(need-len(vals)))
  out.append(AudioPacket(start,logical,adpcm_encode(list(vals))))
 return out

def _scene_score(a:bytes,b:bytes)->float:
 total=count=0
 for i in range(0,len(a),12):
  total+=abs(a[i]-b[i])+abs(a[i+1]-b[i+1])+abs(a[i+2]-b[i+2]);count+=3
 return total/max(1,count)

def encode(args):
 profile=Profile(args.skip_error,args.two_error,args.four_error,args.key_interval,
                 args.motion_error,args.motion_range,args.patch_limit,
                 args.solid_error,args.edge_boost,args.age_boost,args.age_cap,
                 args.transition_boost,args.motion_edge_tolerance,args.vq_edge_penalty,
                 args.vq_fast_error,args.vq_fast_edges)
 raw=_extract_audio(args.input,args.start,args.duration);audio=_audio_packets(raw)
 pcm=array('h');pcm.frombytes(raw)
 if sys.byteorder!='little':pcm.byteswap()
 rms=math.sqrt(sum(int(x)*int(x) for x in pcm)/max(1,len(pcm)))
 gain=args.audio_gain if args.audio_gain>0 else max(1.0,min(8.0,4096/max(1.0,rms)))
 audio_gain_q8=round(gain*256)
 print(f"audio RMS {rms:.1f}, playback gain {gain:.2f}x",file=sys.stderr)
 expected_frames=max(1,round((len(raw)//2)*args.fps/AUDIO_RATE))
 controller=None
 if args.target_mib:
  target=round(args.target_mib*1048576)
  fixed=HEADER_SIZE+expected_frames*VIDEO_INDEX.size+len(audio)*AUDIO_INDEX.size
  audio_bytes=sum(len(p.data) for p in audio)
  bpf=video_budget(target,audio_bytes,expected_frames,fixed)
  controller=RateController(bpf)
  print(f"target video budget: {bpf:.1f} bytes/frame ({bpf*args.fps/1024:.2f} KiB/s)",file=sys.stderr)
 codebook=Path(args.vq_codebook).read_bytes() if args.vq_codebook else b''
 codec=Encoder(profile,codebook);video=[];previous_rgb=None;last_emitted_rgb=None;last_scene=-args.scene_min_frames;scenes=[];omitted=0
 for i,rgb in enumerate(_raw_frames(args.input,args.fps,args.start,args.duration)):
  budget=controller.budget() if controller else None
  score=_scene_score(rgb,previous_rgb) if previous_rgb is not None else 0
  scene=score>=args.scene_threshold and i-last_scene>=args.scene_min_frames
  hold_score=_scene_score(rgb,last_emitted_rgb) if last_emitted_rgb is not None else 999
  if not scene and hold_score<=args.vfr_threshold and not codec.key_due():
   codec.advance();omitted+=1
   if controller:controller.commit(0)
   previous_rgb=rgb
   continue
  if scene:
   last_scene=i;scenes.append(i)
   if controller:budget=max(budget,round(controller.bytes_per_frame*args.scene_burst))
  packet=codec.encode_rgb24(rgb,budget,force_keyframe=scene,key_max_colors=2 if scene else 0)
  if controller:controller.commit(len(packet))
  video.append(VideoPacket(round(i*TIMEBASE/args.fps),packet));previous_rgb=rgb;last_emitted_rgb=rgb
  if scene:print(f"\nscene refresh at frame {i} (score {score:.1f}, {len(packet)} bytes)",file=sys.stderr)
  if (i+1)%100==0:print(f"\r{i+1} frames",end="",file=sys.stderr)
 subtitle_style=json.loads(Path(args.subtitle_style).read_text()) if args.subtitle_style else None
 subtitles=build_subtitles(parse_subtitles(args.subtitles),subtitle_style) if args.subtitles else b''
 fpsn=round(args.fps*1000);blob=build(video,audio,fpsn,1000,AUDIO_CHUNK,codebook=codebook,audio_gain_q8=audio_gain_q8,subtitles=subtitles)
 Path(args.output).write_bytes(blob)
 detail=f", rate error {controller.error_bytes:+.0f} bytes" if controller else ""
 print(f"\nwrote {args.output}: {len(blob)/1048576:.2f} MiB, {len(video)} coded frames, {omitted} held frames, {len(audio)} audio chunks, {len(scenes)} scene refreshes{detail}",file=sys.stderr)

def probe(args):
 info=parse(Path(args.input).read_bytes());video=info.pop('video');audio=info.pop('audio');codebook=info.pop('codebook',b'');subtitles=info.pop('subtitles',b'')
 info.update(codebook_bytes=len(codebook),subtitle_bytes=len(subtitles),video_frames=len(video),video_bytes=sum(len(x.data) for x in video),audio_chunks=len(audio),
             audio_bytes=sum(len(x.data) for x in audio),seconds=info['duration']/info['timebase'])
 print(json.dumps(info,indent=2))

def decode(args):
 info=parse(Path(args.input).read_bytes());out=Path(args.output);out.mkdir(parents=True,exist_ok=True);dec=Decoder(info.get('codebook',b''))
 for i,p in enumerate(info['video']):
  frame=dec.decode(p.data)
  if i%args.every==0:ppm.write(out/f"frame-{i:06}.ppm",WIDTH,HEIGHT,indexed_to_rgb(frame))
 print(f"wrote previews to {out}")

def plan(args):
 seconds=args.episodes*args.minutes*60;frames=round(seconds*args.fps)
 chunks=(round(seconds*AUDIO_RATE)+AUDIO_CHUNK-1)//AUDIO_CHUNK
 audio_payload=chunks*(4+(AUDIO_CHUNK+FIFO_GUARD+1)//2)
 overhead=HEADER_SIZE+frames*VIDEO_INDEX.size+chunks*AUDIO_INDEX.size+args.reserve_kib*1024
 capacity=round(args.rom_mib*1048576);video=max(0,capacity-audio_payload-overhead)
 result={"rom_mib":args.rom_mib,"episodes":args.episodes,"minutes_each":args.minutes,
  "seconds":seconds,"audio_mib":audio_payload/1048576,"indexes_and_reserve_mib":overhead/1048576,
  "video_mib":video/1048576,"video_kib_per_second":video/max(1,seconds)/1024,
  "video_bytes_per_frame":video/max(1,frames),"episode_target_mib":(capacity-args.reserve_kib*1024)/args.episodes/1048576}
 print(json.dumps(result,indent=2))

def main():
 p=argparse.ArgumentParser(prog="gbalong");sub=p.add_subparsers(required=True)
 e=sub.add_parser("encode",help="encode video and mono audio through FFmpeg");e.add_argument("input");e.add_argument("-o","--output",required=True);e.add_argument("--fps",type=float,default=10)
 e.add_argument("--start",type=float,default=0,help="source start time in seconds")
 e.add_argument("--duration",type=float,default=0,help="segment duration in seconds; zero means to end")
 e.add_argument("--target-mib",type=float,help="hard target for this GLV2 episode, including audio and indexes")
 e.add_argument("--audio-gain",type=float,default=0,help="playback gain; zero selects automatic RMS normalization")
 e.add_argument("--subtitles",help="optional WebVTT or SRT subtitle file")
 e.add_argument("--subtitle-style",help="optional subtitle style JSON")
 e.add_argument("--scene-threshold",type=float,default=48,help="RGB cut score that triggers a larger refresh packet")
 e.add_argument("--scene-burst",type=float,default=8,help="scene-refresh budget in normal frame budgets")
 e.add_argument("--scene-min-frames",type=int,default=8,help="minimum spacing between scene refreshes")
 e.add_argument("--motion-error",type=int,default=1400,help="maximum error for a motion-copy block")
 e.add_argument("--motion-range",type=int,default=2,help="motion search radius in four-pixel steps")
 e.add_argument("--vfr-threshold",type=float,default=-1,help="hold frames below this RGB change score; negative disables VFR")
 e.add_argument("--patch-limit",type=int,default=0,help="maximum 4x4 patch records per frame; zero disables the experimental mode")
 e.add_argument("--solid-error",type=int,default=700,help="maximum error for a lossy solid-colour block")
 e.add_argument("--edge-boost",type=int,default=4,help="priority multiplier for strong line-art edges")
 e.add_argument("--age-boost",type=int,default=30,help="percent priority added per stale frame")
 e.add_argument("--age-cap",type=int,default=12,help="maximum stale-frame priority age")
 e.add_argument("--transition-boost",type=int,default=20,help="priority for newly appearing or disappearing edges")
 e.add_argument("--motion-edge-tolerance",type=int,default=8,help="maximum edge-count mismatch for motion copies")
 e.add_argument("--vq-codebook",help="optional 4096-byte 4x4 RGB332 VQ codebook")
 e.add_argument("--vq-edge-penalty",type=int,default=4,help="prefer sharper fallback records for edge-rich blocks")
 e.add_argument("--vq-fast-error",type=int,default=2500,help="fast-path error ceiling for smooth VQ blocks")
 e.add_argument("--vq-fast-edges",type=int,default=10,help="fast-path edge-count ceiling")
 e.add_argument("--skip-error",type=int,default=110);e.add_argument("--two-error",type=int,default=900);e.add_argument("--four-error",type=int,default=260);e.add_argument("--key-interval",type=int,default=80);e.set_defaults(func=encode)
 q=sub.add_parser("probe");q.add_argument("input");q.set_defaults(func=probe)
 d=sub.add_parser("decode");d.add_argument("input");d.add_argument("-o","--output",required=True);d.add_argument("--every",type=int,default=30);d.set_defaults(func=decode)
 z=sub.add_parser("plan",help="estimate a multi-episode cartridge bitrate")
 z.add_argument("--rom-mib",type=float,default=64);z.add_argument("--episodes",type=int,default=4)
 z.add_argument("--minutes",type=float,default=22);z.add_argument("--fps",type=float,default=10)
 z.add_argument("--reserve-kib",type=int,default=512,help="player, menu, thumbnails, and alignment reserve")
 z.set_defaults(func=plan)
 a=p.parse_args();a.func(a)
if __name__=="__main__":main()
