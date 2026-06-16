"""AST analysis and metadata extraction for LVGL bindings."""
from __future__ import print_function

import collections
import copy
import json
import re
from os.path import commonprefix

from pycparser import c_ast, c_generator, c_parser

from . import runtime
from .helpers import (
    ctor_name_from_obj_name,
    get_enum_name,
    is_global_callback,
    is_method_of,
    is_obj_ctor,
    is_struct,
    obj_name_from_ext_name,
    obj_name_from_func_name,
    simplify_identifier,
    str_enum_to_str,
)
from .parse import (
    add_default_declname,
    convert_array_to_ptr,
    function_prototype,
    get_name,
    get_type,
    remove_arg_names,
    remove_declname,
    remove_explicit_struct,
    remove_quals,
)
from .util import memoize


class MissingConversionException(ValueError):
    pass


def has_ctor(obj_name):
    return ctor_name_from_obj_name(obj_name) in [
        ctor.name for ctor in runtime.get("obj_ctors")
    ]


def get_ctor(obj_name):
    return next(
        ctor
        for ctor in runtime.get("obj_ctors")
        if ctor.name == ctor_name_from_obj_name(obj_name)
    )


def get_methods(obj_name):
    return [
        func
        for func in runtime.get("funcs")
        if is_method_of(func.name, obj_name)
        and (not func.name == ctor_name_from_obj_name(obj_name))
    ]


@memoize
def noncommon_part(member_name, stem_name):
    common_part = commonprefix([member_name, stem_name])
    n = len(common_part) - 1
    while n > 0 and member_name[n] != "_":
        n -= 1
    return member_name[n + 1 :]


@memoize
def get_first_arg(func):
    if not func.type.args:
        return None
    if not len(func.type.args.params) >= 1:
        return None
    if not func.type.args.params[0].type:
        return None
    return func.type.args.params[0].type


@memoize
def get_first_arg_type(func):
    first_arg = get_first_arg(func)
    if not first_arg:
        return None
    if not first_arg.type:
        return None
    return get_type(first_arg.type, remove_quals=True)


def get_base_struct_name(struct_name):
    return struct_name[:-2] if struct_name.endswith("_t") else struct_name


# "struct function" starts with struct name (without _t), and their first argument is a pointer to the struct
# Need also to take into account struct functions of aliases of current struct.
@memoize
def get_struct_functions(struct_name):
    funcs = runtime.get("funcs")
    struct_aliases = runtime.get("struct_aliases", {})
    structs = runtime.get("structs", {})
    if not struct_name:
        return []
    base_struct_name = get_base_struct_name(struct_name)
    # eprint("get_struct_functions %s: %s" % (struct_name, [get_type(func.type.args.params[0].type.type, remove_quals = True) for func in funcs if func.name.startswith(base_struct_name)]))
    # eprint("get_struct_functions %s: %s" % (struct_name, struct_aliases[struct_name] if struct_name in struct_aliases else ""))

    # for func in funcs:
    #     print("/* get_struct_functions: func=%s, struct=%s, noncommon part=%s */" % (simplify_identifier(func.name), simplify_identifier(struct_name),
    #         noncommon_part(simplify_identifier(func.name), simplify_identifier(struct_name))))

    reverse_aliases = [
        alias for alias in struct_aliases if struct_aliases[alias] == struct_name
    ]

    return (
        [
            func
            for func in funcs
            if noncommon_part(
                simplify_identifier(func.name), simplify_identifier(struct_name)
            )
            != simplify_identifier(func.name)
            and get_first_arg_type(func) == struct_name
        ]
        if (struct_name in structs or len(reverse_aliases) > 0)
        else []
    ) + (
        get_struct_functions(struct_aliases[struct_name])
        if struct_name in struct_aliases
        else []
    )


@memoize
def is_struct_function(func):
    return func in get_struct_functions(get_first_arg_type(func))


# is_static_member returns true if function does not receive the obj as the first argument
# and the object is not a struct function


@memoize
def is_static_member(func, obj_type=None):
    if obj_type is None:
        obj_type = runtime.get("base_obj_type")
    first_arg = get_first_arg(func)
    # print("/* %s : get_first_arg = %s */" % (get_name(func), first_arg))
    if first_arg:
        if isinstance(first_arg, c_ast.ArrayDecl):
            return True  # Arrays cannot have non static members
    if is_struct_function(func):
        return False
    first_arg_type = get_first_arg_type(func)
    return (first_arg_type == None) or (first_arg_type != obj_type)
def get_enum_members(obj_name):
    enums = runtime.get("enums", {})
    if obj_name not in enums:
        return []
    return [enum_member_name for enum_member_name, value in enums[obj_name].items()]


def get_enum_member_name(enum_member):
    if enum_member[0].isdigit():
        enum_member = "_" + enum_member  # needs to be a valid attribute name
    return enum_member


def get_enum_value(obj_name, enum_member):
    return runtime.get("enums")[obj_name][enum_member]

def register_int_ptr_type(convertor, *types):
    for ptr_type in types:
        for qualified_ptr_type in [ptr_type, "const " + ptr_type]:
            mp_to_lv[qualified_ptr_type] = "mp_array_to_%s" % (convertor)
            lv_to_mp[qualified_ptr_type] = "mp_array_from_%s" % (convertor)
            lv_mp_type[qualified_ptr_type] = "void*"


def analyze():
    global obj_metadata, func_metadata, callback_metadata, func_prototypes
    global parser, gen, ast, lvgl_json, forward_struct_decls
    global typedefs, synonym, struct_typedefs, structs_without_typedef
    global structs, explicit_structs, opaque_structs
    global func_defs, func_decls, all_funcs, funcs, obj_ctors, obj_names
    global parent_obj_names, enum_defs, func_typedefs, blobs, int_constants
    global mp_to_lv, lv_to_mp, lv_mp_type, lv_to_mp_byref, lv_to_mp_funcptr

    obj_metadata = collections.OrderedDict()
    func_metadata = collections.OrderedDict()
    callback_metadata = collections.OrderedDict()

    func_prototypes = {}

    parser = c_parser.CParser()
    gen = c_generator.CGenerator()
    ast = parser.parse(s, filename="<none>")

    if args.json is not None:
        with open(args.json, "r") as f:
            lvgl_json = json.load(f)
        if not lvgl_json:
            # if the json is an empty dictionary
            lvgl_json = None
    else:
        lvgl_json = None

    # *************** Fix ***********************************
    # this is a fix for structures not getting populated properly from
    # forward declarations. pycparser doesn't make the connection between
    # a forwrd declaration and the actual declaration so the structures get created
    # without any fields. Since there are no fields things like callbacks break
    # because the generation code looks for specific field names
    # to know if it is valid to be used as a callback.
    forward_struct_decls = {}

    for item in ast.ext[:]:
        # Locate a forward declaration
        if (
            isinstance(item, c_ast.Decl)
            and item.name is None
            and isinstance(item.type, c_ast.Struct)
            and item.type.name is not None
        ):
            # check to see if there are no fields , and of not store the structure
            # as a foward declaration. If it does have fields then build a single
            # object that represents the structure with the fiels.
            if item.type.decls is None:
                forward_struct_decls[item.type.name] = [item]
            else:
                if item.type.name in forward_struct_decls:
                    decs = forward_struct_decls[item.type.name]
                    if len(decs) == 2:
                        decl, td = decs

                        td.type.type.decls = item.type.decls[:]

                        ast.ext.remove(decl)
                        ast.ext.remove(item)
        # there are 3 objects that get created for a formard declaration.
        # a structure without any fields, a typedef pointing to that structure.
        # and the last is another structure that has fields. So we need to capture
        # all 3 parts to build a single object that represents a structure.
        elif (
            isinstance(item, c_ast.Typedef)
            and isinstance(item.type, c_ast.TypeDecl)
            and item.name
            and item.type.declname
            and item.name == item.type.declname
            and isinstance(item.type.type, c_ast.Struct)
            and item.type.type.decls is None
        ):
            if item.type.type.name in forward_struct_decls:
                forward_struct_decls[item.type.type.name].append(item)

    # ********************************************************************


    # Types and structs

    typedefs = [
        x.type for x in ast.ext if isinstance(x, c_ast.Typedef)
    ]  # and not (hasattr(x.type, 'declname') and lv_base_obj_pattern.match(x.type.declname))]
    # print('/* %s */' % str(typedefs))
    synonym = {}
    for t in typedefs:
        if isinstance(t, c_ast.TypeDecl) and isinstance(t.type, c_ast.IdentifierType):
            if t.declname != t.type.names[0]:
                synonym[t.declname] = t.type.names[0]
                # eprint('%s === %s' % (t.declname, t.type.names[0]))
        if isinstance(t, c_ast.TypeDecl) and isinstance(t.type, c_ast.Struct):
            if t.declname != t.type.name:
                synonym[t.declname] = t.type.name
                # eprint('%s === struct %s' % (t.declname, t.type.name))
    struct_typedefs = [typedef for typedef in typedefs if is_struct(typedef.type)]
    structs_without_typedef = collections.OrderedDict(
        (decl.type.name, decl.type)
        for decl in ast.ext
        if hasattr(decl, "type") and is_struct(decl.type)
    )

    # for typedefs that referenced to a forward declaration struct, replace it with the real definition.
    for typedef in struct_typedefs:
        if typedef.type.decls is None:  # None means it's a forward declaration
            struct_name = typedef.type.name
            # check if it's found in `structs_without_typedef`. It actually has the typedef. Replace type with it.
            if typedef.type.name in structs_without_typedef:
                typedef.type = structs_without_typedef[struct_name]

    structs = collections.OrderedDict(
        (typedef.declname, typedef.type)
        for typedef in struct_typedefs
        if typedef.declname and typedef.type.decls
    )  # and not lv_base_obj_pattern.match(typedef.declname))
    structs.update(structs_without_typedef)  # This is for struct without typedef
    explicit_structs = collections.OrderedDict(
        (typedef.type.name, typedef.declname)
        for typedef in struct_typedefs
        if typedef.type.name
    )  # and not lv_base_obj_pattern.match(typedef.type.name))
    opaque_structs = collections.OrderedDict(
        (typedef.declname, c_ast.Struct(name=typedef.declname, decls=[]))
        for typedef in typedefs
        if isinstance(typedef.type, c_ast.Struct) and typedef.type.decls == None
    )
    structs.update({k: v for k, v in opaque_structs.items() if k not in structs})
    # print('/* --> opaque structs len = %d */' % len(opaque_structs))
    # print('/* --> opaque structs  %s */' % ',\n'.join([struct_name for struct_name in opaque_structs]))
    # print('/* --> structs:\n%s */' % ',\n'.join(sorted(str(structs[struct_name]) for struct_name in structs if struct_name)))
    # print('/* --> structs_without_typedef:\n%s */' % ',\n'.join(sorted(str(structs_without_typedef[struct_name]) for struct_name in structs_without_typedef if struct_name)))
    # print('/* --> explicit_structs:\n%s */' % ',\n'.join(sorted(struct_name + " = " + str(explicit_structs[struct_name]) for struct_name in explicit_structs if struct_name)))
    # print('/* --> structs without typedef:\n%s */' % ',\n'.join(sorted(str(structs[struct_name]) for struct_name in structs_without_typedef)))

    # Functions and objects

    func_defs = [x.decl for x in ast.ext if isinstance(x, c_ast.FuncDef)]
    func_decls = [
        x
        for x in ast.ext
        if isinstance(x, c_ast.Decl) and isinstance(x.type, c_ast.FuncDecl)
    ]
    all_funcs = func_defs + func_decls
    funcs = [
        f for f in all_funcs if not f.name.startswith("_")
    ]  # functions that start with underscore are usually internal
    # eprint('... %s' % ',\n'.join(sorted('%s' % func.name for func in funcs)))
    obj_ctors = [func for func in funcs if is_obj_ctor(func)]
    # eprint('CTORS(%d): %s' % (len(obj_ctors), ', '.join(sorted('%s' % ctor.name for ctor in obj_ctors))))
    for obj_ctor in obj_ctors:
        funcs.remove(obj_ctor)
    obj_names = [create_obj_pattern.match(ctor.name).group(1) for ctor in obj_ctors]


    # All object should inherit directly from base_obj, and not according to lv_ext, as disccussed on https://github.com/littlevgl/lv_binding_micropython/issues/19
    parent_obj_names = {
        child_name: base_obj_name for child_name in obj_names if child_name != base_obj_name
    }
    parent_obj_names[base_obj_name] = None

    # Populate inheritance hierarchy according to lv_ext structures
    # exts = {obj_name_from_ext_name(ext.name): ext for ext in ast.ext if hasattr(ext, 'name') and ext.name is not None and lv_ext_pattern.match(ext.name)}
    # for obj_name, ext in exts.items():
    #     try:
    #         parent_ext_name = ext.type.type.decls[0].type.type.names[0]
    #         if lv_ext_pattern.match(parent_ext_name):
    #             parent_obj_names[obj_name] = obj_name_from_ext_name(parent_ext_name)
    #     except AttributeError:
    #         pass

    # Parse Enums

    enum_defs = [
        x for x in ast.ext if hasattr(x, "type") and isinstance(x.type, c_ast.Enum)
    ]
    enum_defs += [
        x.type
        for x in ast.ext
        if hasattr(x, "type")
        and hasattr(x.type, "type")
        and isinstance(x.type, c_ast.TypeDecl)
        and isinstance(x.type.type, c_ast.Enum)
    ]

    # parse function pointers
    func_typedefs = collections.OrderedDict(
        (t.name, t)
        for t in ast.ext
        if isinstance(t, c_ast.Typedef)
        and isinstance(t.type, c_ast.PtrDecl)
        and isinstance(t.type.type, c_ast.FuncDecl)
    )

    # Global blobs
    blobs = collections.OrderedDict(
        (decl.name, decl.type.type)
        for decl in ast.ext
        if isinstance(decl, c_ast.Decl)
        and "extern" in decl.storage
        and hasattr(decl, "type")
        and isinstance(decl.type, c_ast.TypeDecl)
        and not decl.name.startswith("_")
    )

    blobs["_nesting"] = parser.parse("extern int _nesting;").ext[0].type.type

    int_constants = []
    # Type convertors
    #


    class MissingConversionException(ValueError):
        pass


    mp_to_lv = {
        "mp_obj_t": "(mp_obj_t)",
        "va_list": None,
        "void *": "mp_to_ptr",
        "const uint8_t *": "mp_to_ptr",
        "const void *": "mp_to_ptr",
        "bool": "mp_obj_is_true",
        "char *": "(char*)convert_from_str",
        "char **": "mp_write_ptr_C_Pointer",
        "const char *": "convert_from_str",
        "const char **": "mp_write_ptr_C_Pointer",
        "%s_obj_t *" % module_prefix: "mp_to_lv",
        "uint8_t": "(uint8_t)mp_obj_get_int",
        "uint16_t": "(uint16_t)mp_obj_get_int",
        "uint32_t": "(uint32_t)mp_obj_get_int",
        "uint64_t": "(uint64_t)mp_obj_get_ull",
        "unsigned": "(unsigned)mp_obj_get_int",
        "unsigned int": "(unsigned int)mp_obj_get_int",
        "unsigned char": "(unsigned char)mp_obj_get_int",
        "unsigned short": "(unsigned short)mp_obj_get_int",
        "unsigned long": "(unsigned long)mp_obj_get_int",
        "unsigned long int": "(unsigned long int)mp_obj_get_int",
        "unsigned long long": "(unsigned long long)mp_obj_get_ull",
        "unsigned long long int": "(unsigned long long int)mp_obj_get_ull",
        "int8_t": "(int8_t)mp_obj_get_int",
        "int16_t": "(int16_t)mp_obj_get_int",
        "int32_t": "(int32_t)mp_obj_get_int",
        "int64_t": "(int64_t)mp_obj_get_ull",
        "size_t": "(size_t)mp_obj_get_int",
        "int": "(int)mp_obj_get_int",
        "char": "(char)mp_obj_get_int",
        "short": "(short)mp_obj_get_int",
        "long": "(long)mp_obj_get_int",
        "long int": "(long int)mp_obj_get_int",
        "long long": "(long long)mp_obj_get_ull",
        "long long int": "(long long int)mp_obj_get_ull",
        "float": "(float)mp_obj_get_float",
    }

    lv_to_mp = {
        "mp_obj_t": "(mp_obj_t)",
        "va_list": None,
        "void *": "ptr_to_mp",
        "const uint8_t *": "ptr_to_mp",
        "const void *": "ptr_to_mp",
        "bool": "convert_to_bool",
        "char *": "convert_to_str",
        "char **": "mp_read_ptr_C_Pointer",
        "const char *": "convert_to_str",
        "const char **": "mp_read_ptr_C_Pointer",
        "%s_obj_t *" % module_prefix: "lv_to_mp",
        "uint8_t": "mp_obj_new_int_from_uint",
        "uint16_t": "mp_obj_new_int_from_uint",
        "uint32_t": "mp_obj_new_int_from_uint",
        "uint64_t": "mp_obj_new_int_from_ull",
        "unsigned": "mp_obj_new_int_from_uint",
        "unsigned int": "mp_obj_new_int_from_uint",
        "unsigned char": "mp_obj_new_int_from_uint",
        "unsigned short": "mp_obj_new_int_from_uint",
        "unsigned long": "mp_obj_new_int_from_uint",
        "unsigned long int": "mp_obj_new_int_from_uint",
        "unsigned long long": "mp_obj_new_int_from_ull",
        "unsigned long long int": "mp_obj_new_int_from_ull",
        "int8_t": "mp_obj_new_int",
        "int16_t": "mp_obj_new_int",
        "int32_t": "mp_obj_new_int",
        "int64_t": "mp_obj_new_int_from_ll",
        "size_t": "mp_obj_new_int_from_uint",
        "int": "mp_obj_new_int",
        "char": "mp_obj_new_int",
        "short": "mp_obj_new_int",
        "long": "mp_obj_new_int",
        "long int": "mp_obj_new_int",
        "long long": "mp_obj_new_int_from_ll",
        "long long int": "mp_obj_new_int_from_ll",
        "float": "mp_obj_new_float_from_f",
    }

    lv_mp_type = {
        "mp_obj_t": "%s*" % base_obj_type,
        "va_list": None,
        "void *": "void*",
        "const uint8_t *": "void*",
        "const void *": "void*",
        "bool": "bool",
        "char *": "char*",
        "char **": "char**",
        "const char *": "char*",
        "const char **": "char**",
        "%s_obj_t *" % module_prefix: "%s*" % base_obj_type,
        "uint8_t": "int",
        "uint16_t": "int",
        "uint32_t": "int",
        "uint64_t": "int",
        "unsigned": "int",
        "unsigned int": "int",
        "unsigned char": "int",
        "unsigned short": "int",
        "unsigned long": "int",
        "unsigned long int": "int",
        "unsigned long long": "int",
        "unsigned long long int": "int",
        "int8_t": "int",
        "int16_t": "int",
        "int32_t": "int",
        "int64_t": "int",
        "size_t": "int",
        "int": "int",
        "char": "int",
        "short": "int",
        "long": "int",
        "long int": "int",
        "long long": "int",
        "long long int": "int",
        "void": None,
        "float": "float",
    }

    lv_to_mp_byref = {}
    lv_to_mp_funcptr = {}

    # Add native array supported types
    # These types would be converted automatically to/from array type.
    # Supported array (pointer) types are signed/unsigned int: 8bit, 16bit, 32bit and 64bit.

    register_int_ptr_type("u8ptr", "unsigned char *", "uint8_t *")

    register_int_ptr_type("u16ptr", "unsigned short *", "uint16_t *")

    register_int_ptr_type("i16ptr", "short *", "int16_t *")

    register_int_ptr_type(
        "u32ptr",
        "uint32_t *",
        "unsigned *",
        "unsigned int *",
        "unsigned long *",
        "unsigned long int *",
        "size_t *",
    )

    register_int_ptr_type(
        "i32ptr",
        "int32_t *",
        "signed *",
        "signed int *",
        "signed long *",
        "signed long int *",
        "long *",
        "long int *",
        "int *",
    )

    register_int_ptr_type(
        "u64ptr", "int64_t *", "signed long long *", "long long *", "long long int *"
    )

    register_int_ptr_type(
        "i64ptr", "uint64_t *", "unsigned long long *", "unsigned long long int *"
    )


    #
