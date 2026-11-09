#!/usr/bin/env python3
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).parents[1]/'encoder'))
from image_asset import compile_file,parse
p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('-o','--output',required=True);p.add_argument('--fit',choices=('cover','contain','stretch'),default='cover');a=p.parse_args();b=compile_file(a.input,a.fit);Path(a.output).write_bytes(b);x=parse(b);print(f"{a.output}: {x['width']}x{x['height']} codec={x['codec']} payload={x['payload_bytes']} total={len(b)}")
