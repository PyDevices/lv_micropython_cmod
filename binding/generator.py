"""LVGL binding code generation entry points."""

from __future__ import print_function

from .context import BindingContext
from .emit_micropython import run as emit_run_micropython
from .metadata import build_result


def run_micropython(args, source, pp_cmd, out, cmd_line):
    import builtins

    def emit_print(*a, **k):
        k.setdefault("file", out)
        builtins.print(*a, **k)

    ctx = BindingContext(args, source, pp_cmd, cmd_line, emit_print)
    emit_run_micropython(ctx)
    from . import helpers

    namespace = {name: getattr(ctx, name) for name in ctx.export_names()}
    namespace["simplify_identifier"] = helpers.simplify_identifier
    namespace["get_enum_name"] = helpers.get_enum_name
    return build_result(ctx), namespace


def run_circuitpython(args, source, pp_cmd, out, cmd_line):
    import builtins

    from .emit_circuitpython import run as emit_run_cp

    def emit_print(*a, **k):
        k.setdefault("file", out)
        builtins.print(*a, **k)

    ctx = BindingContext(args, source, pp_cmd, cmd_line, emit_print)
    emit_run_cp(ctx)
    emitted = True
    from . import helpers

    namespace = {}
    for name in ctx.export_names():
        if hasattr(ctx, name):
            namespace[name] = getattr(ctx, name)
    namespace["simplify_identifier"] = helpers.simplify_identifier
    namespace["get_enum_name"] = helpers.get_enum_name
    return build_result(ctx), namespace, emitted
