#!/usr/bin/env python3
"""Encode or collect episodes from JSON and build a GLA1 album."""
from __future__ import annotations
import argparse,json,shutil,subprocess,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).parents[1];sys.path.insert(0,str(ROOT/'encoder'))
from album import Episode,build as build_album
from theme import compile_theme
from image_asset import compile_file
from animation_asset import compile_gif
from screens import Splash,build_splashes,build_episode_extras,TIMED,WAIT_BUTTON,TIMED_SKIPPABLE
from audio_asset import extract as extract_music,build as build_music
from music_resources import build as build_music_resources

def resolve(base:Path,value:str)->Path:
 p=Path(value).expanduser();return p if p.is_absolute() else base/p

def rgb332(rgb:bytes)->bytes:
 if len(rgb)!=80*48*3:raise RuntimeError(f'expected 80x48 RGB24 thumbnail, got {len(rgb)} bytes')
 out=bytearray(80*48)
 for i in range(len(out)):
  r,g,b=rgb[i*3:i*3+3];out[i]=(r&0xe0)|((g&0xe0)>>3)|(b>>6)
 return bytes(out)

def thumbnail(source:Path,at:float)->bytes:
 if not shutil.which('ffmpeg'):raise RuntimeError('ffmpeg was not found on PATH')
 cmd=['ffmpeg','-v','error','-ss',str(at),'-i',str(source),'-frames:v','1','-vf','scale=trunc(iw*sar/2)*2:ih,setsar=1,scale=80:48:force_original_aspect_ratio=increase,crop=80:48','-pix_fmt','rgb24','-f','rawvideo','-']
 return rgb332(subprocess.run(cmd,stdout=subprocess.PIPE,check=True).stdout)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('manifest');ap.add_argument('-o','--output',required=True);ap.add_argument('--work-dir');ap.add_argument('--reuse',action='store_true');a=ap.parse_args()
 mp=Path(a.manifest).resolve();base=mp.parent;cfg=json.loads(mp.read_text());episodes_cfg=cfg['episodes']
 if not 1<=len(episodes_cfg)<=4:raise SystemExit('current GBA menu supports 1..4 videos')
 intro_count=sum(bool(e.get('startup_intro')) for e in episodes_cfg)
 if intro_count>1:raise SystemExit('only one video may be assigned as the startup intro')
 if intro_count==len(episodes_cfg):raise SystemExit('at least one non-intro episode is required for the menu')
 rom=float(cfg.get('rom_mib',64));reserve=float(cfg.get('reserve_mib',0.5));fps=float(cfg.get('fps',10));target=(rom-reserve)/len(episodes_cfg)
 work=Path(a.work_dir).resolve() if a.work_dir else Path(a.output).resolve().with_suffix('.work');work.mkdir(parents=True,exist_ok=True)
 subtitle_style=cfg.get('subtitle_style');subtitle_style_file=work/'subtitle-style.json'
 if subtitle_style:subtitle_style_file.write_text(json.dumps(subtitle_style,indent=2))
 def visual(path,fit='cover',options=None):
  p=resolve(base,path);options=options or {};return compile_gif(p,float(options.get('gif_fps',cfg.get('gif_fps',4))),float(options.get('gif_seconds',cfg.get('gif_seconds',10))),fit) if p.suffix.lower()=='.gif' else compile_file(p,fit)
 music_specs=[cfg.get('menu_music')]+[s.get('music') for s in cfg.get('splashes',[])[:3]]
 for e in episodes_cfg:music_specs += [e.get('preplay',{}).get('music'),e.get('description',{}).get('music')]
 music_blobs=[]
 for spec in music_specs:
  if spec and spec.get('file'):
   raw=extract_music(resolve(base,spec['file']));music_blobs.append(build_music(raw,loop=spec.get('mode','loop')!='once',loop_start=round(float(spec.get('loop_start',0))*8192),loop_end=round(float(spec['loop_end'])*8192) if spec.get('loop_end') is not None else None,gain=float(spec.get('gain',0))))
  else:music_blobs.append(b'')
 music_resources,music_ids=build_music_resources(music_blobs);music_iter=iter(music_ids);menu_music_id=next(music_iter)
 splash_music_ids=[next(music_iter) for _ in cfg.get('splashes',[])[:3]];episode_music_ids=[(next(music_iter),next(music_iter)) for _ in episodes_cfg]
 eps=[];report=[]
 for i,e in enumerate(episodes_cfg):
  title=e['title'];source=resolve(base,e['source']) if 'source'in e else None
  if 'glv'in e:glv=resolve(base,e['glv'])
  else:
   glv=work/f'episode-{i+1:02}.glv';book=work/f'episode-{i+1:02}-vq256.bin';cache=work/f'episode-{i+1:02}.cache.json'
   st=source.stat();settings={'cache_version':2,'source':str(source.resolve()),'source_size':st.st_size,'source_mtime_ns':st.st_mtime_ns,'fps':fps,'target_mib':target,'vq':cfg.get('vq',True),'vq_fps':cfg.get('vq_fps',1),'vq_samples':cfg.get('vq_samples',80000),'vq_edge_fraction':cfg.get('vq_edge_fraction',.5),'key_interval':cfg.get('key_interval',240),'scene_threshold':cfg.get('scene_threshold',48),'motion_error':cfg.get('motion_error',3000),'motion_range':cfg.get('motion_range',2),'solid_error':cfg.get('solid_error',700),'edge_boost':cfg.get('edge_boost',4),'age_boost':cfg.get('age_boost',30),'transition_boost':cfg.get('transition_boost',20),'vq_edge_penalty':cfg.get('vq_edge_penalty',4),'subtitle_style':subtitle_style}
   if e.get('subtitles'):
    sp=resolve(base,e['subtitles']);sst=sp.stat();settings.update(subtitles=str(sp.resolve()),subtitle_size=sst.st_size,subtitle_mtime_ns=sst.st_mtime_ns)
   signature=hashlib.sha256(json.dumps(settings,sort_keys=True,separators=(',',':')).encode()).hexdigest();valid=False
   if a.reuse and glv.exists() and cache.exists():
    try:valid=json.loads(cache.read_text()).get('signature')==signature
    except Exception:valid=False
   if valid:print(f'{title}: reusing unchanged encode {glv}',flush=True)
   else:
    print(f'{title}: source or encoding settings changed; creating a new encode',flush=True)
    if cfg.get('vq',True):
     subprocess.run([sys.executable,str(ROOT/'tools/vq_train.py'),str(source),'-o',str(book),'--fps',str(cfg.get('vq_fps',1)),'--samples',str(cfg.get('vq_samples',80000)),'--edge-fraction',str(cfg.get('vq_edge_fraction',.5))],cwd=ROOT,check=True)
    cmd=[sys.executable,'-m','encoder.cli','encode',str(source),'-o',str(glv),'--fps',str(fps),'--target-mib',str(target),'--key-interval',str(cfg.get('key_interval',240)),'--scene-threshold',str(cfg.get('scene_threshold',48)),'--motion-error',str(cfg.get('motion_error',3000)),'--motion-range',str(cfg.get('motion_range',2)),'--patch-limit','0','--vfr-threshold','-1','--solid-error',str(cfg.get('solid_error',700)),'--edge-boost',str(cfg.get('edge_boost',4)),'--age-boost',str(cfg.get('age_boost',30)),'--transition-boost',str(cfg.get('transition_boost',20)),'--vq-edge-penalty',str(cfg.get('vq_edge_penalty',4))]
    if cfg.get('vq',True):cmd+=['--vq-codebook',str(book)]
    if e.get('subtitles'):cmd+=['--subtitles',str(resolve(base,e['subtitles']))]
    if e.get('subtitles') and subtitle_style:cmd+=['--subtitle-style',str(subtitle_style_file)]
    subprocess.run(cmd,cwd=ROOT,check=True);cache.write_text(json.dumps({'signature':signature,'settings':settings},indent=2))
  if 'thumbnail_rgb332'in e:thumb=resolve(base,e['thumbnail_rgb332']).read_bytes()
  elif 'thumbnail'in e:thumb=thumbnail(resolve(base,e['thumbnail']),0)
  elif source:thumb=thumbnail(source,float(e.get('thumbnail_time',5)))
  else:thumb=bytes(80*48)
  if len(thumb)!=80*48:raise RuntimeError(f'{title}: thumbnail is not 3840 bytes')
  modes={'timed':TIMED,'wait':WAIT_BUTTON,'timed_skippable':TIMED_SKIPPABLE};pre=e.get('preplay',{});desc=e.get('description',{});pre_img=b'';desc_img=b''
  if pre.get('enabled') and pre.get('image'):pre_img=visual(pre['image'],pre.get('fit','cover'),pre)
  if desc.get('enabled') and desc.get('background'):desc_img=visual(desc['background'],desc.get('fit','cover'),desc)
  menu_img=visual(e['menu_background'],e.get('menu_background_fit','cover'),e) if e.get('menu_background') else b''
  extras=build_episode_extras(pre_image=pre_img,pre_mode=modes.get(pre.get('mode','wait'),WAIT_BUTTON),pre_duration=round(float(pre.get('duration',3))*60),pre_fade=bool(pre.get('fade',False)),description_image=desc_img,description_fade=bool(desc.get('fade',False)),pre_music_id=episode_music_ids[i][0],description_music_id=episode_music_ids[i][1],menu_background=menu_img,title=desc.get('title',title),body=desc.get('body',''),text_rect=tuple(desc.get('text_rect',(12,24,216,112)))) if (pre.get('enabled') or desc.get('enabled') or menu_img) else b''
  stream=glv.read_bytes();entry_flags=(1|((int(e.get('intro_position',2))&3)<<1)) if e.get('startup_intro') else 0;eps.append(Episode(title,stream,thumb,flags=entry_flags,extras=extras));report.append({'title':title,'glv':str(glv),'bytes':len(stream),'target_mib':target,'extras_bytes':len(extras)})
 theme_cfg=cfg.get('theme');theme_bg=b''
 if theme_cfg and theme_cfg.get('menu_background',{}).get('mode')=='image' and theme_cfg.get('menu_background',{}).get('image'):theme_bg=visual(theme_cfg['menu_background']['image'],theme_cfg['menu_background'].get('fit','cover'),theme_cfg['menu_background'])
 theme=compile_theme(theme_cfg,theme_bg) if theme_cfg else b''
 spl=[]
 for si,s in enumerate(cfg.get('splashes',[])[:3]):
  if s.get('enabled') and s.get('image'):spl.append(Splash(visual(s['image'],s.get('fit','cover'),s),modes.get(s.get('mode','timed_skippable'),TIMED_SKIPPABLE),round(float(s.get('duration',3))*60),bool(s.get('fade',False)),splash_music_ids[si]))
 global_screens=build_splashes(spl) if spl else b''
 blob=build_album(eps,theme=theme,global_screens=global_screens,music_resources=music_resources if any(music_blobs) else b'',menu_music_id=menu_music_id);out=Path(a.output);out.write_bytes(blob)
 summary={'album':str(out),'album_bytes':len(blob),'theme_bytes':len(theme),'global_screens_bytes':len(global_screens),'rom_mib':rom,'reserve_mib':reserve,'fps':fps,'episode_target_mib':target,'episodes':report}
 out.with_suffix(out.suffix+'.report.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
