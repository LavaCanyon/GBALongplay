#!/usr/bin/env python3
"""Native low-spec Linux desktop wrapper for GLP Studio."""
from __future__ import annotations
import json,os,queue,shutil,subprocess,sys,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,colorchooser,messagebox
ROOT=Path(__file__).resolve().parents[1];WORK=Path.home()/'.glp-studio';WORK.mkdir(exist_ok=True)
TEMPLATES={
 'Classic Blue':{'background':'#081830','header':'#182c54','selection':'#38589c','text':'#ffffff','muted':'#b5bdcf','border':'#ffffff','headerTitle':'GBA LONGPLAY','footerText':'A PLAY   UP DOWN SELECT','list':{'x':4,'y':81,'row':16},'thumb':{'x':152,'y':24,'w':80,'h':48},'overlay':{'y':144,'h':12,'duration':90,'background':'#081020','text':'#ffffff'}},
 'Minimal Dark':{'background':'#101214','header':'#101214','selection':'#d8e1df','text':'#f5f7f6','muted':'#85918f','border':'#596462','headerTitle':'VIDEO COLLECTION','footerText':'SELECT AN EPISODE','list':{'x':8,'y':68,'row':18},'thumb':{'x':154,'y':16,'w':72,'h':43},'overlay':{'y':142,'h':14,'duration':75,'background':'#080a0c','text':'#f5f7f6'}},
 'Simple Red':{'background':'#201018','header':'#681820','selection':'#d06038','text':'#fff0d0','muted':'#d0a090','border':'#ffc060','headerTitle':'SF VIDEO PAK','footerText':'A PLAY  START PAUSE','list':{'x':4,'y':82,'row':16},'thumb':{'x':150,'y':22,'w':82,'h':49},'overlay':{'y':142,'h':12,'duration':90,'background':'#180810','text':'#fff0d0'}}}
MESSAGES={'paused':'PAUSED','resuming':'RESUMING','rewinding':'REWINDING','forwarding':'FORWARDING','chapter':'CHAPTER {number}','locked':'BUTTONS LOCKED','unlocked':'BUTTONS UNLOCKED','brightness_up':'BRIGHTNESS UP','brightness_down':'BRIGHTNESS DOWN','contrast_up':'CONTRAST UP','contrast_down':'CONTRAST DOWN'}
def episode(n):return {'title':f'EPISODE {n}','source':'','subtitles':'','thumbnail_time':5,'startup_intro':False,'intro_position':2,'menu_background':'','preplay':{'enabled':False,'image':'','mode':'wait','duration':3,'fade':False},'description':{'enabled':False,'background':'','title':f'EPISODE {n}','body':'','text_rect':[12,24,216,112],'fade':False}}
def locate_ffmpeg():
 p=shutil.which('ffmpeg')
 if p:return p
 for p in (ROOT/'converter/vendor/ffmpeg',ROOT/'converter/vendor/bin/ffmpeg'):
  if p.exists():return str(p)
 try:
  import imageio_ffmpeg;return imageio_ffmpeg.get_ffmpeg_exe()
 except Exception:return None
class App(tk.Tk):
 def __init__(self):
  super().__init__();self.title('GLP Studio');self.geometry('980x650');self.minsize(850,560);self.option_add('*Font','TkDefaultFont 9');self.style=ttk.Style(self);self.style.theme_use('clam');self.style.configure('.',background='#d4d0c8',foreground='#111');self.style.configure('TNotebook',background='#d4d0c8');self.theme=dict(TEMPLATES['Classic Blue']);self.theme['messages']=dict(MESSAGES);self.subtitle_style={'font':0,'position':'bottom','align':'center','max_lines':2,'effect':'outline','thickness':1,'text_color':'#ffffff','effect_color':'#000000','panel_color':'#081020','padding':2,'line_spacing':2,'dither':1};self.episodes=[episode(1),episode(2)];self.splashes=[];self.current=0;self.q=queue.Queue();self.building=False;self.make_ui();self.load_episode(0);self.draw_preview();self.after(100,self.pump)
 def make_ui(self):
  bar=ttk.Frame(self,padding=4);bar.pack(fill='x');ttk.Button(bar,text='New',command=self.new).pack(side='left');ttk.Button(bar,text='Open…',command=self.open_project).pack(side='left');ttk.Button(bar,text='Save…',command=self.save_project).pack(side='left');ttk.Separator(bar,orient='vertical').pack(side='left',fill='y',padx=5);self.reuse_var=tk.BooleanVar(value=True);ttk.Checkbutton(bar,text='Reuse unchanged encodes',variable=self.reuse_var).pack(side='left',padx=4);ttk.Button(bar,text='Build GBA ROM…',command=self.build).pack(side='left');self.status=ttk.Label(bar,text='Ready');self.status.pack(side='right')
  self.nb=ttk.Notebook(self);self.nb.pack(fill='both',expand=True,padx=5,pady=5);self.project=ttk.Frame(self.nb,padding=8);self.theme_tab=ttk.Frame(self.nb,padding=8);self.subtitle_tab=ttk.Frame(self.nb,padding=8);self.screens=ttk.Frame(self.nb,padding=8);self.build_tab=ttk.Frame(self.nb,padding=8);self.nb.add(self.project,text='Episodes');self.nb.add(self.theme_tab,text='Menu Theme');self.nb.add(self.subtitle_tab,text='Subtitles');self.nb.add(self.screens,text='Screens & Music');self.nb.add(self.build_tab,text='Build Log');self.make_project();self.make_theme();self.make_subtitles();self.make_screens();self.log=tk.Text(self.build_tab,wrap='word',font=('TkFixedFont',9));self.log.pack(fill='both',expand=True)
 def make_project(self):
  left=ttk.Frame(self.project);left.pack(side='left',fill='y');self.list=tk.Listbox(left,width=25,height=18,exportselection=False);self.list.pack(fill='y',expand=True);self.list.bind('<<ListboxSelect>>',self.choose_episode);b=ttk.Frame(left);b.pack(fill='x');ttk.Button(b,text='Add',command=self.add_episode).pack(side='left',expand=True,fill='x');ttk.Button(b,text='Remove',command=self.remove_episode).pack(side='left',expand=True,fill='x')
  holder=ttk.Frame(self.project);holder.pack(side='left',fill='both',expand=True,padx=10);scroll=tk.Canvas(holder,highlightthickness=0,background='#d4d0c8');sb=ttk.Scrollbar(holder,orient='vertical',command=scroll.yview);scroll.configure(yscrollcommand=sb.set);sb.pack(side='right',fill='y');scroll.pack(side='left',fill='both',expand=True);form=ttk.LabelFrame(scroll,text='Selected episode',padding=8);win=scroll.create_window((0,0),window=form,anchor='nw');form.bind('<Configure>',lambda e:scroll.configure(scrollregion=scroll.bbox('all')));scroll.bind('<Configure>',lambda e:scroll.itemconfigure(win,width=e.width));scroll.bind_all('<MouseWheel>',lambda e:scroll.yview_scroll(int(-e.delta/120),'units'));self.ev={};
  self.entry_row(form,'Title','title');self.path_row(form,'Video file','source',video=True);self.path_row(form,'Subtitles (VTT/SRT)','subtitles',video='subs');self.entry_row(form,'Thumbnail time (seconds)','thumbnail_time');intro=ttk.Frame(form);intro.pack(fill='x',pady=4);self.intro_enabled=tk.BooleanVar();ttk.Checkbutton(intro,text='Use as startup intro',variable=self.intro_enabled,command=self.intro_changed).pack(side='left');self.intro_position=tk.StringVar();self.intro_combo=ttk.Combobox(intro,textvariable=self.intro_position,values=['Before all splashes','After Splash 1','After Splash 2','After Splash 3 / before menu'],state='disabled',width=27);self.intro_combo.pack(side='left',padx=8);self.path_row(form,'Highlighted menu background','menu_background')
  ttk.Separator(form).pack(fill='x',pady=8);self.pre_enabled=tk.BooleanVar();self.pre_fade=tk.BooleanVar();pf=ttk.Frame(form);pf.pack(fill='x');ttk.Checkbutton(pf,text='Show pre-play screen',variable=self.pre_enabled).pack(side='left');ttk.Checkbutton(pf,text='Fade in/out',variable=self.pre_fade).pack(side='left',padx=12);self.path_row(form,'Pre-play image','pre_image');self.path_row(form,'Pre-play music','pre_music',video='audio');self.pre_mode=tk.StringVar();self.combo_row(form,'Advance mode',self.pre_mode,['wait','timed','timed_skippable']);self.entry_row(form,'Duration (seconds)','pre_duration')
  ttk.Separator(form).pack(fill='x',pady=8);self.desc_enabled=tk.BooleanVar();self.desc_fade=tk.BooleanVar();df=ttk.Frame(form);df.pack(fill='x');ttk.Checkbutton(df,text='Enable Select description page',variable=self.desc_enabled).pack(side='left');ttk.Checkbutton(df,text='Fade in/out',variable=self.desc_fade).pack(side='left',padx=12);self.path_row(form,'Description background','desc_image');self.path_row(form,'Description music','desc_music',video='audio');self.entry_row(form,'Description title','desc_title');ttk.Label(form,text='Description text').pack(anchor='w');self.desc_body=tk.Text(form,height=8,wrap='word');self.desc_body.pack(fill='x')
 def entry_row(self,parent,label,key):
  f=ttk.Frame(parent);f.pack(fill='x',pady=3);ttk.Label(f,text=label,width=24).pack(side='left');v=tk.StringVar();ttk.Entry(f,textvariable=v).pack(side='left',fill='x',expand=True);self.ev[key]=v
 def path_row(self,parent,label,key,video=False):
  f=ttk.Frame(parent);f.pack(fill='x',pady=3);ttk.Label(f,text=label,width=24).pack(side='left');v=tk.StringVar();ttk.Entry(f,textvariable=v).pack(side='left',fill='x',expand=True);ttk.Button(f,text='Browse…',command=lambda:self.pick(v,video)).pack(side='left',padx=3);self.ev[key]=v
 def combo_row(self,parent,label,var,values):
  f=ttk.Frame(parent);f.pack(fill='x',pady=3);ttk.Label(f,text=label,width=24).pack(side='left');ttk.Combobox(f,textvariable=var,values=values,state='readonly').pack(side='left',fill='x',expand=True)
 def make_theme(self):
  controls=ttk.LabelFrame(self.theme_tab,text='Theme controls',padding=8);controls.pack(side='left',fill='y');self.template=tk.StringVar(value='Classic Blue');c=ttk.Combobox(controls,textvariable=self.template,values=list(TEMPLATES),state='readonly');c.pack(fill='x');c.bind('<<ComboboxSelected>>',lambda e:self.apply_template());self.colors={}
  for name,key in [('Background','background'),('Header','header'),('Selection','selection'),('Text','text'),('Muted text','muted'),('Border','border')]:
   f=ttk.Frame(controls);f.pack(fill='x',pady=3);ttk.Label(f,text=name,width=15).pack(side='left');v=tk.StringVar(value=self.theme[key]);ttk.Entry(f,textvariable=v,width=10).pack(side='left');ttk.Button(f,text='…',width=3,command=lambda v=v:self.color(v)).pack(side='left');v.trace_add('write',lambda *_,v=v:self.theme_changed());self.colors[key]=v
  self.header_var=tk.StringVar(value=self.theme['headerTitle']);self.footer_var=tk.StringVar(value=self.theme['footerText']);self.simple_entry(controls,'Header title',self.header_var);self.simple_entry(controls,'Footer text',self.footer_var);self.menu_bg_mode=tk.StringVar(value='stock');self.combo_row(controls,'Menu background',self.menu_bg_mode,['stock','image','per_episode']);self.menu_bg_mode.trace_add('write',lambda *_:self.theme_changed());fbg=ttk.Frame(controls);fbg.pack(fill='x',pady=3);self.menu_bg_path=tk.StringVar();ttk.Entry(fbg,textvariable=self.menu_bg_path).pack(side='left',fill='x',expand=True);ttk.Button(fbg,text='Browse…',command=lambda:self.pick(self.menu_bg_path)).pack(side='left');self.menu_bg_path.trace_add('write',lambda *_:self.theme_changed());self.visibility_vars={};vf=ttk.LabelFrame(controls,text='Visible menu elements',padding=4);vf.pack(fill='x',pady=6)
  visibility_items=[('Header / title','header'),('Episode text','episode_text'),('Selection highlight','selection'),('Thumbnail','thumbnail'),('Thumbnail border','thumbnail_border'),('Footer','footer')]
  for idx,(label,key) in enumerate(visibility_items):
   v=tk.BooleanVar(value=True);ttk.Checkbutton(vf,text=label,variable=v,command=self.theme_changed).grid(row=idx%3,column=idx//3,sticky='w',padx=(0,12));self.visibility_vars[key]=v
  ttk.Label(controls,text='Advanced JSON').pack(anchor='w',pady=(10,2));self.theme_json=tk.Text(controls,width=38,height=13,font=('TkFixedFont',8));self.theme_json.pack();ttk.Button(controls,text='Apply JSON',command=self.apply_json).pack(fill='x',pady=4)
  view=ttk.LabelFrame(self.theme_tab,text='240 × 160 preview',padding=8);view.pack(side='left',fill='both',expand=True,padx=10);self.canvas=tk.Canvas(view,width=480,height=320,bg='black',highlightthickness=1);self.canvas.pack(expand=True);self.overlay_var=tk.StringVar(value='PAUSED');ttk.Combobox(view,textvariable=self.overlay_var,values=list(MESSAGES.values()),state='readonly').pack();ttk.Button(view,text='Preview overlay',command=lambda:self.draw_preview(self.overlay_var.get())).pack()
 def simple_entry(self,p,label,var):ttk.Label(p,text=label).pack(anchor='w');ttk.Entry(p,textvariable=var).pack(fill='x');var.trace_add('write',lambda *_:self.theme_changed())
 def make_subtitles(self):
  f=ttk.LabelFrame(self.subtitle_tab,text='Album-wide subtitle style',padding=10);f.pack(side='left',fill='y');self.sub_vars={}
  for label,key,values in [('Font','font',['Compact 5x7']),('Position','position',['top','middle','bottom','bottom_safe']),('Alignment','align',['left','center']),('Effect','effect',['none','outline','shadow','panel','dithered_panel']),('Outline thickness','thickness',['1','2']),('Maximum lines','max_lines',['1','2','3'])]:
   v=tk.StringVar(value=str(self.subtitle_style[key]));self.sub_vars[key]=v;self.combo_row(f,label,v,values);v.trace_add('write',lambda *_:self.subtitle_changed())
  for label,key in [('Text colour','text_color'),('Effect colour','effect_color'),('Panel colour','panel_color')]:
   r=ttk.Frame(f);r.pack(fill='x',pady=3);ttk.Label(r,text=label,width=24).pack(side='left');v=tk.StringVar(value=self.subtitle_style[key]);self.sub_vars[key]=v;ttk.Entry(r,textvariable=v,width=10).pack(side='left');ttk.Button(r,text='…',command=lambda v=v:self.color(v)).pack(side='left');v.trace_add('write',lambda *_:self.subtitle_changed())
  ttk.Button(f,text='Preview subtitle',command=lambda:self.draw_preview('SUBTITLE STYLE PREVIEW')).pack(fill='x',pady=10);ttk.Label(self.subtitle_tab,text='VTT/SRT timing remains tied to the audio clock.\nStyle is shared by all episodes.',justify='left').pack(side='left',anchor='n',padx=14)
 def subtitle_changed(self):
  try:
   for k,v in self.sub_vars.items():self.subtitle_style[k]=0 if k=='font' else (int(v.get()) if k in ('thickness','max_lines') and v.get().isdigit() else v.get())
  except Exception:pass
 def make_screens(self):
  canvas=tk.Canvas(self.screens,highlightthickness=0,background='#d4d0c8');bar=ttk.Scrollbar(self.screens,orient='vertical',command=canvas.yview);canvas.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True);inner=ttk.Frame(canvas,padding=4);win=canvas.create_window((0,0),window=inner,anchor='nw');inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width));canvas.bind('<MouseWheel>',lambda e:canvas.yview_scroll(int(-e.delta/120),'units'))
  ttk.Label(inner,text='Global menu audio, animated-image defaults, and the startup splash sequence.').pack(anchor='w');mf=ttk.LabelFrame(inner,text='Default menu music',padding=5);mf.pack(fill='x',pady=5);self.menu_music=tk.StringVar();ttk.Entry(mf,textvariable=self.menu_music).pack(side='left',fill='x',expand=True);ttk.Button(mf,text='Browse…',command=lambda:self.pick(self.menu_music,'audio')).pack(side='left');opts=ttk.LabelFrame(inner,text='Animated GIF defaults',padding=6);opts.pack(fill='x',pady=6);self.gif_fps=tk.DoubleVar(value=4);self.gif_seconds=tk.DoubleVar(value=10);ttk.Label(opts,text='Frames per second (1–10)').grid(row=0,column=0,sticky='w');ttk.Spinbox(opts,from_=1,to=10,textvariable=self.gif_fps,width=7).grid(row=0,column=1);ttk.Label(opts,text='Maximum loop seconds').grid(row=0,column=2,padx=(20,0));ttk.Spinbox(opts,from_=1,to=60,textvariable=self.gif_seconds,width=7).grid(row=0,column=3)
  ttk.Label(inner,text='Startup splash sequence',font=('TkDefaultFont',9,'bold')).pack(anchor='w',pady=(10,2));self.splash_rows=ttk.Frame(inner);self.splash_rows.pack(fill='x',pady=4);ttk.Button(inner,text='Add startup splash',command=self.add_splash).pack(anchor='w',pady=(0,8));self.refresh_splashes()
 def pick(self,var,video=False):
  if video=='subs':types=[('Subtitle files','*.vtt *.srt'),('All files','*')]
  elif video=='audio':types=[('Audio files','*.wav *.mp3 *.ogg *.flac *.m4a *.aac *.opus'),('Media files','*.mp4 *.mkv *.mov'),('All files','*')]
  elif video:types=[('Video files','*.mp4 *.mkv *.avi *.mov *.txt'),('All files','*')]
  else:types=[('Images','*.png *.jpg *.jpeg *.bmp *.gif'),('All files','*')]
  p=filedialog.askopenfilename(filetypes=types);var.set(p or var.get())
 def color(self,var):c=colorchooser.askcolor(var.get(),parent=self)[1];var.set(c or var.get())
 def apply_template(self):self.theme=dict(TEMPLATES[self.template.get()]);self.theme['messages']=dict(MESSAGES);self.refresh_theme();self.draw_preview()
 def theme_changed(self):
  try:
   for k,v in self.colors.items():self.theme[k]=v.get()
   self.theme['headerTitle']=self.header_var.get();self.theme['footerText']=self.footer_var.get();self.theme['menu_background']={'mode':self.menu_bg_mode.get(),'image':self.menu_bg_path.get(),'fit':'cover'};self.theme['visibility']={k:v.get() for k,v in self.visibility_vars.items()};self.theme_json.delete('1.0','end');self.theme_json.insert('1.0',json.dumps(self.theme,indent=2));self.draw_preview()
  except Exception:pass
 def refresh_theme(self):
  for k,v in self.colors.items():v.set(self.theme[k]);self.header_var.set(self.theme['headerTitle']);self.footer_var.set(self.theme['footerText']);mb=self.theme.get('menu_background',{});self.menu_bg_mode.set(mb.get('mode','stock'));self.menu_bg_path.set(mb.get('image',''));vis=self.theme.get('visibility',{});[v.set(vis.get(k,True)) for k,v in self.visibility_vars.items()];self.theme_json.delete('1.0','end');self.theme_json.insert('1.0',json.dumps(self.theme,indent=2))
 def apply_json(self):
  try:self.theme=json.loads(self.theme_json.get('1.0','end'));self.refresh_theme();self.draw_preview()
  except Exception as e:messagebox.showerror('Theme JSON',str(e))
 def draw_preview(self,overlay=''):
  if not hasattr(self,'canvas'):return
  c=self.canvas;c.delete('all');S=2;vis=self.theme.get('visibility',{});mode=self.theme.get('menu_background',{}).get('mode','stock');path=''
  if mode=='image':path=self.theme.get('menu_background',{}).get('image','')
  elif mode=='per_episode' and self.episodes:path=self.episodes[self.current].get('menu_background','')
  self.preview_photo=None
  if path and Path(path).exists():
   try:
    from PIL import Image,ImageTk
    self.preview_photo=ImageTk.PhotoImage(Image.open(path).convert('RGB').resize((480,320)));c.create_image(0,0,image=self.preview_photo,anchor='nw')
   except Exception:c.create_rectangle(0,0,480,320,fill=self.theme.get('background','#081830'),outline='')
  else:c.create_rectangle(0,0,480,320,fill=self.theme.get('background','#081830'),outline='')
  if vis.get('header',True):c.create_rectangle(0,0,480,32,fill=self.theme.get('header','#182c54'),outline='');c.create_text(16,9,text=self.theme.get('headerTitle','GBA LONGPLAY'),fill=self.theme.get('text','#fff'),anchor='nw',font=('TkFixedFont',12,'bold'))
  t=self.theme.get('thumb',{'x':152,'y':24,'w':80,'h':48})
  if vis.get('thumbnail',True):
   if vis.get('thumbnail_border',True):c.create_rectangle((t['x']-1)*S,(t['y']-1)*S,(t['x']+t['w']+1)*S,(t['y']+t['h']+1)*S,outline=self.theme.get('border','#fff'),width=2)
   c.create_rectangle(t['x']*S,t['y']*S,(t['x']+t['w'])*S,(t['y']+t['h'])*S,fill=self.theme.get('header','#182c54'),outline='')
  l=self.theme.get('list',{'x':4,'y':81,'row':16})
  for i,e in enumerate(self.episodes):
   y=(l['y']+i*l['row'])*S
   if i==self.current and vis.get('selection',True):c.create_rectangle(l['x']*S,y-6,472,y+20,fill=self.theme.get('selection','#38589c'),outline='')
   if vis.get('episode_text',True):c.create_text((l['x']+6)*S,y,text=e['title'],fill=self.theme.get('text' if i==self.current else 'muted','#fff'),anchor='nw',font=('TkFixedFont',10,'bold'))
  if vis.get('footer',True):c.create_text(16,302,text=self.theme.get('footerText','A PLAY'),fill=self.theme.get('muted','#aaa'),anchor='nw',font=('TkFixedFont',8))
  if overlay:c.create_rectangle(0,288,480,312,fill=self.theme.get('overlay',{}).get('background','#081020'),outline=self.theme.get('border','#fff'));c.create_text(240,300,text=overlay,fill=self.theme.get('overlay',{}).get('text','#fff'),font=('TkFixedFont',10,'bold'))
 def intro_changed(self):
  enabled=self.intro_enabled.get();self.intro_combo.configure(state='readonly' if enabled else 'disabled')
  if enabled:
   for i,e in enumerate(self.episodes):
    if i!=self.current:e['startup_intro']=False
 def commit_episode(self):
  if not self.episodes:return
  e=self.episodes[self.current];e['title']=self.ev['title'].get();e['source']=self.ev['source'].get();e['subtitles']=self.ev['subtitles'].get();e['startup_intro']=self.intro_enabled.get();e['intro_position']=max(0,self.intro_combo.current());e['menu_background']=self.ev['menu_background'].get();
  try:e['thumbnail_time']=float(self.ev['thumbnail_time'].get())
  except:e['thumbnail_time']=5
  e['preplay']={'enabled':self.pre_enabled.get(),'image':self.ev['pre_image'].get(),'mode':self.pre_mode.get() or 'wait','duration':float(self.ev['pre_duration'].get() or 3),'fade':self.pre_fade.get(),'music':{'file':self.ev['pre_music'].get(),'mode':'loop'} if self.ev['pre_music'].get() else None};e['description']={'enabled':self.desc_enabled.get(),'background':self.ev['desc_image'].get(),'fade':self.desc_fade.get(),'music':{'file':self.ev['desc_music'].get(),'mode':'loop'} if self.ev['desc_music'].get() else None,'title':self.ev['desc_title'].get(),'body':self.desc_body.get('1.0','end').strip(),'text_rect':[12,24,216,112]}
 def load_episode(self,i):
  if not self.episodes:return
  self.current=i;e=self.episodes[i];self.ev['title'].set(e['title']);self.ev['source'].set(e.get('source',''));self.ev['subtitles'].set(e.get('subtitles',''));self.intro_enabled.set(e.get('startup_intro',False));self.intro_position.set(['Before all splashes','After Splash 1','After Splash 2','After Splash 3 / before menu'][min(3,e.get('intro_position',2))]);self.intro_changed();self.ev['menu_background'].set(e.get('menu_background',''));self.ev['thumbnail_time'].set(str(e.get('thumbnail_time',5)));pre=e.get('preplay',{});self.pre_enabled.set(pre.get('enabled',False));self.pre_fade.set(pre.get('fade',False));self.ev['pre_image'].set(pre.get('image',''));self.ev['pre_music'].set((pre.get('music') or {}).get('file',''));self.pre_mode.set(pre.get('mode','wait'));self.ev['pre_duration'].set(str(pre.get('duration',3)));d=e.get('description',{});self.desc_enabled.set(d.get('enabled',False));self.desc_fade.set(d.get('fade',False));self.ev['desc_image'].set(d.get('background',''));self.ev['desc_music'].set((d.get('music') or {}).get('file',''));self.ev['desc_title'].set(d.get('title',e['title']));self.desc_body.delete('1.0','end');self.desc_body.insert('1.0',d.get('body',''));self.refresh_list();self.draw_preview()
 def choose_episode(self,_=None):
  sel=self.list.curselection();
  if sel:self.commit_episode();self.load_episode(sel[0])
 def refresh_list(self):self.list.delete(0,'end');[self.list.insert('end',e['title']) for e in self.episodes];self.list.selection_set(self.current)
 def add_episode(self):
  if len(self.episodes)>=4:return
  self.commit_episode();self.episodes.append(episode(len(self.episodes)+1));self.load_episode(len(self.episodes)-1)
 def remove_episode(self):
  if len(self.episodes)<=1:return
  self.episodes.pop(self.current);self.load_episode(min(self.current,len(self.episodes)-1))
 def add_splash(self):
  if len(self.splashes)<3:self.splashes.append({'enabled':True,'image':'','music':None,'mode':'timed_skippable','duration':3,'fade':False});self.refresh_splashes()
 def refresh_splashes(self):
  for w in self.splash_rows.winfo_children():w.destroy()
  for i,s in enumerate(self.splashes):
   f=ttk.LabelFrame(self.splash_rows,text=f'Splash {i+1}',padding=5);f.pack(fill='x',pady=4);en=tk.BooleanVar(value=s['enabled']);ttk.Checkbutton(f,text='Enabled',variable=en,command=lambda s=s,en=en:s.update(enabled=en.get())).grid(row=0,column=0);fade=tk.BooleanVar(value=s.get('fade',False));ttk.Checkbutton(f,text='Fade in/out',variable=fade,command=lambda s=s,fade=fade:s.update(fade=fade.get())).grid(row=0,column=1);v=tk.StringVar(value=s['image']);ttk.Entry(f,textvariable=v,width=48).grid(row=1,column=0,columnspan=3,sticky='ew');ttk.Button(f,text='Browse…',command=lambda v=v:self.pick(v)).grid(row=1,column=3);m=tk.StringVar(value=s['mode']);ttk.Combobox(f,textvariable=m,values=['timed','wait','timed_skippable'],width=18,state='readonly').grid(row=2,column=0);d=tk.StringVar(value=str(s['duration']));ttk.Entry(f,textvariable=d,width=8).grid(row=2,column=1);ttk.Button(f,text='Remove',command=lambda i=i:self.remove_splash(i)).grid(row=2,column=3);mv=tk.StringVar(value=(s.get('music') or {}).get('file',''));ttk.Label(f,text='Music').grid(row=3,column=0);ttk.Entry(f,textvariable=mv).grid(row=3,column=1,columnspan=2,sticky='ew');ttk.Button(f,text='Browse…',command=lambda mv=mv:self.pick(mv,'audio')).grid(row=3,column=3);mv.trace_add('write',lambda *_,s=s,mv=mv:s.update(music={'file':mv.get(),'mode':'loop'} if mv.get() else None));v.trace_add('write',lambda *_,s=s,v=v:s.update(image=v.get()));m.trace_add('write',lambda *_,s=s,m=m:s.update(mode=m.get()));d.trace_add('write',lambda *_,s=s,d=d:s.update(duration=float(d.get() or 0)))
 def remove_splash(self,i):self.splashes.pop(i);self.refresh_splashes()
 def project_data(self):
  self.commit_episode();return {'project':{'rom_mib':64,'reserve_mib':1.0,'fps':10,'vq':True,'vq_fps':1,'vq_samples':80000,'vq_edge_fraction':.5,'gif_fps':self.gif_fps.get(),'gif_seconds':self.gif_seconds.get(),'menu_music':{'file':self.menu_music.get(),'mode':'loop'} if self.menu_music.get() else None,'splashes':self.splashes,'subtitle_style':self.subtitle_style,'episodes':self.episodes},'theme':self.theme}
 def new(self):self.episodes=[episode(1),episode(2)];self.splashes=[];self.theme=dict(TEMPLATES['Classic Blue']);self.theme['messages']=dict(MESSAGES);self.load_episode(0);self.refresh_splashes();self.refresh_theme()
 def save_project(self):
  p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('GLP project','*.json')]);
  if p:Path(p).write_text(json.dumps(self.project_data(),indent=2))
 def open_project(self):
  p=filedialog.askopenfilename(filetypes=[('GLP project','*.json')]);
  if not p:return
  c=json.loads(Path(p).read_text());self.episodes=c['project']['episodes'];self.splashes=c['project'].get('splashes',[]);self.gif_fps.set(c['project'].get('gif_fps',4));self.gif_seconds.set(c['project'].get('gif_seconds',10));self.menu_music.set((c['project'].get('menu_music') or {}).get('file',''));self.subtitle_style=c['project'].get('subtitle_style',self.subtitle_style);self.theme=c.get('theme',dict(TEMPLATES['Classic Blue']));self.load_episode(0);self.refresh_splashes();self.refresh_theme();[v.set(str(self.subtitle_style.get(k,0))) for k,v in self.sub_vars.items() if k!='font'];self.sub_vars['font'].set('Compact 5x7')
 def build(self):
  if self.building:return
  ff=locate_ffmpeg();
  if not ff:messagebox.showerror('FFmpeg missing','Install FFmpeg or place it in converter/vendor/.');return
  out=filedialog.asksaveasfilename(defaultextension='.gba',filetypes=[('GBA ROM','*.gba')]);
  if not out:return
  cfg=self.project_data();reuse=self.reuse_var.get();self.building=True;self.nb.select(self.build_tab);self.log.delete('1.0','end');threading.Thread(target=self.build_worker,args=(out,ff,cfg,reuse),daemon=True).start()
 def build_worker(self,out,ff,cfg,reuse):
  try:
   manifest=WORK/'desktop-project.json';manifest.write_text(json.dumps({**cfg['project'],'theme':cfg['theme']},indent=2));album=WORK/'desktop-album.gla';env=os.environ.copy();env['PATH']=str(Path(ff).parent)+os.pathsep+env.get('PATH','')
   encode_cmd=[sys.executable,str(ROOT/'tools/build_album_manifest.py'),str(manifest),'-o',str(album),'--work-dir',str(WORK/'encoded')]
   if reuse:encode_cmd.append('--reuse')
   cmds=[encode_cmd,[sys.executable,str(ROOT/'tools/pack_precompiled.py'),str(album),'-o',out]]
   for cmd in cmds:
    self.q.put(('log','$ '+' '.join(cmd)));p=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    for line in p.stdout:self.q.put(('log',line.rstrip()))
    if p.wait():raise RuntimeError('Build command failed')
   self.q.put(('done',out))
  except Exception as e:self.q.put(('error',str(e)))
 def pump(self):
  try:
   while True:
    k,v=self.q.get_nowait()
    if k=='log':self.log.insert('end',v+'\n');self.log.see('end');self.status.config(text=v[-70:])
    elif k=='done':self.building=False;self.status.config(text='ROM complete');messagebox.showinfo('GLP Studio',f'ROM created:\n{v}')
    else:self.building=False;self.status.config(text='Build failed');messagebox.showerror('Build failed',v)
  except queue.Empty:pass
  self.after(100,self.pump)
def check():
 print(json.dumps({'tk':tk.TkVersion,'ffmpeg':locate_ffmpeg(),'template':(ROOT/'converter/templates/matrix64-template.json').exists(),'root':str(ROOT)},indent=2))
if __name__=='__main__':
 if '--check'in sys.argv:check()
 else:App().mainloop()
