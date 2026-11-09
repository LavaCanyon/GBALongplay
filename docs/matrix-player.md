# Full Matrix-backed player (v15)

`glp-matrix-menu-test-v16.gba` integrates the verified menu and streaming player into a 64 MiB Matrix image. v16 limits every mapper command to eight 512-byte blocks (4 KiB); a count of 16 aliases to zero in mGBA's 16-entry mapping table and caused v15's large audio-packet reads to fail.

## Physical layout

| Physical offset | Contents |
|---:|---|
| `0x00000000` | GBA header and 392-byte bootstrap |
| `0x00020000` | 4296-byte EWRAM runtime image |
| `0x02000000` | GLA1 album and GLV2 media streams |
| remainder | `0xFF` padding for the 64 MiB image |

## Bootstrap

Only the first 4 KiB is initially dependable. The bootstrap maps the runtime in 4 KiB pieces, copies it to `0x02000000`, clears its BSS, and enters Thumb code in EWRAM. The complete player therefore remains executable while every Matrix ROM page is replaced.

## Bank-aware storage

The runtime no longer dereferences album or stream ROM pointers. The album begins after a 0.5 MiB bootstrap/runtime reserve, rather than at 32 MiB; this allows one album to use the remaining 63.5 MiB and cross the ordinary 32 MiB boundary. `storage_read()`:

1. converts an album-relative offset to a physical Matrix address;
2. aligns it to a 512-byte mapper block;
3. maps up to 8 KiB at virtual ROM offset zero;
4. handles unaligned leading bytes;
5. copies into an EWRAM destination.

Directory entries and the selected thumbnail are cached. Video packets use a 40,000-byte EWRAM packet buffer; ADPCM packets use a separate 16,400-byte buffer so incremental audio preparation can coexist with video reads.

## Automated validation

After 300 frames in headless mGBA:

- PC remained in EWRAM runtime code (`0x0200009A` in the test build).
- `DISPCNT=0x0414`, confirming Mode 4, BG2, and the selected framebuffer page.
- EWRAM began with the expected copied runtime instructions.

Interactive menu and playback behavior still requires the normal mGBA test because the headless run does not synthesize key input.
