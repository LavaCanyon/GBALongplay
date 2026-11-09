# On-device performance instrumentation

`glp-performance-test-v11.gba` measures decoder work using GBA Timer 2 with the CPU/64 prescaler.

Three two-pixel-high meters appear near the bottom:

- **Red:** most recent video packet decode; full width is the 100 ms budget at 10 fps.
- **Yellow:** maximum video packet decode observed, including keyframes; full width is 100 ms.
- **Green:** maximum 512-sample incremental ADPCM slice; full width is one 16.7 ms display frame.

The meters are written only into the copied VRAM page and do not modify the codec's reconstructed EWRAM frame.

## Automated mGBA measurement

A custom 900-frame headless mGBA run reads the timer counters directly from EWRAM:

| Measurement | Timer ticks (CPU/64) | Approximate time |
|---|---:|---:|
| Typical/latest video packet | 3224 | 12.3 ms |
| Worst video packet/keyframe | 25083 | 95.7 ms |
| Worst 512-sample ADPCM slice | 1446 | 5.5 ms |

The 10 fps stream has approximately 100 ms between video presentation timestamps, so the worst keyframe remains inside its scheduling interval, albeit narrowly. Incremental audio preparation completes comfortably within the four-second alternate-buffer window.

## Optimizations represented by v11

- Video block fill no longer performs integer division/modulo for every changed block.
- Hot video decode and ADPCM slice code execute from IWRAM.
- ADPCM work is sliced into 512 samples, keeping each slice below a display-frame budget.
- Timing includes IRQ work that occurs during a measured decode.

The next optimization target is keyframe decode headroom before adding mapper-copy overhead.
