# CircuitPython binding emission plan

This document maps MicroPython output (`emit_c.py` / `generated/lvmp.c`) to CircuitPython
targets (`emit_circuitpython.py` / future `generated/lvcp.c`). Use `generated/lvmp.c.json`
(or `lvcp.c.json` from `regenerate_lvcp.sh`) as the authoritative API checklist.

Current metadata scale (LVGL 9.x config in this repo):

| Section | Count | Emitter phase |
|---------|------:|---------------|
| `int_constants` | 24 | 1 — module integers |
| `blobs` | 63 | 1 — string / pointer globals |
| `enums` | 59 | 2 — enum types + members |
| `structs` | 101 | 3 — struct wrappers |
| `struct_functions` | 61 | 4 — methods on struct types |
| `objects` | 41 | 5 — LVGL widget/object types |
| `functions` | 221 | 6 — module-level + static calls |

Display flush/tick callbacks are **not** part of C emission. **Display bridge: ON HOLD** until
explicitly resumed (planned: Python `displayio` registration at runtime).

---

## Architecture

### MicroPython today

One generated translation unit (`lvmp.c`) registered via `MP_REGISTER_MODULE`, plus:

- `micropython.mk` / `micropython.cmake` → `USER_C_MODULES`
- LVGL sources compiled as a library
- `lv_mem_core_micropython.c` for GC-aware heap

### CircuitPython target

Split into **three layers**:

1. **Build glue (in cmods)** — `circuitpython.mk`, LVGL sources, `lv_mem_core_circuitpython.c`, generated `lvcp.c`
2. **Hand-written spike (in CP tree)** — `shared-bindings/lvgl/__init__.c` until emission covers module registration
3. **Generated API (in cmods)** — `emit_circuitpython.py` → `generated/lvcp.c`, compiled via `SRC_C +=` in `circuitpython.mk`

LVGL is port-independent; there is no meaningful `common-hal/lvgl/` per chip. Use
`shared-module/lvgl/` for thin port-independent helpers only (e.g. `lv_init` wrapper).

---

## MicroPython → CircuitPython API mapping

CircuitPython shares the same `py/` runtime as MicroPython, but idioms differ in
shared-bindings modules (RST doc comments, `mp_arg_parse_all`, explicit `shared-module`
calls).

| MicroPython (`emit_c.py`) | CircuitPython target | Notes |
|---------------------------|----------------------|-------|
| `MP_REGISTER_MODULE(MP_QSTR_lvgl, …)` | Same macro in `shared-bindings/lvgl/__init__.c` or generated tail | Module must appear in `circuitpy_defns.mk` when `CIRCUITPY_LVGL=1` |
| `MP_DEFINE_CONST_LV_FUN_OBJ_VAR` | `MP_DEFINE_CONST_FUN_OBJ_VAR` or `MP_DEFINE_CONST_FUN_OBJ_KW` | Prefer CP keyword parsing for optional args |
| `mp_lv_obj_fun_builtin_var_t` + custom type slots | Standard `mp_obj_type_t` with `call` slot, or `mp_obj_fun_builtin_var_t` | CP modules rarely use custom fun types; simplify where possible |
| `mp_lv_obj_type_t` + `MP_DEFINE_CONST_OBJ_TYPE` | `MP_DEFINE_CONST_OBJ_TYPE` with `make_new`, `locals_dict`, `parent` | Map inheritance via `parent` slot instead of embedding base methods |
| `mp_lv_struct_t` + buffer protocol | Same pattern or `struct` module-style accessors | Keep buffer export for zero-copy struct fields |
| `mp_to_lv` / `lv_to_mp` convertors | Reuse logic; includes stay `py/obj.h`, `py/binary.h` | No `py/objarray.h` dependency if avoidable on CP |
| Callback dict (`mp_lv_callback`) | `mp_obj_t` stored on object; `mp_sched_schedule` or direct call | CP: ensure callbacks are GC roots; document lifetime |
| `MP_DEFINE_STR_OBJ` for string enums | Same | |
| `MP_ROM_INT` enum members on objects | Same | |
| Nested `gen_obj` / `gen_mp_func` | Same pipeline in `emit_circuitpython.py`, different templates | Share `analyze.py`; fork templates only |

### Headers

MicroPython emission pulls:

```c
#include "py/obj.h"
#include "py/runtime.h"
#include "py/binary.h"
#include "py/objarray.h"
...
```

CircuitPython emission should use:

```c
#include "py/runtime.h"
#include "py/obj.h"
#include "py/binary.h"
#include "shared-bindings/lvgl/__init__.h"   /* when splitting hand-written vs generated */
```

Drop MicroPython-only helpers unless a port still needs them.

---

## Phased rollout

Each phase should compile and import before the next. Verify with a minimal board build.

### Phase 0 — Hand-written spike (in CP tree)

**Goal:** `import lvgl` works; `lvgl.init()` calls `lv_init()`.

Files in CircuitPython:

- `shared-bindings/lvgl/__init__.c` — module dict, `init()`, `__version__`
- `shared-module/lvgl/__init.c` — `void lvgl_init(void)` → `lv_init()`
- `circuitpython.mk` included from port Makefile with `CMODS_LVGL_ALLOW_MISSING_BINDINGS=1`

No generator output required.

### Phase 1 — Module integers and string globals (done)

**Metadata:** `int_constants` (24), `blobs` (63)

**Emitter:** `--target circuitpython`, `max_phase: 1` — globals and blobs only; appends
`LVCP_MODULE_GLOBALS` via `binding/emit_cp.py`.

### Phase 2 — Enum types (done)

**Metadata:** `enums` (84 keys; ~59 top-level module entries after `enum_referenced` filtering)

**Emitter:** `max_phase: 2` — phase 1 output plus enum type objects (`emit_phase2_enums()`).
Module dict macro gains `MP_ROM_PTR(&mp_lv_<ENUM>_type_base)` entries for enums not
nested inside another enum type.

**CP pattern:** same `LVCP_MODULE_GLOBALS` splice in `shared-bindings/lvgl/__init__.c`.

### Phase 3 — Struct types (done)

**Metadata:** `structs` (~177 generated types in `lvcp.c` today)

**Emitter:** `max_phase: 3` — phases 1–2 plus `try_generate_struct` for all AST structs and
`_emit_struct_locals_dicts(include_methods=False)` (field accessors + `__SIZE__`, no struct methods).

**CP pattern:** module dict macro gains `MP_ROM_PTR(&mp_<struct>_type)` entries and struct aliases.

### Phase 4 — Struct methods (done)

**Emitter:** `max_phase >= 4` — `try_generate_structs_from_first_argument()` plus
`_emit_struct_locals_dicts(include_methods=True)`.

### Phase 5 — LVGL objects (done)

**Metadata:** `objects` (41)

**Emitter:** `max_phase >= 5` — widget `gen_obj` loop inside `emit_c` (requires `LV_OBJ_T` header).

### Phase 6 — Module-level functions (done)

**Metadata:** `functions` (221)

**Emitter:** `max_phase >= 6` — module `gen_mp_func` loop; entries merged via `finish_cp_fragment(6+)`.

### Phase 7 — Callbacks (done)

**Emitter:** `max_phase >= 7` — struct-field callback trampolines (`gen_callback_func` / `callbacks_used_on_structs`).

**Full CP build today:** `max_phase: 7` in `emit_circuitpython.py` → ~39.5k-line `lvcp.c` (parity with `lvmp.c`).

---

## `emit_circuitpython.py` structure (proposed)

Mirror `emit_micropython.py`:

```
emit_circuitpython.py
  run(ctx)           — sync runtime, call emit_cp(), absorb, sync_to_ctx
  emit_cp()          — orchestrator (like emit_c())
    emit_header()    — includes, CP-specific macros
    emit_convertors() — share with emit_c via emit_templates.py (future)
    emit_enums()
    emit_structs()
    emit_objects()
    emit_functions()
    emit_module()    — module dict + MP_REGISTER_MODULE
```

Start by extracting **string templates** from `emit_c.py` into target-specific template functions rather than duplicating 2900 lines.

Suggested first automated emission: **Phase 1 only** (constants), behind `--target circuitpython`, with `compare` tests against metadata JSON counts.

---

## Build / regenerate workflow

```bash
# Metadata + stub (today)
./lv_micropython_cmod/regenerate_lvcp.sh

# Full CP firmware (once port is wired)
CMODS_DIR=/path/to/cmods BOARD=your_board ./build_circuitpython.sh
```

Output files:

| File | Purpose |
|------|---------|
| `generated/lvcp.c.pp` | Preprocessed headers (shared with MP) |
| `generated/lvcp.c` | Generated CP bindings (stub → full emission) |
| `generated/lvcp.c.json` | API checklist for emit phases |

---

## Open questions (resolve during spike)

1. **Single TU vs split:** One `lvcp.c` (~40k lines like `lvmp.c`) is simplest for linking; splitting by object family helps incremental compile only if build time hurts.
2. **ROM budget:** Full API may exceed smaller boards; use `lvmp.c.json` to drive `CIRCUITPY_LVGL_FULL` vs trimmed manifests later.
3. **GC roots:** LVGL user_data + Python callbacks must be visible to CP GC — see `binding/gc_callback_audit.md`.
4. **Display bridge:** **ON HOLD** (user request).
4. **Type checking:** Keep MP `mp_to_lv` validation or adopt CP `mp_arg_validate` patterns where available.
