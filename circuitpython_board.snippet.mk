# --- Paste/adapt into circuitpython/ when wiring LVGL ---
#
# Default dev target: unix + coverage variant (see apply_cp_lvgl_patches.sh)
#
# 1a) Unix variant mpconfigvariant.mk  (ports/unix/variants/coverage/mpconfigvariant.mk)
#
#    CIRCUITPY_LVGL = 1
#    CFLAGS += -DCIRCUITPY_LVGL=1
#    CFLAGS += -DLVGL_GENERATED_PHASE1=1
#
# 1b) Board mpconfigboard.mk  (ESP32-P4: ports/espressif/boards/espressif_esp32p4_function_ev/mpconfigboard.mk)
#
#    CIRCUITPY_LVGL = 1
#    # After regenerate_lvcp.sh and spike merge:
#   CFLAGS += -DLVGL_GENERATED_PHASE1=1
#
# 2) py/circuitpy_defns.mk  (near other CIRCUITPY_* module guards)
#
#    ifeq ($(CIRCUITPY_LVGL),1)
#    SRC_PATTERNS += lvgl/%
#    endif
#
#    # In SRC_SHARED_MODULE_ALL += \  (alphabetical; add lvgl block)
#    lvgl/__init__.c \
#
# 3) py/circuitpy_modules.mk  (or the generated module list source)
#
#    ifeq ($(CIRCUITPY_LVGL),1)
#    SRC_PATTERNS += lvgl
#    endif
#
# 4) ports/<port>/Makefile
#
#    Unix (after include ../../py/mkenv.mk):
#    Espressif (after include ../../py/circuitpy_mkenv.mk):
#
#    CMODS_DIR := $(abspath ../../../cmods)    # path from port to this repo
#    include $(CMODS_DIR)/lv_micropython_cmod/circuitpython.mk
#
# 5) Copy circuitpython_spike/ templates into the CP tree (circuitpython_spike/README.md)
#
#    shared-bindings/lvgl/__init.c
#    shared-bindings/lvgl/__init.h
#    shared-module/lvgl/__init.c
#    shared-module/lvgl/__init.h
#
# 6) mpconfigport.h, mpconfigvariant.h, or mpconfigboard.h
#
#    #ifndef CIRCUITPY_LVGL
#    #define CIRCUITPY_LVGL (0)
#    #endif
#
# Display bridge: ON HOLD (see README.md). Flush/tick are not in these C files.
