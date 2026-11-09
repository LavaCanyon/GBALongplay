# Reusable menu/static-screen music

## GSA1 asset

GSA1 is a reusable mono 8192 Hz IMA-ADPCM stream for non-video screens. It stores:

- sample count and duration;
- automatic playback gain;
- one-shot/loop flag;
- exact loop start/end samples;
- 32768-sample chunk index;
- sixteen-sample DMA handoff guards;
- CRC32.

The converter accepts any FFmpeg-supported audio source. `tools/compile_audio.py` already creates and validates GSA1 files.

## Intended screen model

- one optional album-default menu track;
- optional override on every splash;
- optional override on every description page;
- optional override on every pre-play screen;
- silence as an explicit option;
- identical asset hashes are deduplicated.

When two consecutive screens reference the same track ID, playback state continues. A different ID causes an immediate switch. Episode video always replaces static-screen music.

Each track selects one-shot, full loop, or custom sample-accurate loop points.

## Implemented integration

- GMR1 global music resource table with SHA-256 deduplication
- GLA1 resource embedding and CRC validation
- Album-wide menu music ID field
- Per-splash music IDs
- Per-episode pre-play and description music IDs
- GSA1 one-shot/full-loop/custom-loop assets

## Remaining integration

1. Add native converter music fields and compile selected tracks into GMR1.
2. Generalize the existing audio state machine from GLV-relative reads to resource-relative GSA1 reads.
4. Continue a shared track across menu/description transitions.
5. Stop or switch tracks on splash/pre-play transitions.
6. Add native converter controls and audio preview.
7. Subtract compiled music bytes from video budgets.
