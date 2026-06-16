# This file is used by MicroPython CMake-based builds such as the ESP32 and RP2 ports.
# For Make-based builds, see the .mk file in the same directory.

# When building Micropython, this file is to be given as:
#     make USER_C_MODULES=<path to this directory>/micropython.cmake

set(LVMP_DIR ${CMAKE_CURRENT_LIST_DIR})
set(LVMP_C ${LVMP_DIR}/generated/lvmp.c)
set(LVGL_DIR ${LVMP_DIR}/lvgl)
file(GLOB_RECURSE SOURCES ${LVGL_DIR}/src/*.c ${LVMP_DIR}/lv_mem_core_micropython.c)

if(NOT EXISTS ${LVMP_C})
    message(FATAL_ERROR "${LVMP_C} not found. Run ${LVMP_DIR}/regenerate_lvmp.sh after changing lvgl, lv_conf.h, or gen_mpy.py")
endif()

add_library(lv_micropython INTERFACE)
target_sources(lv_micropython INTERFACE ${LVMP_C})
target_include_directories(lv_micropython INTERFACE ${LVMP_DIR})
target_link_libraries(usermod INTERFACE lv_micropython)

add_library(lvgl INTERFACE)
target_sources(lvgl INTERFACE ${SOURCES})
target_compile_options(lvgl INTERFACE -Wno-unused-function)
target_link_libraries(lv_micropython INTERFACE lvgl)
