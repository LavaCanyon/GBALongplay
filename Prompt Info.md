# GBA Longplay

An original, open-source video encoder, menu/player ROM, and cartridge mapper design for long-form video on real Game Boy Advance hardware.

> Status: complete 64 MiB Matrix-backed menu/player pipeline verified in mGBA. `glp-matrix-menu-test-v16.gba` boots into an EWRAM runtime, reads its GLA1 album from the second 32 MiB half, renders thumbnails, starts bank-aware GLV2 playback, streams clean ADPCM audio, returns to the menu, and can start another entry.

## Intended result

```text
gbalong encode show.yaml -o shows.gba --profile cart128
```

Input manifest:

```yaml
title: Saturday Shows
episodes:
  - title: Episode 1
    video: episode-01.mp4
    thumbnail_time: 00:00:18
  - title: Episode 2
    video: episode-02.mp4
  - title: Episode 3
    video: episode-03.mp4
  - title: Episode 4
    video: episode-04.mp4
```

The output is one cartridge image containing a GBA-native episode menu, thumbnails, playback controls, and video/audio streams.

## First hardware target

**64 MiB Matrix-compatible GBA Video image**:

- Uses the mapper command interface already supported by mGBA for commercial 64 MiB GBA Video cartridges.
- Streams physical media through a remappable 8 KiB ROM window in 512-byte blocks.
- Decoder and mapping routines execute from GBA work RAM while the window changes.
- The image identifier at header offset `0xAC` is `M`, allowing mGBA to detect the mapper.
- A 32 MiB flat-ROM profile remains useful for ordinary flash carts.

A custom 128 MiB profile is kept as a future option, but it would need new emulator support and is no longer the default.

## Software architecture

- **Encoder:** cross-platform Python front end with FFmpeg for media decoding; later distributable as standalone Windows, macOS, and Linux executables.
- **Video:** original block-transform/inter-frame codec designed around the ARM7TDMI. Multiple quality profiles; frame skipping is explicit and audio remains the master clock.
- **Audio:** mono low-rate ADPCM, DMA-fed through a FIFO.
- **Player:** devkitARM/libgba-compatible C with hot decode paths moved to ARM assembly after profiling.
- **Display:** 240×160 output with double buffering; aspect-preserving letterbox/crop options.
- **Container:** independently indexed episodes and seek points; CRC-protected chunks; bank-safe layout.
- **Menu:** title list, thumbnails, resume position, episode selection, and playback controls.

## Controls

### Menu

- D-pad: choose episode
- A/Start: play
- Select: options

### Playback

- A: pause/resume
- B: return to menu
- Left/Right: previous/next seek point
- L/R: previous/next episode
- Up/Down: volume

## Capacity expectations

The encoder uses target-size rate control rather than promising fixed quality. Four 22-minute episodes in 64 MiB have only about 12 KiB/s total, including player/menu overhead. IMA ADPCM at 8 kHz consumes about 4 KiB/s, leaving roughly 8 KiB/s for video. That is an intentionally harsh profile best suited to animation and low-motion material; shorter episodes or fewer episodes improve quality substantially.

## Repository layout

```text
encoder/       desktop encoder and reference decoder
player/        GBA menu/player source
docs/          stream and cartridge specifications
hardware/      mapper HDL, memory map, PCB implementation notes
tests/         codec/container conformance vectors
```

## Principles

1. Runs on an unmodified GBA, GBA SP, or Game Boy Player when used with the specified cartridge.
2. Does not reuse or require Majesco/Actimagine code or proprietary stream formats.
3. Deterministic encoding and a documented format.
4. Graceful playback under decode pressure: preserve audio, then drop video frames.
5. Keep cartridge access sequential and mapper transitions infrequent.

## Prototype usage

Requirements: Python 3.10+ and FFmpeg on `PATH`.

```text
python -m encoder.cli plan --rom-mib 64 --episodes 4 --minutes 22 --fps 10
python -m encoder.cli encode input.mp4 -o clip.glv --fps 10 --target-mib 15.875
python -m encoder.cli probe clip.glv
python -m encoder.cli decode clip.glv -o preview --every 30
```

The last command writes dependency-free PPM preview frames. The general-purpose `.glv` prototype still contains video only, but the bundled GBA test ROM exercises an integrated generated ADPCM soundtrack and video stream.

Run codec and C-decoder checks:

```text
python tests/test_codec.py
cc -std=c99 -Iplayer/include tests/c_decoder_test.c player/source/video.c -o ctest
```

Build the generated flat-ROM A/V test with an `arm-none-eabi` GCC toolchain:

```text
sh tools/build_flat.sh
```

Expected `glp-av-test.gba` behavior in mGBA: a moving orange circle over coloured bands, a growing white progress bar, and four changing musical notes. The sequence loops about every four seconds.

## Build roadmap

1. ~~Freeze initial mapper and video packet contracts.~~
2. ~~Implement media preprocessing, reference video codec, ADPCM, and matching C decoder.~~
3. ~~Verify continuous-DMA A/V playback under mGBA and BizHawk.~~
4. ~~Verify GLV2 indexes and background ADPCM buffer preparation (`glp-stream-test-v6.gba`).~~
5. ~~Verify audio-master video scheduling and corrected linker layout (`glp-audio-clock-test-v7b.gba`).~~
6. ~~Reject one-second chunks: frequent DMA handoffs regress mGBA audio (`glp-low-latency-test-v8.gba`).~~
7. ~~Verify incremental decoding of four-second chunks (`glp-incremental-audio-test-v9.gba`); confirmed clean and smooth in mGBA.~~
8. ~~Add cartridge capacity planning and target-size video rate control.~~
9. ~~Verify optimized on-device decode meters (`glp-performance-test-v11.gba`); measured and visual results agree.~~
10. ~~Verify packed-word keyframe decoding (`glp-keyframe-test-v12.gba`); measured and visual results agree at a 58% worst-case bar.~~
11. ~~Verify the GLA1 four-entry menu, thumbnails, selection, playback, and return-to-menu flow (`glp-menu-test-v13.gba`).~~
12. ~~Validate the Matrix command path and 64 MiB high-bank packer (`glp-matrix64-test.gba`); confirmed in mGBA.~~
13. ~~Verify corrected bank-aware Matrix menu and playback, including interactive tests.~~
14. ~~Tune against representative animation and select the conservative four-11-minute profile after testing scene keys, VFR, motion, and 4×4 patches.~~
15. ~~Add JSON-driven multi-episode encoding, thumbnail extraction, album reports, and full 63.5 MiB Matrix album layout.~~
16. ~~Train and evaluate 4×4 VQ codebooks on both animation samples; desktop gate passed.~~
17. ~~Verify hybrid VQ on cel animation and refine it with edge-weighted training (`glp-cel-hybrid-vq-detail-v35.gba`).~~
18. ~~Validate independently trained hybrid VQ profiles on both cel and Flash-style animation; both passed.~~
19. ~~Make per-episode edge-weighted VQ training the default manifest workflow.~~
20. ~~Build and verify a four-entry hybrid-VQ album workflow (`glp-four-entry-vq-demo-v37.gba`).~~
21. ~~Encode, normalize, package, and automatically validate four full episodes.~~
22. ~~Add playback controls, action overlays, GLT1 themes, and the offline converter UI.~~
23. ~~Validate the converter end-to-end from file selection through downloadable GBA ROM.~~
24. Build the low-spec Linux desktop wrapper and continue optional player features.
25. Optionally validate on custom cartridge hardware.
