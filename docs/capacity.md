# 64 MiB capacity plan

Reference target: four 22-minute episodes, 10 fps, mono 8192 Hz IMA ADPCM.

Generated with:

```text
python -m encoder.cli plan --rom-mib 64 --episodes 4 --minutes 22 --fps 10
```

| Allocation | Approximate size |
|---|---:|
| Audio payload | 20.64 MiB |
| Player, menu, indexes, thumbnails, alignment reserve | 1.12 MiB |
| Video payload available | 42.24 MiB |
| Total | 64 MiB |

This leaves approximately:

- **8.19 KiB/s for video**
- **839 bytes per video frame at 10 fps**
- **15.875 MiB average packaged allowance per episode** after the shared reserve

These are ceilings, not guaranteed output sizes. Low-motion animation can encode below budget; live action may use the full allowance while retaining more stale blocks.

## Target-size encoding

For four equal-length episodes, encode each near the planner's episode allowance:

```text
python -m encoder.cli encode episode-01.mp4 -o episode-01.glv \
  --fps 10 --target-mib 15.875
```

The encoder subtracts ADPCM data and index overhead, then assigns the remaining bytes to video. Non-keyframes have a hard packet ceiling. Changed blocks are ranked by reconstruction improvement per byte, so the most visually useful blocks are updated first. Keyframes may exceed their instantaneous frame budget; subsequent frames repay that debt through the rate-control reservoir.

## Practical quality controls

- Longer keyframe intervals reduce storage but make seeks coarser.
- Animation generally benefits from block retention and two-/four-colour modes.
- Live action needs more changed blocks and may require lower frame rate or more cartridge capacity.
- Four 11-minute episodes have roughly twice the video allowance per second of four 22-minute episodes.
- A 32 MiB flat-ROM profile is possible, but four full 22-minute episodes would be extremely constrained after audio.
