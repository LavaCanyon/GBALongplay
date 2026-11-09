"""Tiny P6 PPM reader/writer used for dependency-free codec tests."""
from pathlib import Path

def read(path: str | Path) -> tuple[int, int, bytes]:
    raw = Path(path).read_bytes(); parts = raw.split(None, 4)
    if len(parts) != 5 or parts[0] != b"P6" or parts[3] != b"255":
        raise ValueError("only binary P6 PPM with max value 255 is supported")
    w, h = int(parts[1]), int(parts[2]); data = parts[4]
    if len(data) != w*h*3: raise ValueError("bad PPM payload")
    return w, h, data

def write(path: str | Path, w: int, h: int, rgb: bytes) -> None:
    if len(rgb) != w*h*3: raise ValueError("bad RGB payload")
    Path(path).write_bytes(f"P6\n{w} {h}\n255\n".encode() + rgb)
