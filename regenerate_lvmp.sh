#!/usr/bin/env bash
# Generate lvmp.c from LVGL headers. Run after changing lvgl/, lv_conf.h, or binding/.
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVGL_H="lvgl/lvgl.h"

mkdir -p "$GENERATED"

CPP="${CPP:-gcc -E}"
LV_CFLAGS="${LV_CFLAGS:-}"

PP_FILE=$(mktemp)
trap 'rm -f "$PP_FILE"' EXIT

echo "Preprocessing $LVGL_H"
$CPP $LV_CFLAGS -E -DPYCPARSER \
    -I "$LVMP_DIR/pycparser/utils/fake_libc_include" \
    "$LVMP_DIR/$LVGL_H" > "$PP_FILE"

if [ "${LV_BINDINGS_DEBUG:-0}" = 1 ]; then
    cp "$PP_FILE" "$GENERATED/lvmp.c.pp"
    echo "Wrote $GENERATED/lvmp.c.pp"
fi

echo "Generating $GENERATED/lvmp.c"
METADATA_ARGS=()
if [ "${LV_BINDINGS_DEBUG:-0}" = 1 ]; then
    METADATA_ARGS=(-MD "$GENERATED/lvmp.c.json")
fi

python3 "$LVMP_DIR/gen_lv_bindings.py" \
    --target micropython \
    -M lvgl -MP lv \
    "${METADATA_ARGS[@]}" \
    -E "$PP_FILE" \
    "$LVGL_H" > "$GENERATED/lvmp.c"

echo "Done: $GENERATED/lvmp.c"
