#!/usr/bin/env bash
# Generate lvmp.c from LVGL headers. Run after changing lvgl/, lv_conf.h, or binding/.
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVGL_H="lvgl/lvgl.h"

mkdir -p "$GENERATED"

CPP="${CPP:-gcc -E}"
LV_CFLAGS="${LV_CFLAGS:-}"

echo "Preprocessing $LVGL_H -> generated/lvmp.c.pp"
$CPP $LV_CFLAGS -E -DPYCPARSER \
    -I "$LVMP_DIR/pycparser/utils/fake_libc_include" \
    "$LVMP_DIR/$LVGL_H" > "$GENERATED/lvmp.c.pp"

echo "Generating generated/lvmp.c"
python3 "$LVMP_DIR/gen_lv_bindings.py" \
    --target micropython \
    -M lvgl -MP lv \
    -MD "$GENERATED/lvmp.c.json" \
    -E "$GENERATED/lvmp.c.pp" \
    "$LVGL_H" > "$GENERATED/lvmp.c"

echo "Done: $GENERATED/lvmp.c"
