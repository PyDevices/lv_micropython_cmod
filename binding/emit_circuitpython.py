"""Generate CircuitPython LVGL binding C source.

See binding/circuitpython_emit_plan.md for phased emission and MP→CP API mapping.
"""

from __future__ import print_function

import collections

from . import emit_c as emit_c_mod
from . import runtime
from .analyze import analyze


def _init_emit_defaults(ctx):
    """Placeholder emit-phase globals so metadata export works after analysis-only runs."""
    defaults = {
        "generated_struct_functions": collections.OrderedDict(),
        "struct_aliases": collections.OrderedDict(),
        "callbacks_used_on_structs": collections.OrderedDict(),
        "generated_callbacks": collections.OrderedDict(),
        "generated_funcs": collections.OrderedDict(),
        "enum_referenced": collections.OrderedDict(),
        "generated_obj_names": collections.OrderedDict(),
        "generated_globals": [],
        "module_funcs": [],
        "functions_not_generated": collections.OrderedDict(),
    }
    for name, value in defaults.items():
        if name not in runtime.export_names():
            continue
        runtime.set_(name, value)
    if not hasattr(ctx, "headers") or ctx.headers is None:
        runtime.set_("headers", list(ctx.args.input))


def emit_circuitpython(ctx):
    """Run shared analysis and emit CircuitPython C source to ctx.emit_print."""
    runtime.set_(
        "emit_options",
        {"target": "circuitpython", "max_phase": 7},
    )
    analyze()
    _init_emit_defaults(ctx)
    runtime.absorb_from(__import__("binding.analyze", fromlist=["analyze"]))
    runtime.publish(__import__("sys").modules)
    emit_c_mod.emit_c()


def run(ctx):
    ctx.init_patterns()
    runtime.sync_from_ctx(ctx)
    try:
        emit_circuitpython(ctx)
    finally:
        runtime.absorb_from(__import__("binding.analyze", fromlist=["analyze"]))
        runtime.absorb_from(emit_c_mod)
        runtime.sync_to_ctx(ctx)
