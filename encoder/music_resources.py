"""GMR1 deduplicated album music resource table."""
from __future__ import annotations
import hashlib,struct,zlib
MAGIC=b'GMR1';VERSION=1;HEADER_SIZE=20;ENTRY=struct.Struct('<IIII')
def build(tracks:list[bytes])->tuple[bytes,list[int]]:
 unique=[];ids=[];seen={}
 for b in tracks:
  if not b:ids.append(0);continue
  key=hashlib.sha256(b).digest()
  if key not in seen:seen[key]=len(unique)+1;unique.append(b)
  ids.append(seen[key])
 table=HEADER_SIZE+len(unique)*ENTRY.size;payload=bytearray();entries=[]
 for i,b in enumerate(unique,1):off=table+len(payload);entries.append(ENTRY.pack(i,off,len(b),0));payload+=b
 total=table+len(payload);head=bytearray(struct.pack('<4sHHIII',MAGIC,VERSION,HEADER_SIZE,total,len(unique),0));blob=head+b''.join(entries)+payload;struct.pack_into('<I',blob,16,zlib.crc32(blob)&0xffffffff);return bytes(blob),ids
def parse(data:bytes)->dict:
 if len(data)<HEADER_SIZE:raise ValueError('short GMR1')
 magic,ver,hs,total,count,crc=struct.unpack_from('<4sHHIII',data)
 if magic!=MAGIC or ver!=VERSION or hs!=HEADER_SIZE or total>len(data):raise ValueError('bad GMR1')
 tmp=bytearray(data[:total]);struct.pack_into('<I',tmp,16,0)
 if zlib.crc32(tmp)&0xffffffff!=crc:raise ValueError('GMR1 CRC')
 tracks={}
 for i in range(count):
  ident,off,n,flags=ENTRY.unpack_from(data,hs+i*ENTRY.size)
  if not ident or off+n>total:raise ValueError('track outside GMR1')
  tracks[ident]={'offset':off,'size':n,'flags':flags,'data':data[off:off+n]}
 return {'tracks':tracks,'total_size':total,'crc32':crc}
