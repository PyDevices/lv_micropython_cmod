#!/usr/bin/env bash
# Compare gen_mpy.py and gen_lv_bindings.py output. Exit 0 if lvmp.c files match.
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVGL_H="lvgl/lvgl.h"
CPP="${CPP:-gcc -E}"
LV_CFLAGS="${LV_CFLAGS:-}"

mkdir -p "$GENERATED"

echo "Preprocessing..."
$CPP $LV_CFLAGS -E -DPYCPARSER \
    -I "$LVMP_DIR/pycparser/utils/fake_libc_include" \
    "$LVMP_DIR/$LVGL_H" > "$GENERATED/lvmp.c.pp"

GEN_MPY="$GENERATED/lvmp.gen_mpy.c"
GEN_NEW="$GENERATED/lvmp.gen_lv_bindings.c"

echo "Running gen_mpy.py..."
python3 "$LVMP_DIR/gen_mpy.py" \
    -M lvgl -MP lv \
    -MD "$GENERATED/lvmp.gen_mpy.json" \
    -E "$GENERATED/lvmp.c.pp" \
    "$LVGL_H" > "$GEN_MPY"

echo "Running gen_lv_bindings.py..."
python3 "$LVMP_DIR/gen_lv_bindings.py" \
    --target micropython \
    -M lvgl -MP lv \
    -MD "$GENERATED/lvmp.gen_lv_bindings.json" \
    -E "$GENERATED/lvmp.c.pp" \
    "$LVGL_H" > "$GEN_NEW"

echo "Diffing generated C (ignoring command-line comment)..."
if diff -u \
    <(sed '6s/.*/ * COMMAND_LINE/' "$GEN_MPY") \
    <(sed '6s/.*/ * COMMAND_LINE/' "$GEN_NEW"); then
    echo "OK: gen_mpy.py and gen_lv_bindings.py produce identical output."
else
    echo "MISMATCH: outputs differ (see diff above)."
    exit 1
fi
