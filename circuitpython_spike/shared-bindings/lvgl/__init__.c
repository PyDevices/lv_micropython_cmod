// Copy to circuitpython/shared-bindings/lvgl/__init__.c
//
// init/deinit callables here; module dict + bindings live in generated/lvcp.c.

#include "py/runtime.h"
#include "py/obj.h"
#include "shared-bindings/lvgl/__init__.h"
#include "generated/lvcp_module_globals.h"

extern void mp_lv_deinit_gc(void);

void shared_modules_lvgl_init(void);
void shared_modules_lvgl_deinit(void);

static mp_obj_t lvgl_module_init_fn(void) {
    lvgl_init();
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_init_obj, lvgl_module_init_fn);

static mp_obj_t lvgl_module_deinit_fn(void) {
    lvgl_deinit();
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_0(lvgl_deinit_obj, lvgl_module_deinit_fn);

MP_REGISTER_MODULE(MP_QSTR_lvgl, lvgl_module);

void lvgl_init(void) {
    shared_modules_lvgl_init();
}

void lvgl_deinit(void) {
    shared_modules_lvgl_deinit();
    mp_lv_deinit_gc();
}
