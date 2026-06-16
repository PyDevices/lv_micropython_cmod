# GC and callback lifetime audit

Audit of how LVGL bindings store Python objects and whether CircuitPython's GC can collect them
prematurely. Applies to both `lvmp.c` and `lvcp.c` (same emission from `binding/emit_c.py`).

**Status:** documented 2025-06; no generator changes yet.

---

## Root pointers (`MP_REGISTER_ROOT_POINTER`)

Emitted in `emit_c.py` and present in generated bindings:

| Symbol | Purpose | Adequate? |
|--------|---------|-----------|
| `mp_lv_roots` | Holds `lv_global_t` while LVGL is initialized | Yes — LVGL global state survives GC |
| `mp_lv_user_data` | Scratch slot for **global** LVGL callbacks (`lv_global_callback_pattern`) | Partial — see below |
| `mp_lv_roots_initialized` | One-shot init flag | Yes |
| `lvgl_mod_initialized` | Module import guard | Yes |

`mp_lv_init_gc()` / `mp_lv_deinit_gc()` run from module `__init__` / teardown paths.

CircuitPython uses the same `py/gc` root-pointer machinery as MicroPython; no CP-specific
root registration is emitted today.

---

## Widget objects (`mp_lv_obj_t`)

Flow (`emit_c.py`, `lv_to_mp` / `mp_lv_delete_cb`):

1. Each `lv_obj_t` may have `lv_obj->user_data` pointing at an `mp_lv_obj_t` wrapper.
2. The wrapper holds `.lv_obj` and an optional `.callbacks` dict.
3. On `LV_EVENT_DELETE`, `mp_lv_delete_cb` clears `self->lv_obj` but does not free the wrapper.

**Reachability:** The GC traces Python references, not LVGL's C object graph. A widget wrapper is
reachable only if:

- Python code holds a reference to the widget object, or
- Another traced Python object references it.

If Python drops all references while LVGL still owns the `lv_obj_t`, the wrapper may become
unreachable and be collected even though LVGL still has a stale `user_data` pointer.

**Mitigation today:** Keep Python references to widgets for as long as LVGL uses them (same as
upstream lv_micropython behavior).

**Future option:** Register active `mp_lv_obj_t` instances in a root list, or clear
`lv_obj->user_data` when the wrapper is finalized.

---

## Callback dicts

Callbacks are stored in a dict, keyed by callback qstr (`mp_lv_callback` / `get_callback_dict_from_user_data`):

| Container | Dict location | GC traces dict? |
|-----------|---------------|-----------------|
| `lv_obj_t` widget | `mp_lv_obj_t.callbacks` | Only if wrapper is traced |
| Struct with `user_data` field | `void*` → `mp_obj_dict` | Only if struct is reachable from Python |
| Global LVGL callback | `MP_STATE_PORT(mp_lv_user_data)` | Root pointer holds the **pointer value**, not the dict object |

### Setting callbacks (`mp_lv_callback`)

When a callable is passed:

```c
mp_obj_dict_store(callbacks, MP_OBJ_NEW_QSTR(callback_name), mp_callback);
```

The dict holds strong references to callables. The dict itself must stay alive for the callback
to fire.

### Invoking callbacks (`gen_callback_func`, phase 7)

Trampolines call:

```c
mp_obj_t callbacks = get_callback_dict_from_user_data(user_data);
mp_call_function_n_kw(mp_obj_dict_get(callbacks, MP_OBJ_NEW_QSTR(...)), ...);
```

If `callbacks` was collected, this is a use-after-free risk.

### Global callbacks

`is_global_callback()` (`binding/helpers.py`) matches typedefs like `lv_*_cb_t` on the global
LVGL state. User data resolves to `MP_STATE_PORT(mp_lv_user_data)`.

When registering, code may store a dict at that address. `mp_lv_user_data` is a registered root
pointer, but it stores a `void*` — the GC roots the **slot**, not the `mp_obj_dict` it points to
unless that dict is also reachable from traced Python objects.

**Action item (CP + MP):** When assigning a callback dict to `mp_lv_user_data` or struct
`user_data`, either:

1. Document that the application must keep a Python reference to the dict/widget, or
2. Emit `MP_REGISTER_ROOT_POINTER` for a dedicated `mp_lv_callback_roots` list, or
3. Use `gc_collect_start` / allocation APIs that pin objects (heavier).

---

## Struct `user_data` fields

Struct fields typed as callbacks get trampolines in phase 7 (`callbacks_used_on_structs`).
Non-object structs may store `user_data` as a raw `void*` to a dict (`MP_OBJ_TO_PTR(mp_obj_new_dict(0))`).

Same rule as widgets: **the dict is not rooted unless Python holds a reference.**

---

## CircuitPython-specific notes

- **Spike module** (`circuitpython_spike/shared-bindings/lvgl/__init.c`) only registers
  `init` / `deinit`; generated symbols live in `lvcp.c` and are merged via `LVCP_MODULE_GLOBALS`.
- **Allocator** (`lv_mem_core_circuitpython.c`): LVGL heap allocations use `gc_alloc` / `m_malloc`;
  LVGL-internal pointers are not Python objects.
- **Display bridge:** **ON HOLD** — flush/tick callbacks will be Python-registered separately;
  same callback lifetime rules apply when implemented.

---

## Recommended usage (until generator roots callbacks)

1. Keep a Python reference to every widget that has event handlers.
2. For struct callbacks, keep a reference to the struct wrapper (or the dict passed as `user_data`).
3. Call `lvgl.deinit()` before dropping all LVGL references when shutting down.
4. After first CP on-device test, add a stress test: create widget, register callback, `del` widget
   ref, force `gc.collect()`, invoke LVGL timer — verify whether callback still works.

---

## Open generator work (not scheduled)

| Item | Priority |
|------|----------|
| Root callback dicts when stored only in LVGL `user_data` | High after first CP build |
| Clear `lv_obj->user_data` on wrapper finalization | Medium |
| CP-specific `mp_arg_validate` in hand-written spike | Low |
| Display bridge GC policy | **On hold** (user request) |

See also `circuitpython_emit_plan.md` § Open questions.
