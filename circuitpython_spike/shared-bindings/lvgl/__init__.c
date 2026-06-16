// Copy to circuitpython/shared-bindings/lvgl/__init__.c
//
// Phase 0: import lvgl; lvgl.init()
// Phase 1: merge generated constants via LVGL_GENERATED_PHASE1 (see generated/lvcp.c).

#include "py/runtime.h"
#include "py/obj.h"
#include "shared-bindings/lvgl/__init.h"
#include "shared-module/lvgl/__init.h"

//| """LVGL graphics library bindings."""
//|

//| def init() -> None:
//|     """Initialize the LVGL library. Call once before using LVGL APIs."""
//|     ...
//|
static mp_obj_t lvgl_init_obj(void) {
    lvgl_init();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(lvgl_init_obj, lvgl_init_obj);

//| def deinit() -> None:
//|     """Deinitialize LVGL."""
//|     ...
//|
static mp_obj_t lvgl_deinit_obj(void) {
    lvgl_deinit();
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(lvgl_deinit_obj, lvgl_deinit_obj);

#ifdef LVGL_GENERATED_PHASE1
/* LVCP_MODULE_GLOBALS and lvgl_module_entries[] live in generated/lvcp.c (linked via circuitpython.mk). */
extern const mp_rom_map_elem_t lvgl_module_entries[];
extern const size_t lvgl_module_entry_count;
#endif

static const mp_rom_map_elem_t lvgl_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lvgl) },
    { MP_ROM_QSTR(MP_QSTR___version__), MP_ROM_QSTR(MP_QSTR_9) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&lvgl_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit), MP_ROM_PTR(&lvgl_deinit_obj) },
#ifdef LVGL_GENERATED_PHASE1
    LVCP_MODULE_GLOBALS
#endif
};

static MP_DEFINE_CONST_DICT(lvgl_module_globals, lvgl_module_globals_table);

const mp_obj_module_t lvgl_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&lvgl_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_module);

void lvgl_init(void) {
    shared_modules_lvgl_init();
}

void lvgl_deinit(void) {
    shared_modules_lvgl_deinit();
}
