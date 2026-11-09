#!/usr/bin/env python3
"""Build a GLA1 album from TITLE|STREAM.glv|THUMB.rgb episode specs."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'encoder'))
from album import Episode,build
from theme import compile_theme
p=argparse.ArgumentParser();p.add_argument('-o','--output',required=True);p.add_argument('--theme',help='theme JSON to compile as GLT1');p.add_argument('--episode',action='append',required=True,help='TITLE|stream.glv|80x48.rgb332')
a=p.parse_args();episodes=[]
for spec in a.episode:
 parts=spec.split('|');
 if len(parts)!=3:raise SystemExit('episode must be TITLE|STREAM|THUMBNAIL')
 title,stream,thumb=parts;episodes.append(Episode(title,Path(stream).read_bytes(),Path(thumb).read_bytes()))
theme=compile_theme(__import__('json').loads(Path(a.theme).read_text())) if a.theme else b''
blob=build(episodes,theme=theme);Path(a.output).write_bytes(blob);print(f'wrote {a.output}: {len(episodes)} episodes, {len(blob)} bytes')
