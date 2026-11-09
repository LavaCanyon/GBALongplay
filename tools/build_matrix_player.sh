#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
CC=${CC:-arm-none-eabi-gcc};OBJCOPY=${OBJCOPY:-arm-none-eabi-objcopy};NM=${NM:-arm-none-eabi-nm}
B="$ROOT/matrix_player/build";mkdir -p "$B";rm -f "$B"/*.o
ALBUM_OFFSET=${ALBUM_OFFSET:-0x80000}
CFLAGS="-mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -Wall -Wextra -ffreestanding -fno-builtin -fno-strict-aliasing -ffunction-sections -fdata-sections -DGLP_MATRIX_STORAGE -DGLP_ALBUM_PHYSICAL=$ALBUM_OFFSET -I$ROOT/player/include"
for s in main video adpcm menu storage image;do "$CC" $CFLAGS -c "$ROOT/player/source/$s.c" -o "$B/$s.o";done
"$CC" $CFLAGS -c "$ROOT/matrix_player/runtime_entry.c" -o "$B/runtime_entry.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/matrix_player/runtime.ld" -Wl,-Map,"$B/runtime.map" -o "$B/runtime.elf" "$B"/*.o -lgcc
"$OBJCOPY" -O binary "$B/runtime.elf" "$B/runtime.bin"
RUNTIME_SIZE=$(wc -c < "$B/runtime.bin" | tr -d ' ')
BSS_START=$($NM -n "$B/runtime.elf" | awk '$3=="__bss_start"{print "0x"$1}')
BSS_END=$($NM -n "$B/runtime.elf" | awk '$3=="__bss_end"{print "0x"$1}')
"$CC" -mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -ffreestanding -fno-builtin -DRUNTIME_SIZE=$RUNTIME_SIZE -DBSS_START=$BSS_START -DBSS_END=$BSS_END -c "$ROOT/matrix_player/boot.c" -o "$B/boot.o"
"$CC" -mcpu=arm7tdmi -marm -mthumb-interwork -c "$ROOT/matrix_player/crt0.s" -o "$B/crt0.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/matrix_player/boot.ld" -Wl,-Map,"$B/boot.map" -o "$B/boot.elf" "$B/crt0.o" "$B/boot.o" -lgcc
"$OBJCOPY" -O binary "$B/boot.elf" "$B/boot.gba"
python3 "$ROOT/tools/fix_gba.py" "$B/boot.gba"
if [ -n "${ALBUM_FILE:-}" ]; then cp "$ALBUM_FILE" "$B/album.gla"; else python3 "$ROOT/tools/gen_test_assets.py" "$B/album.gla"; fi
OUTPUT_FILE=${OUTPUT_FILE:-$ROOT/glp-matrix-menu-test-v16.gba}
python3 "$ROOT/tools/pack_matrix_album.py" "$B/boot.gba" "$B/runtime.bin" "$B/album.gla" --album-offset "$ALBUM_OFFSET" -o "$OUTPUT_FILE"
echo "runtime=$RUNTIME_SIZE bytes bss=$BSS_START..$BSS_END"
