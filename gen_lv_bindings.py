#!/usr/bin/env python3
"""Generate LVGL bindings (supported entry point)."""
from __future__ import print_function

import os
import sys

_LVMP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _LVMP_DIR)

from binding.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
