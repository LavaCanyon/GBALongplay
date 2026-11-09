# GLA1 multi-episode album

GLA1 wraps multiple GLV2 episode streams, thumbnails, and menu metadata.

## Header (32 bytes)

```text
char[4] magic = "GLA1"
u16 version = 1
u16 header_size = 32
u16 episode_count
u16 flags
u32 directory_offset
u32 data_offset
u32 image_size
u32 crc32              // whole album with this field zero
u32 reserved
```

## Directory entry (64 bytes)

```text
char[32] title_ascii
u32 glv_offset
u32 glv_size
u32 duration_ticks
u32 thumbnail_offset
u32 thumbnail_size
u32 flags
u32 reserved0
u32 reserved1
```

The current thumbnail representation is raw 80×48 RGB332 (3840 bytes). Identical GLV2 streams are deduplicated by the desktop album builder.

## v13 menu controls

- Up/Down: choose one of four episodes
- A: play selected episode
- B during playback: stop audio safely and return to menu

The test album uses four unique titles and thumbnails pointing to one shared synthetic GLV2 stream. This verifies directory parsing, selection, thumbnail rendering, player reset, and return-to-menu behavior without quadrupling the test ROM.
