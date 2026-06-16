"""Shared mutable state for one LVGL binding generation run.

Consumer modules (analyze, emit_c, helpers, parse) receive mirrored globals via
publish(). Cross-module reads should use get(); cross-module writes should use
set_() so all consumers stay in sync.
"""
from __future__ import print_function

from .context import BindingContext

# Modules that mirror binding globals during generation.
_CONSUMER_MODULES = (
    "binding.analyze",
    "binding.emit_c",
    "binding.helpers",
    "binding.parse",
)


def export_names():
    return BindingContext.EXPORT_NAMES


def set_(name, value):
    """Assign a binding global and mirror it to consumer modules."""
    globals()[name] = value
    import sys

    publish(sys.modules, names=(name,))


def sync_from_ctx(ctx):
    """Load context inputs into runtime and publish to consumer modules."""
    import sys

    for name in ctx.export_names():
        if hasattr(ctx, name):
            globals()[name] = getattr(ctx, name)
    globals()["print"] = ctx.emit_print
    publish(sys.modules)


def sync_from_namespace(namespace):
    """Load a generation namespace dict into runtime (for metadata helpers)."""
    for name in export_names():
        if name in namespace:
            globals()[name] = namespace[name]


def absorb_from(module):
    """Pull binding globals from a consumer module into runtime."""
    for name in export_names():
        if hasattr(module, name):
            globals()[name] = getattr(module, name)
    if hasattr(module, "print"):
        globals()["print"] = module.print


def sync_to_ctx(ctx):
    """Write runtime state back to the binding context."""
    for name in ctx.export_names():
        if name in globals():
            setattr(ctx, name, globals()[name])


def publish(modules, names=None):
    """Copy runtime globals into consumer modules."""
    if names is None:
        names = export_names()
    for mod_name in _CONSUMER_MODULES:
        mod = modules.get(mod_name)
        if mod is None:
            continue
        for name in names:
            if name in globals():
                setattr(mod, name, globals()[name])
        if "print" in globals():
            mod.print = globals()["print"]


_MISSING = object()


def get(name, default=_MISSING):
    """Return a binding global from runtime."""
    if name in globals():
        return globals()[name]
    if default is not _MISSING:
        return default
    raise NameError(name)


class _Namespace(object):
    """Attribute access to binding globals (read/write through runtime)."""

    def __getattr__(self, name):
        try:
            return get(name)
        except NameError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        set_(name, value)


ns = _Namespace()
