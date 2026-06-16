// Copy to circuitpython/shared-module/lvgl/__init.c
//
// Port-independent LVGL init wrapper (no display driver here).

#include "lvgl.h"
#include "shared-module/lvgl/__init__.h"

void shared_modules_lvgl_init(void) {
    lv_init();
}

void shared_modules_lvgl_deinit(void) {
    lv_deinit();
}
