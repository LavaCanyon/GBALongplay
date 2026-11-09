# GLV2 single-episode container

GLV2 is the current executable prototype format. All integers are little-endian and all offsets are absolute from the beginning of the container.

## Header (64 bytes)

```text
char[4] magic = "GLV2"
u16 version = 2
u16 header_size = 64
u16 width = 240
u16 height = 160
u32 timebase = 8192
u32 fps_num
u32 fps_den
u32 duration_ticks
u32 video_frame_count
u32 audio_chunk_count
u32 audio_chunk_samples = 32768
u32 video_index_offset
u32 audio_index_offset
u32 data_offset
u32 flags                  // bit 0: loop
u32 reserved
u32 crc32                  // CRC of whole container with this field zero
```

## Video index

Twelve bytes per frame:

```text
u32 pts_ticks
u32 packet_offset
u32 packet_size
```

Video packets are `FRM0` block-codec frames. Audio is the master clock; the player may skip overdue non-reference video packets.

## Audio index

Sixteen bytes per chunk:

```text
u32 pts_ticks
u32 logical_sample_count
u32 packet_offset
u32 packet_size
```

Audio is mono IMA ADPCM at 8192 Hz. A chunk contains 32768 logical samples (four seconds) plus a 16-sample overlap guard. The guard duplicates the first 16 samples of the following chunk. The GBA decodes each chunk incrementally—currently 1024 samples per VBlank—rather than blocking video for the whole chunk.

## Continuous GBA playback

Two EWRAM PCM buffers hold 32768+16 decoded samples each. Timer 0 and FIFO A start once and then remain running. When Timer 1 marks a chunk boundary, the IRQ handler:

1. disables only DMA1;
2. selects the prepared alternate buffer at offset `+16`;
3. reenables DMA1 without clearing FIFO A;
4. flags the old buffer for background ADPCM decoding.

The 16 guard samples from the old buffer are already in FIFO A, so starting the next DMA source at `+16` avoids duplication and keeps mGBA, BizHawk, and hardware-oriented behavior consistent.

## Next container layer

The final cartridge image will wrap one or more GLV2 episode streams in a global menu/directory structure. Individual GLV2 offsets will become bank-aware physical locations when packed into a 64 MiB Matrix image.
