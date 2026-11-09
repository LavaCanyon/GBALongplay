#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).parents[1]))
from encoder.animation_asset import compile_gif,parse
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('-o','--output',required=True);p.add_argument('--fps',type=float,default=4);p.add_argument('--seconds',type=float,default=10);p.add_argument('--fit',choices=('cover','contain','stretch'),default='cover');a=p.parse_args();b=compile_gif(a.input,a.fps,a.seconds,a.fit);Path(a.output).write_bytes(b);x=parse(b);print(f"{a.output}: {len(x['frames'])} frames, {len(b)} bytes")
