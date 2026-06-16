"""Generate MicroPython LVGL binding C source."""
from __future__ import print_function

import builtins

from . import emit_c as emit_c_mod
from . import runtime
from .analyze import analyze

print = builtins.print


def run(ctx):
    ctx.init_patterns()
    runtime.sync_from_ctx(ctx)
    try:
        analyze()
        runtime.absorb_from(__import__("binding.analyze", fromlist=["analyze"]))
        runtime.publish(__import__("sys").modules)
        emit_c_mod.emit_c()
    finally:
        runtime.absorb_from(emit_c_mod)
        runtime.sync_to_ctx(ctx)
