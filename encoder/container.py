"""GLV2 single-episode, timestamped A/V container.

Offsets are absolute file/image offsets. Audio chunks overlap by 16 samples so
GBA FIFO look-ahead can remain uninterrupted while DMA changes source buffers.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import struct, zlib

MAGIC=b"GLV2"; VERSION=2; HEADER_SIZE=64; TIMEBASE=8192
FLAG_LOOP=1; FLAG_CODEBOOK=2; FLAG_SUBTITLES=4
HEADER=struct.Struct("<4sHHHH13I")
VIDEO_INDEX=struct.Struct("<III")       # pts, offset, bytes
AUDIO_INDEX=struct.Struct("<IIII")      # pts, logical samples, offset, bytes
WIDTH=240; HEIGHT=160

@dataclass
class VideoPacket:
    pts:int
    data:bytes
@dataclass
class AudioPacket:
    pts:int
    samples:int
    data:bytes


def build(video:list[VideoPacket],audio:list[AudioPacket],fps_num:int=10,fps_den:int=1,
          audio_chunk_samples:int=32768,flags:int=0,codebook:bytes=b'',audio_gain_q8:int=256,subtitles:bytes=b'')->bytes:
    if codebook and (len(codebook)%16 or len(codebook)>4096):
        raise ValueError('codebook must contain up to 256 16-byte patterns')
    vi_off=HEADER_SIZE
    ai_off=vi_off+len(video)*VIDEO_INDEX.size
    data_off=ai_off+len(audio)*AUDIO_INDEX.size
    cursor=data_off+len(codebook)+len(subtitles); vi=[]; ai=[]; payload=bytearray(codebook+subtitles)
    if codebook: flags|=FLAG_CODEBOOK
    if subtitles: flags|=FLAG_SUBTITLES
    for p in video:
        vi.append(VIDEO_INDEX.pack(p.pts,cursor,len(p.data)));payload+=p.data;cursor+=len(p.data)
    for p in audio:
        ai.append(AUDIO_INDEX.pack(p.pts,p.samples,cursor,len(p.data)));payload+=p.data;cursor+=len(p.data)
    video_end=(video[-1].pts + TIMEBASE*fps_den//fps_num) if video else 0
    audio_end=max((p.pts+p.samples for p in audio),default=0)
    duration=max(video_end,audio_end)
    values=(MAGIC,VERSION,HEADER_SIZE,WIDTH,HEIGHT,TIMEBASE,fps_num,fps_den,duration,
            len(video),len(audio),audio_chunk_samples,vi_off,ai_off,data_off,flags,(audio_gain_q8<<16)|(len(codebook)//16),0)
    header=bytearray(HEADER.pack(*values))
    body=b''.join(vi)+b''.join(ai)+payload
    crc=zlib.crc32(header+body)&0xffffffff
    struct.pack_into("<I",header,HEADER_SIZE-4,crc)
    return bytes(header)+body


def parse(data:bytes,verify_crc:bool=True)->dict:
    if len(data)<HEADER_SIZE:raise ValueError("short GLV2")
    v=HEADER.unpack_from(data)
    if v[0]!=MAGIC or v[1]!=VERSION or v[2]!=HEADER_SIZE:raise ValueError("bad GLV2 header")
    (_,version,hsize,w,h,timebase,fpsn,fpsd,duration,nv,na,chunk,vi,ai,doff,flags,packed_meta,crc)=v
    codebook_count=packed_meta&0xffff;audio_gain_q8=(packed_meta>>16) or 256
    if verify_crc:
        tmp=bytearray(data);struct.pack_into("<I",tmp,HEADER_SIZE-4,0)
        if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError("GLV2 CRC mismatch")
    cb_bytes=codebook_count*16
    if codebook_count>256 or doff+cb_bytes>len(data):raise ValueError('bad codebook')
    codebook=data[doff:doff+cb_bytes] if flags&FLAG_CODEBOOK else b''
    subtitles=b''
    if flags&FLAG_SUBTITLES:
        suboff=doff+cb_bytes
        if suboff+24>len(data) or data[suboff:suboff+4]!=b'GLU1':raise ValueError('bad subtitles')
        subsize=struct.unpack_from('<I',data,suboff+8)[0]
        if suboff+subsize>len(data):raise ValueError('subtitles outside file')
        subtitles=data[suboff:suboff+subsize]
    videos=[];audios=[]
    for i in range(nv):
        pts,off,n=VIDEO_INDEX.unpack_from(data,vi+i*VIDEO_INDEX.size)
        if off+n>len(data):raise ValueError("video packet outside file")
        videos.append(VideoPacket(pts,data[off:off+n]))
    for i in range(na):
        pts,samples,off,n=AUDIO_INDEX.unpack_from(data,ai+i*AUDIO_INDEX.size)
        if off+n>len(data):raise ValueError("audio packet outside file")
        audios.append(AudioPacket(pts,samples,data[off:off+n]))
    return {"version":version,"width":w,"height":h,"timebase":timebase,"fps_num":fpsn,
            "fps_den":fpsd,"duration":duration,"audio_chunk_samples":chunk,"flags":flags,
            "video":videos,"audio":audios,"codebook":codebook,"subtitles":subtitles,"audio_gain_q8":audio_gain_q8,"crc32":crc}


def write(path:str|Path,*args,**kwargs)->None:Path(path).write_bytes(build(*args,**kwargs))
def read(path:str|Path,verify_crc:bool=True)->dict:return parse(Path(path).read_bytes(),verify_crc)
