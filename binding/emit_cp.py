"""CircuitPython binding emission (phases 1–7).

Phased emission is controlled by ``emit_options.max_phase`` in ``emit_c.py``.
``finish_cp_fragment()`` emits the mergeable ``LVCP_MODULE_GLOBALS`` table for the
hand-written spike module in ``circuitpython_spike/``.
"""
from __future__ import print_function

import collections

from . import runtime
from .analyze import get_enum_members, get_enum_member_name, get_enum_value
from .helpers import (
    get_enum_name,
    is_method_of,
    method_name_from_func_name,
    sanitize,
    simplify_identifier,
)


def _module_global_entries(
    max_phase,
    int_constants,
    generated_globals,
    enums,
    enum_referenced,
    generated_structs=None,
    struct_aliases=None,
    obj_names=None,
    module_funcs=None,
):
    entries = []
    if max_phase >= 1:
        for int_constant in int_constants:
            entries.append(
                "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(MP_ROM_INT({value})) }}".format(
                    name=sanitize(get_enum_name(int_constant)),
                    value=int_constant,
                )
            )
        for global_name in generated_globals:
            entries.append(
                "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_{global_name}) }}".format(
                    name=sanitize(simplify_identifier(global_name)),
                    global_name=global_name,
                )
            )
    if max_phase >= 2:
        for enum_name in enums.keys():
            if enum_name in enum_referenced:
                continue
            entries.append(
                "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_lv_{enum}_type_base) }}".format(
                    name=sanitize(get_enum_name(enum_name)),
                    enum=enum_name,
                )
            )
    if max_phase >= 3:
        if generated_structs:
            for struct_name in generated_structs:
                if not generated_structs[struct_name]:
                    continue
                entries.append(
                    "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_{struct_name}_type) }}".format(
                        name=sanitize(simplify_identifier(struct_name)),
                        struct_name=sanitize(struct_name),
                    )
                )
        if struct_aliases:
            for struct_name in struct_aliases:
                entries.append(
                    "    {{ MP_ROM_QSTR(MP_QSTR_{alias_name}), MP_ROM_PTR(&mp_{struct_name}_type) }}".format(
                        struct_name=sanitize(struct_name),
                        alias_name=sanitize(simplify_identifier(struct_aliases[struct_name])),
                    )
                )
    if max_phase >= 5 and obj_names:
        for obj_name in obj_names:
            entries.append(
                "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_lv_{obj}_type_base) }}".format(
                    name=sanitize(obj_name),
                    obj=sanitize(obj_name),
                )
            )
    if max_phase >= 6 and module_funcs:
        for func in module_funcs:
            entries.append(
                "    {{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_{func}_mpobj) }}".format(
                    name=sanitize(simplify_identifier(func.name)),
                    func=func.name,
                )
            )
    return entries


def finish_cp_fragment(max_phase):
    """Emit mergeable module entry table for shared-bindings/lvgl/__init__.c."""
    int_constants = runtime.get("int_constants", [])
    generated_globals = runtime.get("generated_globals", [])
    enums = runtime.get("enums", {})
    enum_referenced = runtime.get("enum_referenced", collections.OrderedDict())
    generated_structs = runtime.get("generated_structs", {})
    struct_aliases = runtime.get("struct_aliases", collections.OrderedDict())
    obj_names = runtime.get("obj_names", [])
    module_funcs = runtime.get("module_funcs", [])

    entries = _module_global_entries(
        max_phase,
        int_constants,
        generated_globals,
        enums,
        enum_referenced,
        generated_structs=generated_structs,
        struct_aliases=struct_aliases,
        obj_names=obj_names,
        module_funcs=module_funcs,
    )

    print(
        """
/*
 * CircuitPython phase-{phase} module entries.
 * Include from shared-bindings/lvgl/__init.c when LVGL_GENERATED_PHASE1 is set.
 * Object definitions live above in this file.
 */

#ifndef LVCP_MODULE_GLOBALS_H
#define LVCP_MODULE_GLOBALS_H

#define LVCP_MODULE_GLOBALS \\""".format(
            phase=max_phase
        )
    )

    if entries:
        print(", \\\n".join(entries))
    else:
        print("    /* no module entries */")

    print(
        """
#endif /* LVCP_MODULE_GLOBALS_H */

/* Backward-compatible alias for phase-1 spike templates */
#define LVCP_PHASE1_MODULE_GLOBALS LVCP_MODULE_GLOBALS

const mp_rom_map_elem_t lvgl_module_entries[] = {{
{table}
}};

const size_t lvgl_module_entry_count = sizeof(lvgl_module_entries) / sizeof(lvgl_module_entries[0]);
""".format(
            table=",\n".join(entries) if entries else "    /* no module entries */"
        )
    )

    runtime.set_("generated_globals", generated_globals)
    runtime.set_("int_constants", int_constants)
    runtime.set_("enum_referenced", enum_referenced)


def finish_phase1_fragment():
    """Emit phase-1 module entry table (alias for finish_cp_fragment(1))."""
    finish_cp_fragment(1)


def emit_phase2_enums():
    """Emit enum type objects (same C shape as emit_c.gen_obj for enum keys)."""
    if runtime.get("_cp_enums_emitted", False):
        return
    runtime.set_("_cp_enums_emitted", True)
    enums = runtime.get("enums", {})
    obj_metadata = runtime.get("obj_metadata")
    enum_referenced = collections.OrderedDict()
    module_name = runtime.get("module_name", "lvgl")

    print(
        """
/*
 * CircuitPython phase-2 enum type objects
 */
"""
    )

    for obj_name in list(enums.keys()):
        obj_metadata[obj_name] = {"members": collections.OrderedDict()}

        enum_members = [
            "{{ MP_ROM_QSTR(MP_QSTR_{enum_member}), MP_ROM_PTR({enum_member_value}) }}".format(
                enum_member=sanitize(get_enum_member_name(enum_member_name)),
                enum_member_value=get_enum_value(obj_name, enum_member_name),
            )
            for enum_member_name in get_enum_members(obj_name)
        ]
        obj_metadata[obj_name]["members"].update(
            {
                get_enum_member_name(enum_member_name): {"type": "enum_member"}
                for enum_member_name in get_enum_members(obj_name)
            }
        )

        obj_enums = [
            enum_name for enum_name in enums.keys() if is_method_of(enum_name, obj_name)
        ]
        enum_types = [
            "{{ MP_ROM_QSTR(MP_QSTR_{name}), MP_ROM_PTR(&mp_lv_{enum}_type_base) }}".format(
                name=sanitize(method_name_from_func_name(enum_name)), enum=enum_name
            )
            for enum_name in obj_enums
        ]
        obj_metadata[obj_name]["members"].update(
            {
                method_name_from_func_name(enum_name): {"type": "enum_type"}
                for enum_name in obj_enums
            }
        )
        for enum_name in obj_enums:
            if enum_name in obj_metadata:
                obj_metadata[obj_name]["members"][
                    method_name_from_func_name(enum_name)
                ].update(obj_metadata[enum_name])
            enum_referenced[enum_name] = True

        locals_dict_entries = ",\n    ".join(enum_members + enum_types)

        print(
            """
/*
 * {module_name} {obj} object definitions
 */

static const mp_rom_map_elem_t {obj}_locals_dict_table[] = {{
    {locals_dict_entries}
}};

static MP_DEFINE_CONST_DICT({obj}_locals_dict, {obj}_locals_dict_table);

static void {obj}_print(const mp_print_t *print,
    mp_obj_t self_in,
    mp_print_kind_t kind)
{{
    mp_printf(print, "{module_name} {obj}");
}}

static MP_DEFINE_CONST_OBJ_TYPE(
    mp_lv_{obj}_type_base,
    MP_QSTR_{obj},
    MP_TYPE_FLAG_NONE,
    print, {obj}_print,
    attr, call_parent_methods,
    locals_dict, &{obj}_locals_dict
);

GENMPY_UNUSED static const mp_lv_obj_type_t mp_lv_{obj}_type = {{
#ifdef LV_OBJ_T
    .lv_obj_class = NULL,
#endif
    .mp_obj_type = &mp_lv_{obj}_type_base,
}};
""".format(
                module_name=module_name,
                obj=sanitize(obj_name),
                locals_dict_entries=locals_dict_entries,
            )
        )

    runtime.set_("obj_metadata", obj_metadata)
    runtime.set_("enum_referenced", enum_referenced)
