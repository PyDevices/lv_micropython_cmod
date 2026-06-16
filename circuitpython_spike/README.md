# CircuitPython Phase 0 spike templates

Target board: **[ESP32-P4-Function-EV-Board](https://circuitpython.org/board/espressif_esp32p4_function_ev/)**
(`BOARD=espressif_esp32p4_function_ev`, `ports/espressif`).

Copy these files into a CircuitPython tree after `circuitpython/` is in place.
Follow `circuitpython_board.snippet.mk` for `CIRCUITPY_LVGL`, `circuitpy_defns.mk`, and
`circuitpython.mk` wiring.

## Layout in CircuitPython

```
circuitpython/
  shared-bindings/lvgl/__init__.c   ← from here (+ phase-1 merge below)
  shared-bindings/lvgl/__init.h
  shared-module/lvgl/__init.c
  shared-module/lvgl/__init.h
```

Generated bindings (not copied wholesale):

```
cmods/lv_micropython_cmod/generated/lvcp.c   ← regenerate_lvcp.sh
```

## Build flow

1. Apply CP tree patches (dry-run first):

```bash
./lv_micropython_cmod/apply_cp_lvgl_patches.sh --dry-run
./lv_micropython_cmod/apply_cp_lvgl_patches.sh --apply
```

Spike files to copy are listed in `copy_manifest.txt` (tab-separated dir/filename — avoids bash `$__init__` expansion).

2. `CIRCUITPY_LVGL=1` on the P4 board `mpconfigboard.mk` (patch script adds this).
3. Port `Makefile` includes `$(CMODS_DIR)/lv_micropython_cmod/circuitpython.mk` (patch script adds this).

Display flush/tick: **ON HOLD** — not in these C files. See `binding/gc_callback_audit.md` and README.

## Merging `lvcp.c` into the spike module

Phases 1–7 (`max_phase: 7`) emit the full API surface. Output is `lvcp.c`
(~39.5k lines today, comparable to `lvmp.c`) containing:

- Constants, blobs, enums, structs (with methods), widget types, module functions, callbacks
- A mergeable tail: `LVCP_MODULE_GLOBALS` macro plus `lvgl_module_entries[]`

The hand-written spike keeps `init` / `deinit` / `__version__`. Generated symbols are **not**
registered via `MP_REGISTER_MODULE` in `lvcp.c`; they are spliced into the spike dict.

### Step A — compile `lvcp.c`

`circuitpython.mk` adds `$(CMODS_DIR)/lv_micropython_cmod/generated/lvcp.c` to the port build.
Blob/string object definitions in `lvcp.c` must be linked before the spike module references `&mp_<blob>`.

### Step B — expand the globals table

In `shared-bindings/lvgl/__init.c`, when `LVGL_GENERATED_PHASE1` is defined:

```c
#ifdef LVGL_GENERATED_PHASE1
/* LVCP_MODULE_GLOBALS and lvgl_module_entries[] are at the tail of lvcp.c */
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
```

`LVCP_MODULE_GLOBALS` is a backslash-continued macro in `lvcp.c` (~590 module-level entries
for a full phase-7 build). `LVCP_PHASE1_MODULE_GLOBALS` is a backward-compatible alias.
Re-run `regenerate_lvcp.sh` after LVGL header changes.

### What remains outside generated C

- `MP_REGISTER_MODULE` — the spike module in `shared-bindings/lvgl/__init__.c` owns registration
- Display flush/tick — **ON HOLD** (Python bridge; resume when requested)
- `MP_REGISTER_MODULE` in generated C (CP uses the spike module only)

See `binding/circuitpython_emit_plan.md` for later phases.
