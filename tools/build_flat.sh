#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
CC=${CC:-arm-none-eabi-gcc}; OBJCOPY=${OBJCOPY:-arm-none-eabi-objcopy}
command -v "$CC" >/dev/null || { echo "arm-none-eabi-gcc not found" >&2; exit 1; }
python3 "$ROOT/tools/gen_test_assets.py" "$ROOT/player/source/test_assets.c"
B="$ROOT/player/build-flat"; mkdir -p "$B"; rm -f "$B"/*.o
CFLAGS="-mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -Wall -Wextra -ffreestanding -fno-builtin -fomit-frame-pointer -I$ROOT/player/include"
for s in "$ROOT"/player/source/*.c; do
  o="$B/$(basename "${s%.c}").o"; "$CC" $CFLAGS -c "$s" -o "$o"
done
"$CC" -mcpu=arm7tdmi -marm -mthumb-interwork -c "$ROOT/player/source/crt0.s" -o "$B/crt0.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/player/linker.ld" \
  -Wl,-Map,"$B/glp-av-test.map" -o "$B/glp-av-test.elf" "$B"/*.o -lgcc
"$OBJCOPY" -O binary "$B/glp-av-test.elf" "$ROOT/glp-av-test.gba"
python3 "$ROOT/tools/fix_gba.py" "$ROOT/glp-av-test.gba"
echo "Built $ROOT/glp-av-test.gba"
