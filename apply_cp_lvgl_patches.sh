#!/usr/bin/env bash
# Apply (or preview) CircuitPython LVGL integration patches.
#
# Usage:
#   ./apply_cp_lvgl_patches.sh --dry-run
#   ./apply_cp_lvgl_patches.sh --apply
#   ./apply_cp_lvgl_patches.sh --status
#
# Environment:
#   CP_DIR      CircuitPython tree (default: $CMODS_DIR/circuitpython or ~/github/circuitpython)
#   CMODS_DIR   This repo root (default: parent of lv_micropython_cmod)
#   BOARD       Board id (default: espressif_esp32p4_function_ev)
#   PORT        Port name under ports/ (default: espressif)

set -euo pipefail

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
CMODS_DIR="${CMODS_DIR:-$(cd "$LVMP_DIR/.." && pwd)}"
CP_DIR="${CP_DIR:-$CMODS_DIR/circuitpython}"
if [ ! -d "$CP_DIR/.git" ] && [ -d "$HOME/github/circuitpython/.git" ]; then
    CP_DIR="$HOME/github/circuitpython"
fi
BOARD="${BOARD:-espressif_esp32p4_function_ev}"
PORT="${PORT:-espressif}"
SPIKE_DIR="$LVMP_DIR/circuitpython_spike"
SPIKE_MANIFEST="$SPIKE_DIR/copy_manifest.txt"

MARKER_BEGIN="# >>> cmods-lvgl begin (apply_cp_lvgl_patches.sh)"
MARKER_END="# >>> cmods-lvgl end"

MODE="${1:---dry-run}"
case "$MODE" in
    --dry-run|--apply|--status) ;;
    -h|--help)
        sed -n '2,14p' "$0"
        exit 0
        ;;
    *)
        echo "Usage: $0 [--dry-run|--apply|--status]"
        exit 1
        ;;
esac

DRY_RUN=0
APPLY=0
if [ "$MODE" = "--dry-run" ]; then DRY_RUN=1; fi
if [ "$MODE" = "--apply" ]; then APPLY=1; fi

log() { echo "$*"; }

patch_block_present() {
    local file="$1"
    [ -f "$file" ] && grep -qF "$MARKER_BEGIN" "$file"
}

insert_block_after_line() {
    local file="$1"
    local anchor="$2"
    local block="$3"
    if patch_block_present "$file"; then
        log "  skip (already patched): $file"
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  [dry-run] insert block into $file after: $anchor"
        return 0
    fi
    python3 - "$file" "$anchor" "$MARKER_BEGIN" "$MARKER_END" "$block" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
anchor = sys.argv[2]
begin = sys.argv[3]
end = sys.argv[4]
block = sys.argv[5]

text = path.read_text()
if begin in text:
    sys.exit(0)
if anchor not in text:
    raise SystemExit(f"anchor not found in {path}: {anchor!r}")
insert = f"\n{begin}\n{block}\n{end}\n"
path.write_text(text.replace(anchor, anchor + insert, 1))
PY
}

copy_spike_files() {
    python3 - "$SPIKE_DIR" "$CP_DIR" "$SPIKE_MANIFEST" "$DRY_RUN" <<'PY'
import filecmp
import shutil
import sys
from pathlib import Path

spike_dir, cp_dir, manifest, dry = sys.argv[1:5]
dry_run = dry == "1"

def copy_one(rel_dir: str, filename: str) -> None:
    rel = f"{rel_dir}/{filename}"
    src = Path(spike_dir)
    dst = Path(cp_dir)
    for part in rel_dir.split("/"):
        src /= part
        dst /= part
    src /= filename
    dst /= filename
    if not src.is_file():
        raise SystemExit(f"missing spike file: {src}")
    if dst.is_file() and filecmp.cmp(src, dst, shallow=False):
        print(f"  unchanged: {rel}")
        return
    if dry_run:
        verb = "update" if dst.is_file() else "create"
        print(f"  [dry-run] {verb} {rel}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  copied: {rel}")

for raw in Path(manifest).read_text().splitlines():
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    rel_dir, filename = line.split("\t", 1)
    copy_one(rel_dir.strip(), filename.strip())
PY
}

if [ ! -d "$CP_DIR/.git" ]; then
    echo "CircuitPython tree not found at $CP_DIR"
    echo "Set CP_DIR to your clone (e.g. CP_DIR=~/github/circuitpython)"
    exit 1
fi

if [ ! -f "$SPIKE_MANIFEST" ]; then
    echo "Missing spike manifest: $SPIKE_MANIFEST" >&2
    exit 1
fi

PORT_DIR="$CP_DIR/ports/$PORT"
BOARD_MK="$PORT_DIR/boards/$BOARD/mpconfigboard.mk"
BOARD_H="$PORT_DIR/boards/$BOARD/mpconfigboard.h"
DEFNS_MK="$CP_DIR/py/circuitpy_defns.mk"
MPCONFIG_MK="$CP_DIR/py/circuitpy_mpconfig.mk"
PORT_MK="$PORT_DIR/Makefile"

CMODS_REL=$(python3 -c "import os; print(os.path.relpath('$CMODS_DIR', '$PORT_DIR'))")

log "CircuitPython: $CP_DIR"
log "cmods:         $CMODS_DIR (as $CMODS_REL from port)"
log "board:         $BOARD"
log "mode:          $MODE"
log

if [ "$MODE" = "--status" ]; then
    SPIKE_INIT_C=$(python3 - "$SPIKE_MANIFEST" "$CP_DIR" <<'PY'
import sys
from pathlib import Path
manifest, cp_dir = sys.argv[1:3]
rel_dir, filename = Path(manifest).read_text().splitlines()[0].split("\t", 1)
p = Path(cp_dir)
for part in rel_dir.split("/"):
    p /= part
p /= filename.strip()
print(p)
PY
)
    report() {
        local label="$1"
        local file="$2"
        if [ ! -e "$file" ]; then
            echo "missing  $file"
        elif [ "$label" = "spike" ]; then
            echo "ok       $file"
        elif patch_block_present "$file"; then
            echo "patched  $file"
        else
            echo "pending  $file"
        fi
    }
    report spike "$SPIKE_INIT_C"
    report patch "$BOARD_MK"
    report patch "$DEFNS_MK"
    report patch "$MPCONFIG_MK"
    report patch "$PORT_MK"
    if [ -f "$BOARD_H" ]; then
        report patch "$BOARD_H"
    fi
    exit 0
fi

log "==> Copy spike templates"
copy_spike_files
log

log "==> Patch board mpconfigboard.mk"
if [ ! -f "$BOARD_MK" ]; then
    echo "Board makefile not found: $BOARD_MK" >&2
    exit 1
fi
BOARD_BLOCK="CIRCUITPY_LVGL = 1
CFLAGS += -DCIRCUITPY_LVGL=1
CFLAGS += -DLVGL_GENERATED_PHASE1=1"
insert_block_after_line "$BOARD_MK" "CIRCUITPY_ESP_PSRAM_FREQ = 200m" "$BOARD_BLOCK"
log

log "==> Patch py/circuitpy_mpconfig.mk (default off)"
MPCONFIG_BLOCK="CIRCUITPY_LVGL ?= 0
CFLAGS += -DCIRCUITPY_LVGL=\$(CIRCUITPY_LVGL)"
insert_block_after_line "$MPCONFIG_MK" "CFLAGS += -DCIRCUITPY_LOCALE=\$(CIRCUITPY_LOCALE)" "$MPCONFIG_BLOCK"
log

log "==> Patch py/circuitpy_defns.mk"
DEFNS_PATTERNS_BLOCK="ifeq (\$(CIRCUITPY_LVGL),1)
SRC_PATTERNS += lvgl/%
endif"
insert_block_after_line "$DEFNS_MK" "ifeq (\$(CIRCUITPY_LOCALE),1)" "$DEFNS_PATTERNS_BLOCK"

DEFNS_LIST_BLOCK=$'\tlvgl/__init__.c \\'
insert_block_after_line "$DEFNS_MK" $'\tlocale/__init__.c \\' "$DEFNS_LIST_BLOCK"
log

log "==> Patch port Makefile (circuitpython.mk)"
PORT_BLOCK="CMODS_DIR := \$(abspath $CMODS_REL)
include \$(CMODS_DIR)/lv_micropython_cmod/circuitpython.mk"
insert_block_after_line "$PORT_MK" "include ../../py/circuitpy_mkenv.mk" "$PORT_BLOCK"
log

log "==> Patch board mpconfigboard.h (ifndef guard)"
if [ -f "$BOARD_H" ]; then
    BOARD_H_BLOCK="#ifndef CIRCUITPY_LVGL
#define CIRCUITPY_LVGL (0)
#endif"
    insert_block_after_line "$BOARD_H" "#pragma once" "$BOARD_H_BLOCK"
fi
log

if [ "$DRY_RUN" = 1 ]; then
    log "Dry run complete. Re-run with --apply to write changes."
elif [ "$APPLY" = 1 ]; then
    log "Patches applied."
    log
    log "Next:"
    log "  $LVMP_DIR/regenerate_lvcp.sh"
    log "  cd $PORT_DIR && make BOARD=$BOARD CMODS_DIR=$CMODS_DIR"
    log "  # allocator-only first: add CMODS_LVGL_ALLOW_MISSING_BINDINGS=1"
fi
