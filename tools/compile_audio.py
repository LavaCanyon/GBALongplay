#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from encoder.audio_asset import extract,build,parse,RATE
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('-o','--output',required=True);p.add_argument('--mode',choices=('loop','once'),default='loop');p.add_argument('--loop-start',type=float,default=0);p.add_argument('--loop-end',type=float);p.add_argument('--gain',type=float,default=0);a=p.parse_args();raw=extract(a.input);end=round(a.loop_end*RATE) if a.loop_end is not None else None;b=build(raw,loop=a.mode=='loop',loop_start=round(a.loop_start*RATE),loop_end=end,gain=a.gain);Path(a.output).write_bytes(b);x=parse(b);print(f"{a.output}: {x['sample_count']/RATE:.2f}s, {len(x['packets'])} chunks, gain={x['gain_q8']/256:.2f}x, {len(b)} bytes")
