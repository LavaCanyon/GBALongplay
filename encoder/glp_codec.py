"""Reference GLV block-video codec.

This is intentionally straightforward, deterministic Python. It establishes the
bitstream used by the GBA decoder; optimization belongs in the player, not here.
Pixels are RGB332 palette indices and frames are 240x160.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

WIDTH, HEIGHT, BLOCK = 240, 160, 8
BX, BY = WIDTH // BLOCK, HEIGHT // BLOCK
BLOCKS = BX * BY
MASK_BYTES = (BLOCKS + 7) // 8
FRAME_HEADER = struct.Struct("<4sIHHI")  # magic, number, flags, changed, payload bytes
KEYFRAME = 1
SPARSE = 2


def rgb_to_332(rgb: bytes) -> bytearray:
    if len(rgb) != WIDTH * HEIGHT * 3:
        raise ValueError(f"expected {WIDTH}x{HEIGHT} RGB24")
    out = bytearray(WIDTH * HEIGHT)
    for i in range(len(out)):
        r, g, b = rgb[i*3:i*3+3]
        out[i] = (r & 0xE0) | ((g & 0xE0) >> 3) | (b >> 6)
    return out


def palette_bgr555() -> bytes:
    out = bytearray()
    for c in range(256):
        r3, g3, b2 = c >> 5, (c >> 2) & 7, c & 3
        r5 = (r3 << 2) | (r3 >> 1)
        g5 = (g3 << 2) | (g3 >> 1)
        b5 = (b2 << 3) | (b2 << 1) | (b2 >> 1)
        out += struct.pack("<H", r5 | (g5 << 5) | (b5 << 10))
    return bytes(out)


def _rgb(c: int) -> tuple[int, int, int]:
    return ((c >> 5) * 255 // 7, ((c >> 2) & 7) * 255 // 7, (c & 3) * 255 // 3)


def _distance_slow(a: int, b: int) -> int:
    ar, ag, ab = _rgb(a); br, bg, bb = _rgb(b)
    return 2*(ar-br)**2 + 3*(ag-bg)**2 + (ab-bb)**2

# Motion search calls the distance function millions of times. RGB332 has only
# 65,536 possible pairs, so a table is both deterministic and much faster.
_DIST = tuple(_distance_slow(a, b) for a in range(256) for b in range(256))
def _dist(a: int, b: int) -> int: return _DIST[(a << 8) | b]


def _block_xy(frame: bytes | bytearray, x0: int, y0: int) -> list[int]:
    return [frame[(y0+y)*WIDTH+x0+x] for y in range(BLOCK) for x in range(BLOCK)]

def _block(frame: bytes | bytearray, bi: int) -> list[int]:
    return _block_xy(frame, (bi % BX) * BLOCK, (bi // BX) * BLOCK)


def _put_block(frame: bytearray, bi: int, px: list[int]) -> None:
    x0, y0 = (bi % BX) * BLOCK, (bi // BX) * BLOCK
    for y in range(BLOCK):
        start = (y0+y)*WIDTH+x0
        frame[start:start+BLOCK] = bytes(px[y*BLOCK:(y+1)*BLOCK])


def _quadrant(px: list[int], q: int) -> list[int]:
    x0=(q&1)*4; y0=(q>>1)*4
    return [px[(y0+y)*8+x0+x] for y in range(4) for x in range(4)]

def _put_quadrant(px: list[int], q: int, patch: list[int]) -> None:
    x0=(q&1)*4; y0=(q>>1)*4
    for y in range(4): px[(y0+y)*8+x0:x0+(y0+y)*8+4] = patch[y*4:(y+1)*4]

def _mse(a: list[int], b: list[int]) -> int:
    return sum(_dist(x, y) for x, y in zip(a, b)) // max(1, len(a))

def _edge_count(px: list[int]) -> int:
    """Count strong internal edges in an 8x8 block for line-art priority."""
    n=0
    for y in range(8):
        for x in range(8):
            i=y*8+x
            if x<7 and _dist(px[i],px[i+1])>10000:n+=1
            if y<7 and _dist(px[i],px[i+8])>10000:n+=1
    return n


def _quantize(px: list[int], k: int) -> tuple[list[int], list[int], int]:
    """Small deterministic weighted k-means in RGB332 space."""
    counts: dict[int, int] = {}
    for c in px: counts[c] = counts.get(c, 0) + 1
    colors = sorted(counts, key=lambda c: (-counts[c], c))
    centers = colors[:k] or [0]
    while len(centers) < k: centers.append(centers[-1])
    for _ in range(4):
        groups = [[] for _ in range(k)]
        for c, n in counts.items():
            j = min(range(k), key=lambda q: (_dist(c, centers[q]), q))
            groups[j].append((c, n))
        nxt = []
        for j, group in enumerate(groups):
            if not group:
                nxt.append(centers[j]); continue
            # Medoid keeps the result representable in RGB332.
            nxt.append(min((c for c, _ in group),
                           key=lambda q: sum(_dist(q, c)*n for c, n in group)))
        centers = nxt
    indices = [min(range(k), key=lambda q: (_dist(c, centers[q]), q)) for c in px]
    recon = [centers[i] for i in indices]
    return centers, indices, _mse(px, recon)


def _pack_indices(indices: list[int], bits: int) -> bytes:
    out = bytearray((len(indices)*bits + 7)//8)
    mask = (1 << bits) - 1
    bit = 0
    for v in indices:
        out[bit >> 3] |= (v & mask) << (bit & 7)
        bit += bits
    return bytes(out)


def _unpack_indices(data: bytes, count: int, bits: int) -> list[int]:
    mask = (1 << bits) - 1
    return [(data[(i*bits) >> 3] >> ((i*bits) & 7)) & mask for i in range(count)]


@dataclass
class Profile:
    skip_error: int = 110
    two_color_error: int = 900
    four_color_error: int = 260
    key_interval: int = 80
    motion_error: int = 3000
    motion_range: int = 2
    patch_limit: int = 0
    solid_error: int = 700
    edge_boost: int = 4
    age_boost: int = 30
    age_cap: int = 12
    transition_boost: int = 20
    motion_edge_tolerance: int = 8
    vq_edge_penalty: int = 4
    vq_fast_error: int = 2500
    vq_fast_edges: int = 10


class Encoder:
    def __init__(self, profile: Profile = Profile(), codebook: bytes = b''):
        self.profile = profile
        self.previous = bytearray(WIDTH * HEIGHT)
        self.number = 0
        self.last_key = -profile.key_interval
        self.ages = [0] * BLOCKS
        self.codebook = [list(codebook[i:i+16]) for i in range(0,len(codebook),16)]
        self._vq_centers = None
        if self.codebook:
            import numpy as np
            pal=np.array([_rgb(i) for i in range(256)],dtype=np.float32)
            book=np.array(self.codebook,dtype=np.uint8)
            self._vq_centers=pal[book].reshape(len(book),48)

    def _vq_labels(self,current:bytes|bytearray):
        if self._vq_centers is None:return None
        import numpy as np
        pal=np.array([_rgb(i) for i in range(256)],dtype=np.float32)
        f=np.frombuffer(bytes(current),dtype=np.uint8).reshape(HEIGHT,WIDTH)
        patches=f.reshape(HEIGHT//4,4,WIDTH//4,4).transpose(0,2,1,3).reshape(-1,16)
        x=pal[patches].reshape(-1,48);c=self._vq_centers
        d=(x*x).sum(1)[:,None]+(c*c).sum(1)[None,:]-2*x@c.T
        return d.argmin(1).reshape(HEIGHT//4,WIDTH//4)

    def key_due(self) -> bool:
        return self.number == 0 or self.number-self.last_key >= self.profile.key_interval

    def advance(self) -> None:
        """Advance source time without changing the reconstructed frame."""
        self.number += 1

    def encode_rgb24(self, rgb: bytes, budget: int | None = None,
                     force_keyframe: bool = False, key_max_colors: int = 0) -> bytes:
        return self.encode_indexed(rgb_to_332(rgb), budget, force_keyframe, key_max_colors)

    def encode_indexed(self, current: bytes | bytearray,
                       budget: int | None = None,
                       force_keyframe: bool = False,
                       key_max_colors: int = 0) -> bytes:
        """Encode one frame.

        ``budget`` is a hard byte ceiling for non-keyframes. Blocks are ranked
        by reconstruction improvement per encoded byte; low-value changes are
        deferred by retaining their previous reconstructed blocks. Keyframes
        intentionally ignore the ceiling so every block is refreshed.
        """
        if len(current) != WIDTH * HEIGHT: raise ValueError("bad frame size")
        key = (force_keyframe or self.number == 0 or
               self.number - self.last_key >= self.profile.key_interval)
        candidates = []
        current_blocks = [_block(current, bi) for bi in range(BLOCKS)]
        previous_blocks = [_block(self.previous, bi) for bi in range(BLOCKS)]
        block_errors = [_mse(current_blocks[bi], previous_blocks[bi]) for bi in range(BLOCKS)]
        vq_labels = self._vq_labels(current)
        for bi in range(BLOCKS):
            src = current_blocks[bi]; old = previous_blocks[bi]
            old_error = block_errors[bi]
            if not key:
                if budget is None and old_error <= self.profile.skip_error: continue
                if budget is not None and old_error == 0: continue
            src_edges = _edge_count(src); old_edges = _edge_count(old)
            if not key and vq_labels is not None:
                bx,by=bi%BX,bi//BX;fast_rec=list(old);fast_mask=0;fast_indices=[]
                for q in range(4):
                    qx,qy=q&1,q>>1;ix=int(vq_labels[by*2+qy,bx*2+qx]);patch=self.codebook[ix]
                    srcq,oldq=_quadrant(src,q),_quadrant(old,q)
                    if _mse(srcq,patch)<_mse(srcq,oldq):
                        fast_mask|=1<<q;fast_indices.append((q,ix,patch))
                if fast_indices:
                    for q,_ix,patch in fast_indices:_put_quadrant(fast_rec,q,patch)
                    fast_error=_mse(src,fast_rec)
                    if fast_error<=self.profile.vq_fast_error and src_edges<=self.profile.vq_fast_edges:
                        fast_record=bytes((6,fast_mask))+bytes(ix for _q,ix,_patch in fast_indices)
                        fast_gain=max(1,old_error-fast_error);edge_factor=100+min(src_edges,40)*self.profile.edge_boost
                        age_factor=100+min(self.ages[bi],self.profile.age_cap)*self.profile.age_boost
                        transition_factor=100+min(abs(src_edges-old_edges),20)*self.profile.transition_boost
                        priority=max(1,fast_gain*edge_factor*age_factor*transition_factor//1000000)
                        candidates.append((bi,fast_record,fast_rec,priority,(fast_record,list(fast_rec),priority)))
                        continue
            unique = set(src)
            c1, _i1, e1 = _quantize(src, 1)
            if len(unique) == 1 or e1 <= self.profile.solid_error:
                record = bytes((0, c1[0])); rec = [c1[0]]*64; rec_error = e1
            else:
                c2, i2, e2 = _quantize(src, 2)
                if key_max_colors == 2 or e2 <= self.profile.two_color_error:
                    record = bytes((1, *c2)) + _pack_indices(i2, 1)
                    rec = [c2[i] for i in i2]; rec_error = e2
                else:
                    c4, i4, e4 = _quantize(src, 4)
                    if e4 <= self.profile.four_color_error:
                        record = bytes((2, *c4)) + _pack_indices(i4, 2)
                        rec = [c4[i] for i in i4]; rec_error = e4
                    else:
                        record = bytes((3,)) + bytes(src); rec = src; rec_error = 0
            gain = max(1, old_error - rec_error)
            fallback = (record, list(rec), gain)
            if not key and vq_labels is not None:
                bx,by=bi%BX,bi//BX;patched=list(old);mask=0;indices=[]
                for q in range(4):
                    qx,qy=q&1,q>>1;ix=int(vq_labels[by*2+qy,bx*2+qx]);patch=self.codebook[ix]
                    srcq,oldq=_quadrant(src,q),_quadrant(old,q)
                    if _mse(srcq,patch)<_mse(srcq,oldq):
                        mask|=1<<q;indices.append((q,ix,patch))
                if indices:
                    for q,_ix,patch in indices:_put_quadrant(patched,q,patch)
                    vq_record=bytes((6,mask))+bytes(ix for _q,ix,_patch in indices)
                    vq_error=_mse(src,patched);vq_gain=max(1,old_error-vq_error)
                    detail_cost=100+min(src_edges,40)*self.profile.vq_edge_penalty
                    if vq_gain*len(record)*100>gain*len(vq_record)*detail_cost:
                        record,rec,rec_error,gain=vq_record,patched,vq_error,vq_gain
            if not key and self.profile.patch_limit != 0:
                patch_options=[]
                for q in range(4):
                    srcq,oldq=_quadrant(src,q),_quadrant(old,q)
                    pal,idx,err=_quantize(srcq,2);patch=[pal[j] for j in idx]
                    qgain=_mse(srcq,oldq)-err
                    if qgain>0:
                        data=bytes((pal[0],pal[1]))+_pack_indices(idx,1)
                        patch_options.append((qgain,q,data,patch))
                patch_options.sort(reverse=True)
                for k in range(1,len(patch_options)+1):
                    chosen=sorted(patch_options[:k],key=lambda x:x[1]);patched=list(old);mask=0;body=bytearray()
                    for _qgain,q,data,patch in chosen:
                        mask|=1<<q;body+=data;_put_quadrant(patched,q,patch)
                    patch_record=bytes((5,mask))+bytes(body)
                    patch_error=_mse(src,patched);patch_gain=max(1,old_error-patch_error)
                    if patch_gain*len(record)>gain*len(patch_record):
                        record,rec,rec_error,gain=patch_record,patched,patch_error,patch_gain
            if not key and self.profile.motion_range:
                bx, by = bi % BX, bi // BX
                x0, y0 = bx*BLOCK, by*BLOCK
                best_error, best_delta, best_rec = old_error, None, None
                r = self.profile.motion_range
                for dy in range(-r, r+1):
                    sy = y0 + dy*4
                    if not 0 <= sy <= HEIGHT-BLOCK: continue
                    for dx in range(-r, r+1):
                        sx = x0 + dx*4
                        if (dx == 0 and dy == 0) or not 0 <= sx <= WIDTH-BLOCK: continue
                        candidate_rec = _block_xy(self.previous, sx, sy)
                        error = _mse(src, candidate_rec)
                        if error < best_error:
                            best_error, best_delta, best_rec = error, (dx, dy), candidate_rec
                motion_gain = old_error - best_error
                if (best_delta is not None and best_error <= self.profile.motion_error and
                        abs(_edge_count(best_rec)-src_edges) <= self.profile.motion_edge_tolerance and
                        motion_gain * len(record) > gain * 3):
                    dx, dy = best_delta
                    record = bytes((4, dx & 255, dy & 255))
                    rec = list(best_rec); rec_error = best_error; gain = max(1, motion_gain)
            edge_factor = 100 + min(src_edges,40)*self.profile.edge_boost
            age_factor = 100 + min(self.ages[bi],self.profile.age_cap)*self.profile.age_boost
            transition_factor = 100 + min(abs(src_edges-old_edges),20)*self.profile.transition_boost
            # Clearing detailed background into a character's flat painted area
            # is a high-value occlusion update, even when the source has few edges.
            if e1 <= self.profile.solid_error and old_error > self.profile.solid_error:
                transition_factor = max(transition_factor, 400)
            priority = gain * edge_factor * age_factor * transition_factor // 1000000
            candidates.append((bi, record, rec, max(1,priority), fallback))

        if not key and self.profile.patch_limit >= 0:
            patch_ranked=sorted((c for c in candidates if c[1][0]==5),
                                key=lambda c:(c[3]/len(c[1]),c[3]),reverse=True)
            keep={c[0] for c in patch_ranked[:self.profile.patch_limit]}
            limited=[]
            for bi,record,rec,gain,fallback in candidates:
                if record[0]==5 and bi not in keep:
                    record,rec,gain=fallback
                limited.append((bi,record,rec,gain,fallback))
            candidates=limited

        if not key and budget is not None:
            available = max(0, budget - FRAME_HEADER.size - MASK_BYTES)
            ranked = sorted(candidates,
                            key=lambda c: (c[3] / len(c[1]), c[3]), reverse=True)
            chosen = []
            for candidate in ranked:
                n = len(candidate[1])
                if n <= available:
                    chosen.append(candidate); available -= n
            candidates = sorted(chosen, key=lambda c: c[0])

        mask = bytearray(MASK_BYTES); records = bytearray()
        reconstructed = bytearray(self.previous)
        for bi, record, rec, _gain, _fallback in candidates:
            mask[bi >> 3] |= 1 << (bi & 7); records += record
            _put_block(reconstructed, bi, rec)
        flags = KEYFRAME if key else 0
        if len(candidates)*2 < MASK_BYTES:
            index_bytes = b''.join(struct.pack('<H', c[0]) for c in candidates)
            payload = index_bytes + bytes(records); flags |= SPARSE
        else:
            payload = bytes(mask + records)
        header = FRAME_HEADER.pack(b"FRM0", self.number, flags,
                                   len(candidates), len(payload))
        selected_blocks = {c[0] for c in candidates}
        for bi in range(BLOCKS):
            if bi in selected_blocks or block_errors[bi] <= self.profile.skip_error:
                self.ages[bi] = 0
            else:
                self.ages[bi] = min(255, self.ages[bi] + 1)
        self.previous = reconstructed
        if key: self.last_key = self.number
        self.number += 1
        return header + payload


class Decoder:
    def __init__(self,codebook:bytes=b''):
        self.frame=bytearray(WIDTH*HEIGHT)
        self.codebook=[list(codebook[i:i+16]) for i in range(0,len(codebook),16)]

    def decode(self, packet: bytes) -> bytearray:
        if len(packet) < FRAME_HEADER.size: raise ValueError("short frame")
        magic, number, flags, changed, size = FRAME_HEADER.unpack_from(packet)
        if magic != b"FRM0" or len(packet) != FRAME_HEADER.size + size:
            raise ValueError("bad frame packet")
        reference = bytearray(self.frame); p = FRAME_HEADER.size
        if flags & SPARSE:
            if p + changed*2 > len(packet): raise ValueError("short sparse index")
            indices = [struct.unpack_from('<H', packet, p+i*2)[0] for i in range(changed)]
            p += changed*2
            if any(i >= BLOCKS for i in indices): raise ValueError("bad sparse block index")
        else:
            if p + MASK_BYTES > len(packet): raise ValueError("short frame mask")
            mask = packet[p:p+MASK_BYTES]; p += MASK_BYTES
            indices = [bi for bi in range(BLOCKS) if mask[bi >> 3] & (1 << (bi & 7))]
        seen = 0
        for bi in indices:
            seen += 1; mode = packet[p]; p += 1
            if mode == 0:
                px = [packet[p]] * 64; p += 1
            elif mode == 1:
                pal = packet[p:p+2]; p += 2
                idx = _unpack_indices(packet[p:p+8], 64, 1); p += 8
                px = [pal[i] for i in idx]
            elif mode == 2:
                pal = packet[p:p+4]; p += 4
                idx = _unpack_indices(packet[p:p+16], 64, 2); p += 16
                px = [pal[i] for i in idx]
            elif mode == 3:
                px = list(packet[p:p+64]); p += 64
            elif mode == 4:
                dx = packet[p] - 256 if packet[p] & 128 else packet[p]
                dy = packet[p+1] - 256 if packet[p+1] & 128 else packet[p+1]
                p += 2; bx, by = bi % BX, bi // BX; sx, sy = bx*BLOCK+dx*4, by*BLOCK+dy*4
                if not (0 <= sx <= WIDTH-BLOCK and 0 <= sy <= HEIGHT-BLOCK): raise ValueError("bad motion vector")
                px = _block_xy(reference, sx, sy)
            elif mode == 5:
                if p >= len(packet): raise ValueError("short quadrant mask")
                qmask=packet[p];p+=1;px=_block(reference,bi)
                for q in range(4):
                    if qmask&(1<<q):
                        if p+4>len(packet): raise ValueError("short quadrant patch")
                        pal=packet[p:p+2];idx=_unpack_indices(packet[p+2:p+4],16,1);p+=4
                        _put_quadrant(px,q,[pal[j] for j in idx])
            elif mode == 6:
                if p >= len(packet) or not self.codebook: raise ValueError("missing VQ codebook")
                qmask=packet[p];p+=1;px=_block(reference,bi)
                for q in range(4):
                    if qmask&(1<<q):
                        if p>=len(packet) or packet[p]>=len(self.codebook):raise ValueError("bad VQ index")
                        _put_quadrant(px,q,self.codebook[packet[p]]);p+=1
            else: raise ValueError(f"unknown block mode {mode}")
            _put_block(self.frame, bi, px)
        if seen != changed or p != len(packet): raise ValueError("corrupt frame records")
        return bytearray(self.frame)


def indexed_to_rgb(frame: bytes | bytearray) -> bytes:
    out = bytearray(len(frame)*3)
    for i, c in enumerate(frame): out[i*3:i*3+3] = bytes(_rgb(c))
    return bytes(out)
