#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd);CC=${CC:-arm-none-eabi-gcc};OBJCOPY=${OBJCOPY:-arm-none-eabi-objcopy}
B="$ROOT/matrix_test/build";mkdir -p "$B"
"$CC" -mcpu=arm7tdmi -mthumb -mthumb-interwork -Os -ffreestanding -fno-builtin -c "$ROOT/matrix_test/main.c" -o "$B/main.o"
"$CC" -mcpu=arm7tdmi -marm -mthumb-interwork -c "$ROOT/matrix_test/crt0.s" -o "$B/crt0.o"
"$CC" -mcpu=arm7tdmi -mthumb-interwork -nostdlib -T "$ROOT/matrix_test/linker.ld" -Wl,-Map,"$B/test.map" -o "$B/test.elf" "$B/crt0.o" "$B/main.o" -lgcc
"$OBJCOPY" -O binary "$B/test.elf" "$B/boot.gba"
python3 "$ROOT/tools/fix_gba.py" "$B/boot.gba"
python3 "$ROOT/tools/make_matrix_payload.py" "$B/payload.bin"
python3 "$ROOT/tools/pack_matrix.py" "$B/boot.gba" "$B/payload.bin" -o "$ROOT/glp-matrix64-test.gba"
