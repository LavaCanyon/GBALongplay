# Matrix-compatible 64 MiB cartridge profile (validated bootstrap)

## Selection

The default large-image profile now follows the Matrix Memory command interface used by commercial 64 MiB GBA Video cartridges. This is preferable to inventing a mapper because current mGBA versions recognize this cartridge class, while the protocol is also known to have existed on real hardware.

mGBA enables Matrix handling when an image is larger than 32 MiB and byte `0xAC` in the GBA header is `M`.

## Registers

The mapper receives 32-bit writes in this order:

| Address | Meaning |
|---|---|
| `0x08800184` | physical byte offset, 512-byte aligned |
| `0x08800188` | virtual ROM offset, 512-byte aligned |
| `0x0880018C` | number of 512-byte blocks |
| `0x08800180` | command/commit (`0x11`) |

The visible mapping table contains sixteen 512-byte entries, giving an 8 KiB working window. A stream reader executes from RAM, maps up to 8 KiB, copies it to EWRAM, then advances.

## Image/bootstrap rules

- Physical capacity: 64 MiB.
- GBA header game-code byte at `0xAC` is `M` for emulator detection.
- The reset/bootstrap path must fit within the initially visible area.
- Runtime decoder, IRQ handler, stacks, and mapper-copy routine execute from IWRAM/EWRAM while mappings change.
- Stream chunks are preferably 512-byte aligned, but the reader supports arbitrary lengths by mapping covering blocks.
- DMA must not read the ROM window while a mapping command is committed.

## Validated high-bank test

`glp-matrix64-test.gba` is a 64 MiB image with a 528-byte bootstrap in the initially visible region and a 38,400-byte RGB332 framebuffer at physical offset `0x02000000`—the beginning of the second 32 MiB half.

The bootstrap repeatedly maps up to 4 KiB into virtual offset `0x1000`, copies it to EWRAM, and displays it in Mode 4. A 300-frame headless mGBA run reached stable player code with `DISPCNT=0x0404`; sampled EWRAM contained the expected high-bank pattern. This confirms mapper detection, command order, 512-byte block counts, and access beyond the ordinary GBA ROM window.

## Optional future profile

A simple 128 MiB custom mapper remains possible, but it would require a patched emulator or new upstream emulator support. It is therefore not the default while emulator compatibility is a priority.
