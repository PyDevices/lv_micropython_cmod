#!/usr/bin/env bash
# Generate CircuitPython LVGL bindings (full phase-7 emission → generated/lvcp.c).
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVGL_H="lvgl/lvgl.h"

mkdir -p "$GENERATED"

CPP="${CPP:-gcc -E}"
# Match circuitpython.mk: CP build disables LVGL's bundled TJPGD (uses lib/tjpgd for jpegio).
LV_CFLAGS="${LV_CFLAGS:--DCMODS_CIRCUITPYTHON_BUILD=1 -I$LVMP_DIR}"

PP_FILE=$(mktemp)
trap 'rm -f "$PP_FILE"' EXIT

echo "Preprocessing $LVGL_H"
$CPP $LV_CFLAGS -E -DPYCPARSER \
    -I "$LVMP_DIR/pycparser/utils/fake_libc_include" \
    "$LVMP_DIR/$LVGL_H" > "$PP_FILE"

if [ "${LV_BINDINGS_DEBUG:-0}" = 1 ]; then
    cp "$PP_FILE" "$GENERATED/lvcp.c.pp"
    echo "Wrote $GENERATED/lvcp.c.pp"
fi

echo "Running generator (--target circuitpython)"
METADATA_ARGS=()
if [ "${LV_BINDINGS_DEBUG:-0}" = 1 ]; then
    METADATA_ARGS=(-MD "$GENERATED/lvcp.c.json")
fi

python3 "$LVMP_DIR/gen_lv_bindings.py" \
    --target circuitpython \
    -M lvgl -MP lv \
    "${METADATA_ARGS[@]}" \
    -E "$PP_FILE" \
    "$LVGL_H" > "$GENERATED/lvcp.c"
status=$?

if [ "$status" -ne 0 ]; then
    exit "$status"
fi

python3 - "$GENERATED/lvcp.c" "$GENERATED/lvcp_module_globals.h" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1]).read_text()
start = src.find("#ifndef LVCP_MODULE_GLOBALS_H")
end_marker = "#endif /* LVCP_MODULE_GLOBALS_H */"
end = src.find(end_marker)
if start < 0 or end < 0:
    raise SystemExit("LVCP_MODULE_GLOBALS block not found in lvcp.c")
end += len(end_marker)
Path(sys.argv[2]).write_text(src[start:end] + "\n")
PY

echo "Done: $GENERATED/lvcp.c"
