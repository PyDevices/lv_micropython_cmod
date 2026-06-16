import collections
import json

from .helpers import sanitize
from .model import GenerationResult


def _struct_functions_metadata(namespace):
    from .analyze import get_struct_functions, noncommon_part

    from . import runtime

    runtime.sync_from_namespace(namespace)
    metadata = collections.OrderedDict()
    for struct_name, generated in namespace["generated_structs"].items():
        if not generated:
            continue
        struct_funcs = get_struct_functions(struct_name)
        if not struct_funcs:
            continue
        members = collections.OrderedDict()
        for func in struct_funcs:
            if func.name not in namespace["func_metadata"]:
                continue
            member_name = sanitize(noncommon_part(func.name, struct_name))
            members[member_name] = namespace["func_metadata"][func.name]
        if members:
            metadata[namespace["simplify_identifier"](struct_name)] = members
    return metadata


def save_metadata(namespace, path):
    simplify_identifier = namespace["simplify_identifier"]
    get_enum_name = namespace["get_enum_name"]

    metadata = collections.OrderedDict()
    metadata["objects"] = {
        obj_name: namespace["obj_metadata"].get(
            obj_name, {"members": collections.OrderedDict()}
        )
        for obj_name in namespace["obj_names"]
    }
    metadata["functions"] = {
        simplify_identifier(f.name): namespace["func_metadata"][f.name]
        for f in namespace["module_funcs"]
    }
    metadata["enums"] = {
        get_enum_name(enum_name): namespace["obj_metadata"].get(
            enum_name, {"members": collections.OrderedDict()}
        )
        for enum_name in namespace["enums"].keys()
        if enum_name not in namespace["enum_referenced"]
    }
    metadata["structs"] = [
        simplify_identifier(struct_name)
        for struct_name in namespace["generated_structs"]
        if namespace["generated_structs"][struct_name]
    ]
    metadata["structs"] += [
        simplify_identifier(namespace["struct_aliases"][struct_name])
        for struct_name in namespace["struct_aliases"].keys()
    ]
    metadata["struct_functions"] = _struct_functions_metadata(namespace)
    metadata["blobs"] = [
        simplify_identifier(global_name)
        for global_name in namespace["generated_globals"]
    ]
    metadata["int_constants"] = [
        get_enum_name(int_constant) for int_constant in namespace["int_constants"]
    ]

    with open(path, "w") as metadata_file:
        json.dump(metadata, metadata_file, indent=4)


def build_result(ctx):
    return GenerationResult(
        module_name=ctx.module_name,
        module_prefix=ctx.module_prefix,
        obj_names=ctx.obj_names,
        obj_metadata=ctx.obj_metadata,
        func_metadata=ctx.func_metadata,
        module_funcs=ctx.module_funcs,
        enums=ctx.enums,
        enum_referenced=ctx.enum_referenced,
        generated_structs=ctx.generated_structs,
        struct_aliases=ctx.struct_aliases,
        generated_globals=ctx.generated_globals,
        int_constants=ctx.int_constants,
        headers=getattr(ctx, "headers", []),
        pp_cmd=ctx.pp_cmd,
        cmd_line=ctx.cmd_line,
    )
