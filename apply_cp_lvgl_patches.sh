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
#   PORT        Port under ports/ (default: unix)
#   VARIANT     Unix variant (default: coverage; ignored for espressif)
#   BOARD       Espressif board id (default: espressif_esp32p4_function_ev; ignored for unix)

set -euo pipefail

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
CMODS_DIR="${CMODS_DIR:-$(cd "$LVMP_DIR/.." && pwd)}"
CP_DIR="${CP_DIR:-$CMODS_DIR/circuitpython}"
if [ ! -d "$CP_DIR/.git" ] && [ -d "$HOME/github/circuitpython/.git" ]; then
    CP_DIR="$HOME/github/circuitpython"
fi
PORT="${PORT:-unix}"
VARIANT="${VARIANT:-coverage}"
BOARD="${BOARD:-espressif_esp32p4_function_ev}"
SPIKE_DIR="$LVMP_DIR/circuitpython_spike"
SPIKE_MANIFEST="$SPIKE_DIR/copy_manifest.txt"

MARKER_TAG="cmods-lvgl begin (apply_cp_lvgl_patches.sh)"
MARKER_BEGIN="# >>> $MARKER_TAG"
MARKER_END="# >>> cmods-lvgl end"

markers_for_file() {
    local file="$1"
    case "$file" in
        *.h)
            echo "/* >>> $MARKER_TAG */"
            echo "/* >>> cmods-lvgl end */"
            ;;
        *)
            echo "$MARKER_BEGIN"
            echo "$MARKER_END"
            ;;
    esac
}

repair_invalid_header_markers() {
    local file="$1"
    [ -f "$file" ] || return 0
    case "$file" in
        *.h) ;;
        *) return 0 ;;
    esac
    if ! grep -qF "# >>> cmods-lvgl" "$file"; then
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  [dry-run] repair invalid # markers in $file"
        return 0
    fi
    python3 - "$file" "$MARKER_TAG" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
tag = sys.argv[2]
text = path.read_text()
text = text.replace(f"# >>> {tag}", f"/* >>> {tag} */")
text = text.replace("# >>> cmods-lvgl end", "/* >>> cmods-lvgl end */")
path.write_text(text)
PY
    log "  repaired header markers: $file"
}

MODE="${1:---dry-run}"
case "$MODE" in
    --dry-run|--apply|--status) ;;
    -h|--help)
        sed -n '2,16p' "$0"
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
    local needle="${2:-cmods-lvgl begin}"
    [ -f "$file" ] && grep -qF "$needle" "$file"
}

insert_block_before_line() {
    local file="$1"
    local anchor="$2"
    local block="$3"
    local needle="${4:-cmods-lvgl begin}"
    repair_invalid_header_markers "$file"
    if patch_block_present "$file" "$needle"; then
        log "  skip (already patched): $file"
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  [dry-run] insert block into $file before: $anchor"
        return 0
    fi
    local begin end
    begin=$(markers_for_file "$file" | sed -n '1p')
    end=$(markers_for_file "$file" | sed -n '2p')
    python3 - "$file" "$anchor" "$begin" "$end" "$block" <<'PY'
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
path.write_text(text.replace(anchor, insert + anchor, 1))
PY
}

insert_block_after_line() {
    local file="$1"
    local anchor="$2"
    local block="$3"
    local needle="${4:-cmods-lvgl begin}"
    repair_invalid_header_markers "$file"
    if patch_block_present "$file" "$needle"; then
        log "  skip (already patched): $file"
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  [dry-run] insert block into $file after: $anchor"
        return 0
    fi
    local begin end
    begin=$(markers_for_file "$file" | sed -n '1p')
    end=$(markers_for_file "$file" | sed -n '2p')
    python3 - "$file" "$anchor" "$begin" "$end" "$block" <<'PY'
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

insert_raw_after_line() {
    local file="$1"
    local anchor="$2"
    local line="$3"
    if grep -qF "$line" "$file" 2>/dev/null; then
        log "  skip (already present): $file"
        return 0
    fi
    if [ "$DRY_RUN" = 1 ]; then
        echo "  [dry-run] insert into $file after: $anchor"
        return 0
    fi
    python3 - "$file" "$anchor" "$line" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
anchor = sys.argv[2]
line = sys.argv[3]

text = path.read_text()
if line in text:
    sys.exit(0)
if anchor not in text:
    raise SystemExit(f"anchor not found in {path}: {anchor!r}")
path.write_text(text.replace(anchor, anchor + "\n" + line, 1))
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

port_makefile_anchor() {
    if [ "$PORT" = "unix" ]; then
        echo "include ../../py/mkenv.mk"
    else
        echo "include ../../py/circuitpy_mkenv.mk"
    fi
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
VARIANT_MK="$PORT_DIR/variants/$VARIANT/mpconfigvariant.mk"
VARIANT_H="$PORT_DIR/variants/$VARIANT/mpconfigvariant.h"
DEFNS_MK="$CP_DIR/py/circuitpy_defns.mk"
MPCONFIG_MK="$CP_DIR/py/circuitpy_mpconfig.mk"
PORT_MK="$PORT_DIR/Makefile"

CMODS_REL=$(python3 -c "import os; print(os.path.relpath('$CMODS_DIR', '$PORT_DIR'))")

log "CircuitPython: $CP_DIR"
log "cmods:         $CMODS_DIR (as $CMODS_REL from port)"
log "port:          $PORT"
if [ "$PORT" = "unix" ]; then
    log "variant:       $VARIANT"
else
    log "board:         $BOARD"
fi
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
    if [ "$PORT" = "unix" ]; then
        report patch "$VARIANT_MK"
        if [ -f "$VARIANT_H" ]; then
            report patch "$VARIANT_H"
        fi
    else
        report patch "$BOARD_MK"
        if [ -f "$BOARD_H" ]; then
            report patch "$BOARD_H"
        fi
    fi
    report patch "$DEFNS_MK"
    report patch "$MPCONFIG_MK"
    report patch "$PORT_MK"
    exit 0
fi

log "==> Copy spike templates"
copy_spike_files
log

LVGL_ENABLE_BLOCK="CIRCUITPY_LVGL = 1
CFLAGS += -DCIRCUITPY_LVGL=1
CFLAGS += -DLVGL_GENERATED_PHASE1=1"

variant_mk_anchor() {
    if [ "$VARIANT" = "coverage" ]; then
        echo $'-DCIRCUITPY_ZLIB=1'
    elif [ "$VARIANT" = "standard" ]; then
        echo 'FROZEN_MANIFEST ?= $(VARIANT_DIR)/manifest.py'
    else
        echo $'-DCIRCUITPY_LOCALE=1 \\'
    fi
}

if [ "$PORT" = "unix" ]; then
    log "==> Patch unix variant mpconfigvariant.mk"
    if [ ! -f "$VARIANT_MK" ]; then
        echo "Variant makefile not found: $VARIANT_MK" >&2
        exit 1
    fi
    insert_block_after_line "$VARIANT_MK" "$(variant_mk_anchor)" "$LVGL_ENABLE_BLOCK"
    log

    log "==> Patch unix variant mpconfigvariant.mk (module sources)"
    VARIANT_BINDINGS_BLOCK=$'shared-bindings/lvgl/__init__.c \\'
    insert_block_after_line "$VARIANT_MK" $'shared-bindings/jpegio/JpegDecoder.c \\' "$VARIANT_BINDINGS_BLOCK" "shared-bindings/lvgl/__init__.c"
    VARIANT_MODULE_BLOCK=$'shared-module/lvgl/__init__.c \\'
    insert_block_after_line "$VARIANT_MK" $'shared-module/jpegio/JpegDecoder.c \\' "$VARIANT_MODULE_BLOCK" "shared-module/lvgl/__init__.c"
    log

    log "==> Patch unix variant mpconfigvariant.h (ifndef guard)"
    if [ -f "$VARIANT_H" ]; then
        VARIANT_H_BLOCK="#ifndef CIRCUITPY_LVGL
#define CIRCUITPY_LVGL (0)
#endif"
        insert_block_after_line "$VARIANT_H" '#include "../mpconfigvariant_common.h"' "$VARIANT_H_BLOCK"
    fi
    log
else
    log "==> Patch board mpconfigboard.mk"
    if [ ! -f "$BOARD_MK" ]; then
        echo "Board makefile not found: $BOARD_MK" >&2
        exit 1
    fi
    insert_block_after_line "$BOARD_MK" "CIRCUITPY_ESP_PSRAM_FREQ = 200m" "$LVGL_ENABLE_BLOCK"
    log

    log "==> Patch board mpconfigboard.h (ifndef guard)"
    if [ -f "$BOARD_H" ]; then
        BOARD_H_BLOCK="#ifndef CIRCUITPY_LVGL
#define CIRCUITPY_LVGL (0)
#endif"
        insert_block_after_line "$BOARD_H" "#pragma once" "$BOARD_H_BLOCK"
    fi
    log
fi

log "==> Patch py/circuitpy_mpconfig.mk (default off)"
MPCONFIG_BLOCK="CIRCUITPY_LVGL ?= 0
CFLAGS += -DCIRCUITPY_LVGL=\$(CIRCUITPY_LVGL)"
insert_block_after_line "$MPCONFIG_MK" "CFLAGS += -DCIRCUITPY_LOCALE=\$(CIRCUITPY_LOCALE)" "$MPCONFIG_BLOCK"
log

log "==> Patch py/circuitpy_defns.mk"
DEFNS_PATTERNS_BLOCK="ifeq (\$(CIRCUITPY_LVGL),1)
SRC_PATTERNS += lvgl/%
endif"
insert_block_before_line "$DEFNS_MK" "ifeq (\$(CIRCUITPY_MATH),1)" "$DEFNS_PATTERNS_BLOCK" "SRC_PATTERNS += lvgl/%"

DEFNS_LIST_BLOCK=$'\tlvgl/__init__.c \\'
insert_block_after_line "$DEFNS_MK" $'\tjpegio/JpegDecoder.c \\' "$DEFNS_LIST_BLOCK" "lvgl/__init__.c"
log

log "==> Patch port Makefile (circuitpython.mk)"
PORT_BLOCK="CMODS_DIR := \$(abspath $CMODS_REL)
include \$(CMODS_DIR)/lv_micropython_cmod/circuitpython.mk"
PORT_ANCHOR=$(port_makefile_anchor)
insert_block_after_line "$PORT_MK" "$PORT_ANCHOR" "$PORT_BLOCK"
log

if [ "$DRY_RUN" = 1 ]; then
    log "Dry run complete. Re-run with --apply to write changes."
elif [ "$APPLY" = 1 ]; then
    log "Patches applied."
    log
    log "Next:"
    log "  $LVMP_DIR/regenerate_lvcp.sh"
    log "  ./build_cp_unix.sh"
    log "  # embedded (future): ./build_cp_esp32.sh"
fi
