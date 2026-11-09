# v12 keyframe optimization

The v12 decoder writes complete 32-bit pixel groups into aligned EWRAM instead of expanding every block into a temporary 64-byte array and copying one byte at a time.

Mode-specific paths:

- Solid block: one replicated word, 16 stores per 8×8 block.
- Two-/four-colour block: unpack four indices directly into each output word.
- Raw block: pack each unaligned packet group into aligned output words.
- Block coordinates advance incrementally; no per-block division or modulo.
- Hot routines remain in IWRAM.

Automated 900-frame mGBA comparison:

| Measurement | v11 | v12 |
|---|---:|---:|
| Typical/latest video | 12.3 ms | 11.0 ms |
| Worst video/keyframe | 95.7 ms | 58.0 ms |
| Worst ADPCM slice | 5.5 ms | 5.5 ms |

The worst keyframe now uses about 58% of the 100 ms interval at 10 fps, leaving approximately 42 ms for mapper copying, menu bookkeeping, and emulator/hardware variation.
