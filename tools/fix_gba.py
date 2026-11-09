#!/usr/bin/env python3
"""Install the standard GBA header/logo and complement checksum."""
from pathlib import Path
import sys
LOGO=bytes.fromhex('''
24 FF AE 51 69 9A A2 21 3D 84 82 0A 84 E4 09 AD 11 24 8B 98 C0 81 7F 21
A3 52 BE 19 93 09 CE 20 10 46 4A 4A F8 27 31 EC 58 C7 E8 33 82 E3 CE BF
85 F4 DF 94 CE 4B 09 C1 94 56 8A C0 13 72 A7 FC 9F 84 4D 73 A3 CA 9A 61
58 97 A3 27 FC 03 98 76 23 1D C7 61 03 04 AE 56 BF 38 84 00 40 A7 0E FD
FF 52 FE 03 6F 95 30 F1 97 FB C0 85 60 D6 80 25 A9 63 BE 03 01 4E 38 E2
F9 A2 34 FF BB 3E 03 44 78 00 90 CB 88 11 3A 94 65 C0 7C 63 87 F0 3C AF
D6 25 E4 8B 38 0A AC 72 21 D4 F8 07''')
def fix(path:Path):
    rom=bytearray(path.read_bytes());
    if len(rom)<0xC0:raise ValueError('ROM is too short')
    rom[4:0xA0]=LOGO;rom[0xA0:0xAC]=b'GLP AV TEST '
    rom[0xAC:0xB0]=b'MGLP';rom[0xB0:0xB2]=b'00';rom[0xB2]=0x96
    rom[0xB3:0xBD]=bytes(10);rom[0xBD]=(-0x19-sum(rom[0xA0:0xBD]))&255
    rom[0xBE:0xC0]=b'\0\0'
    size=1
    while size<len(rom):size<<=1
    size=max(size,128*1024);rom.extend(b'\xff'*(size-len(rom)));path.write_bytes(rom)
    print(f'fixed {path} ({len(rom)} bytes), header checksum {rom[0xBD]:02x}')
if __name__=='__main__':fix(Path(sys.argv[1]))
