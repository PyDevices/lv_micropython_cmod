#!/usr/bin/env bash
# Generate CircuitPython LVGL bindings (full phase-7 emission → generated/lvcp.c).
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVGL_H="lvgl/lvgl.h"

mkdir -p "$GENERATED"

CPP="${CPP:-gcc -E}"
LV_CFLAGS="${LV_CFLAGS:-}"

echo "Preprocessing $LVGL_H -> generated/lvcp.c.pp"
$CPP $LV_CFLAGS -E -DPYCPARSER \
    -I "$LVMP_DIR/pycparser/utils/fake_libc_include" \
    "$LVMP_DIR/$LVGL_H" > "$GENERATED/lvcp.c.pp"

echo "Running generator (--target circuitpython)"
python3 "$LVMP_DIR/gen_lv_bindings.py" \
    --target circuitpython \
    -M lvgl -MP lv \
    -MD "$GENERATED/lvcp.c.json" \
    -E "$GENERATED/lvcp.c.pp" \
    "$LVGL_H" > "$GENERATED/lvcp.c"
status=$?

if [ "$status" -ne 0 ]; then
    exit "$status"
fi

echo "Done: $GENERATED/lvcp.c"
