# CircuitPython build glue for LVGL + generated bindings.
#
# Include from a CircuitPython port Makefile after setting CMODS_DIR to the cmods
# repo root (the parent of lv_micropython_cmod/):
#
#   CMODS_DIR := $(abspath ../../cmods)          # adjust relative to port dir
#   include $(CMODS_DIR)/lv_micropython_cmod/circuitpython.mk
#
# Requires:
#   - generated/lvcp.c (run regenerate_lvcp.sh; see verify_bindings.sh)
#   - CIRCUITPY_LVGL=1 in the board mpconfigboard.mk (see circuitpython_board.snippet.mk)
#
# Optional: CMODS_LVGL_ALLOW_MISSING_BINDINGS=1 to compile LVGL + allocator without lvcp.c.

CMODS_LVMP_DIR ?= $(CMODS_DIR)/lv_micropython_cmod
LVGL_DIR := $(CMODS_LVMP_DIR)/lvgl
LVCP_C := $(CMODS_LVMP_DIR)/generated/lvcp.c

CMODS_LVGL_SOURCES := $(shell find $(LVGL_DIR)/src -type f -name '*.c')
CMODS_LV_SOURCES := $(CMODS_LVMP_DIR)/lv_mem_core_circuitpython.c

ifeq ($(wildcard $(LVCP_C)),)
ifeq ($(CMODS_LVGL_ALLOW_MISSING_BINDINGS),1)
$(warning $(LVCP_C) not found; building LVGL library + allocator only)
else
$(error $(LVCP_C) not found. Run $(CMODS_LVMP_DIR)/regenerate_lvcp.sh or set CMODS_LVGL_ALLOW_MISSING_BINDINGS=1 for allocator-only spike)
endif
else
CMODS_LV_SOURCES += $(LVCP_C)
endif

# CircuitPython allocator override (see lv_conf.h + lv_mem_core_circuitpython.c)
CFLAGS += -DCMODS_CIRCUITPYTHON_BUILD=1
CFLAGS += -I$(CMODS_LVMP_DIR) -Wno-unused-function

# LVGL + bindings + GC-aware allocator
SRC_C += $(CMODS_LVGL_SOURCES) $(CMODS_LV_SOURCES)

# Hand-written module registration lives in the CP tree:
#   shared-bindings/lvgl/__init__.c  (spike; see circuitpython_board.snippet.mk)
# Generated API surface is in generated/lvcp.c; merge via LVCP_MODULE_GLOBALS in __init__.c.
