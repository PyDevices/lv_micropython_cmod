#!/usr/bin/env bash
exec "$(cd "$(dirname "$0")/.." && pwd)/lv_bindings/verify_bindings.sh" "$@"
