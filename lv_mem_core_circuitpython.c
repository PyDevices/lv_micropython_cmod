/**
 * @file lv_mem_core_circuitpython.c
 *
 * GC-aware LVGL heap for CircuitPython.
 *
 * Wire up by:
 *   1. In lv_conf.h (CP build only):
 *        #define LV_STDLIB_CIRCUITPYTHON_OVERRIDE 253
 *        #define LV_USE_STDLIB_MALLOC LV_STDLIB_CIRCUITPYTHON_OVERRIDE
 *   2. Add this file to the CircuitPython board / extmod sources list.
 *
 * Uses CircuitPython's m_malloc/m_realloc/m_free, which route through the
 * garbage-collected heap (see py/malloc.c).
 */

/*********************
 *      INCLUDES
 *********************/
#include "lvgl/src/stdlib/lv_mem.h"

/* Must match lv_conf.h when building for CircuitPython. */
#ifndef LV_STDLIB_CIRCUITPYTHON_OVERRIDE
#define LV_STDLIB_CIRCUITPYTHON_OVERRIDE 253
#endif

#if LV_USE_STDLIB_MALLOC == LV_STDLIB_CIRCUITPYTHON_OVERRIDE

#include <py/mpconfig.h>
#include <py/misc.h>
#if MICROPY_MALLOC_USES_ALLOCATED_SIZE
#include <py/gc.h>
#endif

/*********************
 *      DEFINES
 *********************/

/**********************
 *   GLOBAL FUNCTIONS
 **********************/

void lv_mem_init(void)
{
    /* Nothing to init — CP heap is already running. */
}

void lv_mem_deinit(void)
{
    /* Nothing to deinit. */
}

lv_mem_pool_t lv_mem_add_pool(void *mem, size_t bytes)
{
    LV_UNUSED(mem);
    LV_UNUSED(bytes);
    return NULL;
}

void lv_mem_remove_pool(lv_mem_pool_t pool)
{
    LV_UNUSED(pool);
}

void *lv_malloc_core(size_t size)
{
#if MICROPY_MALLOC_USES_ALLOCATED_SIZE
    return gc_alloc(size, true);
#else
    return m_malloc(size);
#endif
}

void *lv_realloc_core(void *p, size_t new_size)
{
#if MICROPY_MALLOC_USES_ALLOCATED_SIZE
    return gc_realloc(p, new_size, true);
#else
    return m_realloc(p, new_size);
#endif
}

void lv_free_core(void *p)
{
#if MICROPY_MALLOC_USES_ALLOCATED_SIZE
    gc_free(p);
#else
    m_free(p);
#endif
}

void lv_mem_monitor_core(lv_mem_monitor_t *mon_p)
{
    LV_UNUSED(mon_p);
}

lv_result_t lv_mem_test_core(void)
{
    return LV_RESULT_OK;
}

#endif /* LV_USE_STDLIB_MALLOC == LV_STDLIB_CIRCUITPYTHON_OVERRIDE */
