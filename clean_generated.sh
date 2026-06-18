#!/usr/bin/env bash
# Remove generated bindings and generator caches. Safe to run anytime; regenerate before building.
set -e

LVMP_DIR=$(cd "$(dirname "$0")" && pwd)
CMODS_DIR=$(cd "$LVMP_DIR/.." && pwd)

rm -rf "$LVMP_DIR/generated"/*
rm -f "$CMODS_DIR/lextab.py" "$CMODS_DIR/yacctab.py"
rm -f "$LVMP_DIR/lextab.py" "$LVMP_DIR/yacctab.py"

echo "Cleaned generated/ and pycparser table caches."
echo "Regenerate before building:"
echo "  $LVMP_DIR/regenerate_lvmp.sh"
echo "  $LVMP_DIR/regenerate_lvcp.sh   # CircuitPython"
