"""IMA ADPCM mono reference codec used by GLV audio chunks."""
from __future__ import annotations
import struct

INDEX = (-1, -1, -1, -1, 2, 4, 6, 8)
STEP = (7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,37,41,45,50,55,60,66,
        73,80,88,97,107,118,130,143,157,173,190,209,230,253,279,307,337,371,408,
        449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,1552,1707,1878,
        2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,6484,7132,
        7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,22385,
        24623,27086,29794,32767)


def encode(samples: list[int], predictor: int = 0, index: int = 0) -> bytes:
    out = bytearray(struct.pack("<hBB", predictor, index, 0)); nibs = []
    for sample in samples:
        step = STEP[index]; diff = sample - predictor; code = 8 if diff < 0 else 0
        d = abs(diff); delta = step >> 3
        if d >= step: code |= 4; d -= step; delta += step
        if d >= step >> 1: code |= 2; d -= step >> 1; delta += step >> 1
        if d >= step >> 2: code |= 1; delta += step >> 2
        predictor += -delta if code & 8 else delta
        predictor = max(-32768, min(32767, predictor))
        index = max(0, min(88, index + INDEX[code & 7])); nibs.append(code)
    for i in range(0, len(nibs), 2):
        out.append(nibs[i] | ((nibs[i+1] if i+1 < len(nibs) else 0) << 4))
    return bytes(out)


def decode(data: bytes, sample_count: int) -> list[int]:
    predictor, index, _ = struct.unpack_from("<hBB", data); out = []
    for byte in data[4:]:
        for code in (byte & 15, byte >> 4):
            if len(out) == sample_count: return out
            step = STEP[index]; delta = step >> 3
            if code & 4: delta += step
            if code & 2: delta += step >> 1
            if code & 1: delta += step >> 2
            predictor += -delta if code & 8 else delta
            predictor = max(-32768, min(32767, predictor))
            index = max(0, min(88, index + INDEX[code & 7])); out.append(predictor)
    if len(out) != sample_count: raise ValueError("short ADPCM block")
    return out
