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
#   - CIRCUITPY_LVGL=1 in port config (unix variant or board mpconfigboard.mk)

CMODS_LVMP_DIR ?= $(CMODS_DIR)/lv_micropython_cmod
LVGL_DIR := $(CMODS_LVMP_DIR)/lvgl
LVCP_C := $(CMODS_LVMP_DIR)/generated/lvcp.c

CMODS_LVGL_SOURCES := $(shell find $(LVGL_DIR)/src -type f -name '*.c')
# CP coverage (and jpegio) already link lib/tjpgd; LVGL's copy uses incompatible tjpgdcnf.
CMODS_LVGL_SOURCES := $(filter-out $(LVGL_DIR)/src/libs/tjpgd/tjpgd.c,$(CMODS_LVGL_SOURCES))
CMODS_LV_SOURCES := $(CMODS_LVMP_DIR)/lv_mem_core_circuitpython.c

ifeq ($(wildcard $(LVCP_C)),)
$(error $(LVCP_C) not found. Run $(CMODS_LVMP_DIR)/regenerate_lvcp.sh)
endif
CMODS_LV_SOURCES += $(LVCP_C)

# CircuitPython allocator override (see lv_conf.h + lv_mem_core_circuitpython.c)
CFLAGS += -DCMODS_CIRCUITPYTHON_BUILD=1
CFLAGS += -I$(CMODS_LVMP_DIR) -I$(LVGL_DIR) -Wno-unused-function

# Spike module + generated bindings need LVGL headers during qstr/preprocess.
$(BUILD)/shared-bindings/lvgl/%.o: CFLAGS += -I$(CMODS_LVMP_DIR) -I$(LVGL_DIR) -Wno-unused-const-variable
$(BUILD)/shared-module/lvgl/%.o: CFLAGS += -I$(CMODS_LVMP_DIR) -I$(LVGL_DIR)

# LVGL + generated bindings: suppress -Werror noise from upstream/generated C.
LVGL_SUPPRESS_CFLAGS := -Wno-cast-align -Wno-nested-externs -Wno-unused-parameter \
	-Wno-sign-compare -Wno-missing-prototypes -Wno-old-style-definition \
	-Wno-float-conversion -Wno-double-promotion -Wno-shadow
$(foreach _lvsrc,$(CMODS_LVGL_SOURCES),$(eval $(BUILD)/$(_lvsrc:.c=.o): CFLAGS += $(LVGL_SUPPRESS_CFLAGS)))
$(foreach _lvsrc,$(CMODS_LV_SOURCES),$(eval $(BUILD)/$(_lvsrc:.c=.o): CFLAGS += $(LVGL_SUPPRESS_CFLAGS)))

# LVGL + bindings + GC-aware allocator
SRC_C += $(CMODS_LVGL_SOURCES) $(CMODS_LV_SOURCES)

# Hand-written module registration lives in the CP tree:
#   shared-bindings/lvgl/__init__.c  (spike; see docs/lvgl/circuitpython_spike.md)
# Generated API surface is in generated/lvcp.c; merge via LVCP_MODULE_GLOBALS in __init__.c.
