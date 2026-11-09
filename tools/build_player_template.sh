#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd);OUT=${1:-$ROOT/converter/templates};ALBUM_OFFSET=${ALBUM_OFFSET:-0x70000}
CC=${CC:-arm-none-eabi-gcc};OBJCOPY=${OBJCOPY:-arm-none-eabi-objcopy};NM=${NM:-arm-none-eabi-nm};B="$ROOT/matrix_player/template-build";mkdir -p "$B" "$OUT";rm -f "$B"/*.o
CFLAGS="-mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -Wall -Wextra -ffreestanding -fno-builtin -fno-strict-aliasing -ffunction-sections -fdata-sections -DGLP_MATRIX_STORAGE -DGLP_ALBUM_PHYSICAL=$ALBUM_OFFSET -I$ROOT/player/include"
for s in main video adpcm menu storage image;do "$CC" $CFLAGS -c "$ROOT/player/source/$s.c" -o "$B/$s.o";done
"$CC" $CFLAGS -c "$ROOT/matrix_player/runtime_entry.c" -o "$B/runtime_entry.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/matrix_player/runtime.ld" -Wl,-Map,"$B/runtime.map" -o "$B/runtime.elf" "$B"/*.o -lgcc
"$OBJCOPY" -O binary "$B/runtime.elf" "$OUT/matrix64-runtime.bin"
SIZE=$(wc -c < "$OUT/matrix64-runtime.bin"|tr -d ' ');BS=$($NM -n "$B/runtime.elf"|awk '$3=="__bss_start"{print "0x"$1}');BE=$($NM -n "$B/runtime.elf"|awk '$3=="__bss_end"{print "0x"$1}')
"$CC" -mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -ffreestanding -fno-builtin -DRUNTIME_SIZE=$SIZE -DBSS_START=$BS -DBSS_END=$BE -c "$ROOT/matrix_player/boot.c" -o "$B/boot.o"
"$CC" -mcpu=arm7tdmi -marm -mthumb-interwork -c "$ROOT/matrix_player/crt0.s" -o "$B/crt0.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/matrix_player/boot.ld" -o "$B/boot.elf" "$B/crt0.o" "$B/boot.o" -lgcc
"$OBJCOPY" -O binary "$B/boot.elf" "$OUT/matrix64-boot.gba";python3 "$ROOT/tools/fix_gba.py" "$OUT/matrix64-boot.gba"
python3 - "$OUT" "$ALBUM_OFFSET" "$SIZE" "$BS" "$BE" <<'PY'
from pathlib import Path
import json,hashlib,sys
p=Path(sys.argv[1]);files={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ('matrix64-boot.gba','matrix64-runtime.bin')}
(p/'matrix64-template.json').write_text(json.dumps({'format':'GLP_MATRIX64_TEMPLATE','version':1,'album_offset':int(sys.argv[2],0),'runtime_offset':0x20000,'runtime_size':int(sys.argv[3]),'bss_start':sys.argv[4],'bss_end':sys.argv[5],'sha256':files},indent=2))
PY
rm -rf "$B";echo "Template built in $OUT"
