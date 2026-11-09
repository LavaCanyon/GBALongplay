#!/usr/bin/env python3
"""Join independently keyed GLV2 segments into one episode."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'encoder'))
from container import read,build,VideoPacket,AudioPacket
p=argparse.ArgumentParser();p.add_argument('segments',nargs='+');p.add_argument('-o','--output',required=True);a=p.parse_args()
video=[];audio=[];offset=0;first=None
for name in a.segments:
 x=read(name)
 if first is None:first=x
 elif x['codebook']!=first['codebook'] or x['fps_num']!=first['fps_num'] or x['fps_den']!=first['fps_den'] or x['audio_chunk_samples']!=first['audio_chunk_samples']:raise SystemExit('segment formats/codebooks do not match')
 video += [VideoPacket(q.pts+offset,q.data) for q in x['video']]
 audio += [AudioPacket(q.pts+offset,q.samples,q.data) for q in x['audio']]
 offset += x['duration']
blob=build(video,audio,first['fps_num'],first['fps_den'],first['audio_chunk_samples'],flags=first['flags']&~1,codebook=first['codebook'],audio_gain_q8=first['audio_gain_q8'])
Path(a.output).write_bytes(blob);print(f'wrote {a.output}: {len(a.segments)} segments, {len(video)} frames, {offset/first["timebase"]:.3f}s, {len(blob)} bytes')
