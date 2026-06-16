#!/usr/bin/env bash
# Regression checks for MicroPython/CircuitPython binding generation.
# Run from repo root or lv_micropython_cmod/:  ./lv_micropython_cmod/verify_bindings.sh
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
GENERATED="$LVMP_DIR/generated"
LVCP_C="$GENERATED/lvcp.c"
LVCP_JSON="$GENERATED/lvcp.c.json"
LVMP_JSON="$GENERATED/lvmp.c.json"

echo "==> MicroPython generator parity (gen_mpy.py vs gen_lv_bindings.py)"
"$LVMP_DIR/compare_bindings.sh"
echo

echo "==> Regenerate CircuitPython bindings (lvcp.c)"
"$LVMP_DIR/regenerate_lvcp.sh"
echo

echo "==> Validate generated/lvcp.c"
python3 - "$LVCP_C" "$LVCP_JSON" "$LVMP_JSON" <<'PY'
import json
import sys
from pathlib import Path

lvcp_path = Path(sys.argv[1])
lvcp_json_path = Path(sys.argv[2])
lvmp_json_path = Path(sys.argv[3])

text = lvcp_path.read_text()
lines = text.splitlines()
line_count = len(lines)

errors = []

# Size: should track lvmp.c (full phase-7 emission), not the old ~2k phase-1 trim.
if line_count < 35000 or line_count > 45000:
    errors.append(f"lvcp.c line count {line_count} outside expected 35000–45000")

if "Target: circuitpython" not in text:
    errors.append("missing Target: circuitpython banner")

if "MP_REGISTER_MODULE(" in text:
    errors.append("lvcp.c must not call MP_REGISTER_MODULE (spike module registers lvgl)")

if "lvgl_module" not in text and "LVCP_MODULE_GLOBALS" not in text:
    errors.append("missing lvgl_module export or LVCP_MODULE_GLOBALS merge macro")

if "lvgl_module_entries" not in text:
    errors.append("missing lvgl_module_entries[] table")

if "CircuitPython phase-2 enum type objects" not in text:
    errors.append("missing phase-2 enum emission")

if "Struct " not in text or "mp_lv_" not in text:
    errors.append("missing struct/object emission markers")

meta = json.loads(lvcp_json_path.read_text())
lvmp_meta = json.loads(lvmp_json_path.read_text()) if lvmp_json_path.is_file() else {}

def check_count(label, got, expect, slack=5):
    if abs(got - expect) > slack:
        errors.append(f"{label}: got {got}, expected ~{expect} (±{slack})")

check_count("structs", len(meta.get("structs", [])), 100)
check_count("functions", len(meta.get("functions", {})), 221)
check_count("objects", len(meta.get("objects", {})), 41)
check_count("int_constants", len(meta.get("int_constants", [])), 24, slack=2)
check_count("blobs", len(meta.get("blobs", [])), 63, slack=2)

if lvmp_meta:
    check_count("structs vs lvmp.c.json", len(meta.get("structs", [])), len(lvmp_meta.get("structs", [])), slack=3)
    check_count("functions vs lvmp.c.json", len(meta.get("functions", {})), len(lvmp_meta.get("functions", {})), slack=3)

if errors:
    print("FAIL:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)

print(f"OK: lvcp.c ({line_count} lines)")
print(f"    metadata: {len(meta.get('structs', []))} structs, "
      f"{len(meta.get('functions', {}))} functions, "
      f"{len(meta.get('objects', {}))} objects, "
      f"{len(meta.get('int_constants', []))} int_constants, "
      f"{len(meta.get('blobs', []))} blobs")
PY

echo
echo "All binding regression checks passed."
