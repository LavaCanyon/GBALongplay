"""GLT1 fixed-size menu/action-overlay theme compiler."""
from __future__ import annotations
import struct,zlib
MAGIC=b'GLT1';VERSION=1;SIZE=320
MESSAGE_KEYS=('paused','resuming','rewinding','forwarding','chapter','locked','unlocked','brightness_up','brightness_down')
# Contrast messages share the brightness text slots only in the first draft? No: fit all 11 messages.
MESSAGE_KEYS=('paused','resuming','rewinding','forwarding','chapter','locked','unlocked','brightness_up','brightness_down','contrast_up','contrast_down')

def rgb332(value:str)->int:
 s=value.lstrip('#');
 if len(s)!=6:raise ValueError(f'bad colour {value}')
 n=int(s,16);r=n>>16;g=n>>8&255;b=n&255;return ((r*7+127)//255<<5)|((g*7+127)//255<<2)|((b*3+127)//255)
def text(value,n):
 b=str(value).upper().encode('ascii','replace')[:n-1];return b+b'\0'*(n-len(b))
def compile_theme(t:dict,menu_background:bytes=b'')->bytes:
 ep=t.get('episode_list',t.get('list',{}));th=t.get('thumbnail',t.get('thumb',{}));ov=t.get('overlay',{});footer=t.get('footer',{});bg=t.get('background',{});msg=t.get('messages',{})
 colors=[rgb332(bg.get('color',t.get('background','#081830')) if isinstance(bg,dict) else bg),rgb332(t.get('header','#182c54')),rgb332(ep.get('selected_background',t.get('selection','#38589c'))),rgb332(ep.get('selected_text',t.get('text','#ffffff'))),rgb332(ep.get('normal_text',t.get('muted','#b5bdcf'))),rgb332(th.get('border_color',t.get('border','#ffffff'))),rgb332(ov.get('background','#081020')),rgb332(ov.get('text','#ffffff'))]
 coords=[8,5,int(ep.get('x',4)),int(ep.get('y',81)),int(ep.get('row_height',ep.get('row',16))),int(ep.get('text_x',10)),int(th.get('x',152)),int(th.get('y',24)),int(th.get('width',th.get('w',80))),int(th.get('height',th.get('h',48))),int(footer.get('x',8)),int(footer.get('y',151)),int(ov.get('x',0)),int(ov.get('y',144)),int(ov.get('width',240)),int(ov.get('height',12))]
 coords=[max(0,min(255,x)) for x in coords];out=bytearray(SIZE);out[:8]=struct.pack('<4sHH',MAGIC,VERSION,SIZE);out[8:16]=bytes(colors);out[16:32]=bytes(coords);struct.pack_into('<H',out,32,int(ov.get('duration_frames',ov.get('duration',90))));out[36:60]=text(t.get('headerTitle',t.get('header_title','GBA LONGPLAY')),24);out[60:92]=text(footer.get('text',t.get('footerText','A PLAY   UP DOWN SELECT')),32)
 defaults={'paused':'PAUSED','resuming':'RESUMING','rewinding':'REWINDING','forwarding':'FORWARDING','chapter':'CHAPTER {number}','locked':'BUTTONS LOCKED','unlocked':'BUTTONS UNLOCKED','brightness_up':'BRIGHTNESS UP','brightness_down':'BRIGHTNESS DOWN','contrast_up':'CONTRAST UP','contrast_down':'CONTRAST DOWN'}
 p=92
 for k in MESSAGE_KEYS:out[p:p+20]=text(msg.get(k,defaults[k]),20);p+=20
 vis=t.get('visibility',{});names=('header','episode_text','selection','thumbnail','thumbnail_border','footer');out[34]=sum((1<<i) for i,n in enumerate(names) if vis.get(n,True));mode=t.get('menu_background',{}).get('mode','stock');out[35]={'stock':0,'image':1,'per_episode':2}.get(mode,0)
 if menu_background:struct.pack_into('<I',out,312,SIZE)
 blob=out+menu_background;struct.pack_into('<I',blob,SIZE-4,0);struct.pack_into('<I',blob,SIZE-4,zlib.crc32(blob)&0xffffffff);return bytes(blob)
def parse_theme(data:bytes)->dict:
 if len(data)<SIZE:raise ValueError('short GLT1')
 magic,ver,size=struct.unpack_from('<4sHH',data)
 if magic!=MAGIC or ver!=VERSION or size!=SIZE:raise ValueError('bad GLT1 header')
 bg_off=struct.unpack_from('<I',data,312)[0];total=len(data);tmp=bytearray(data[:total]);crc=struct.unpack_from('<I',tmp,SIZE-4)[0];struct.pack_into('<I',tmp,SIZE-4,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GLT1 CRC mismatch')
 msgs={};p=92
 for k in MESSAGE_KEYS:msgs[k]=data[p:p+20].split(b'\0',1)[0].decode('ascii');p+=20
 names=('header','episode_text','selection','thumbnail','thumbnail_border','footer');visibility={n:bool(data[34]&(1<<i)) for i,n in enumerate(names)}
 return {'colors':list(data[8:16]),'coords':list(data[16:32]),'overlay_duration':struct.unpack_from('<H',data,32)[0],'header_title':data[36:60].split(b'\0',1)[0].decode('ascii'),'footer':data[60:92].split(b'\0',1)[0].decode('ascii'),'messages':msgs,'visibility':visibility,'background_mode':data[35],'menu_background':data[bg_off:] if bg_off else b'','crc32':crc}
