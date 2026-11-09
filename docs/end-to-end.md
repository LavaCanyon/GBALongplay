# End-to-end album build

The manifest builder automates equal capacity allocation, episode encoding, thumbnail extraction, GLA1 creation, and a JSON size report.

```text
python tools/build_album_manifest.py examples/album.json -o shows.gla
```

Requirements: Python 3.10+ and FFmpeg available as `ffmpeg` on `PATH`.

For a 64 MiB four-entry album with a 0.5 MiB bootstrap/runtime reserve, each episode receives a 15.875 MiB GLV2 ceiling. The album starts at physical offset `0x00080000` and may continue across the 32 MiB boundary. The encoder itself subtracts audio and index costs before setting its video budget.

The default hybrid profile uses `vq: true`, 80,000 training patches, 50% edge-weighted sampling, conservative 8×8 fallback modes, complete scene keyframes, and no dynamic 4×4 patches. Each 4 KiB codebook is embedded inside its episode's GLV2 stream.

During iterative builds, preserve the work directory and use:

```text
python tools/build_album_manifest.py album.json -o shows.gla \
  --work-dir encoded --reuse
```

An episode may provide an already encoded stream instead of `source`:

```json
{
  "title": "EPISODE 1",
  "glv": "encoded/episode-01.glv",
  "thumbnail_rgb332": "art/episode-01.rgb"
}
```

The current menu accepts one to four entries. Titles are converted to the album format's ASCII field. Automatic thumbnails are cropped to 80×48 and converted to the player's RGB332 palette.

After creating `shows.gla`, package it with the Matrix player toolchain:

```text
ALBUM_FILE="$PWD/shows.gla" \
OUTPUT_FILE="$PWD/shows.gba" \
sh tools/build_matrix_player.sh
```

The shell build requires an `arm-none-eabi` GCC/binutils toolchain on `PATH`.
