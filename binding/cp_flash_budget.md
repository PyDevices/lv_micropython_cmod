# CircuitPython build: allocator and flash budget

Short review before the first on-tree CP build (P4 Function EV board).

**Related:** `lv_mem_core_circuitpython.c`, `lv_mem_core_micropython.c`, `circuitpython.mk`, `binding/gc_callback_audit.md`.

---

## Flash budget (P4 Function EV)

| Board setting | Value |
|---------------|-------|
| `CIRCUITPY_ESP_FLASH_SIZE` | 16 MB |
| PSRAM | 32 MB (HPi) |

Firmware partition size on ESP32 CP boards is typically **~2–4 MB** for the factory app (varies by `sdkconfig` / partition table). LVGL integration adds:

| Component | Source size (approx.) | Notes |
|-----------|----------------------:|-------|
| LVGL `src/**/*.c` | **~10.3 MB** source | 285 translation units; most of flash cost |
| `generated/lvcp.c` | **~1.60 MB** source | ~39.5k lines; parity with `lvmp.c` |
| `generated/lvmp.c` | **~1.55 MB** source | reference |
| Spike module | ~2 KB | `shared-bindings/lvgl/`, `shared-module/lvgl/` |
| Allocator | ~2 KB | `lv_mem_core_circuitpython.c` |

**Reference binary:** MicroPython unix build with full LVGL + `lvmp.c` today is **~2.0 MB** (`build-standard/micropython`). Embedded CP image will differ (LTO, ESP32 toolchain, full CP core), but order of magnitude is **multi‑MB** — comfortable on 16 MB flash **if** the app partition is ≥ ~3 MB.

**Actions before merge to main CP board:**

1. After first CP build with full bindings, note `make` output size / `idf.py size`.
2. After full `lvcp.c` link, compare again; ensure partition headroom ≥ 512 KB for future growth.
3. If tight on smaller boards later, plan `CIRCUITPY_LVGL_FULL` trim driven by `lvcp.c.json` (see `circuitpython_emit_plan.md`).

---

## Allocator (CP vs MP)

Both routes use the same `lv_conf.h` switch:

```c
#if defined(CMODS_CIRCUITPYTHON_BUILD)
#define LV_USE_STDLIB_MALLOC LV_STDLIB_CIRCUITPYTHON_OVERRIDE  /* 253 */
#else
#define LV_USE_STDLIB_MALLOC LV_STDLIB_MICROPYTHON_OVERRIDE  /* 254 */
#endif
```

`circuitpython.mk` sets `-DCMODS_CIRCUITPYTHON_BUILD=1` and compiles `lv_mem_core_circuitpython.c`.

| API | MicroPython (`lv_mem_core_micropython.c`) | CircuitPython (draft) |
|-----|-------------------------------------------|------------------------|
| `lv_malloc_core` | `gc_alloc(size, **true**)` | `gc_alloc(size, **true**)` (aligned with MP) |
| `lv_realloc_core` | `gc_realloc(..., **true**)` | `gc_realloc(..., **true**)` |
| `lv_free_core` | `gc_free` | `gc_free` |
| pools | not supported | not supported |

Both ports use `gc_alloc(size, true)` for `lv_malloc_core` and `gc_realloc(..., true)` for `lv_realloc_core`. Validate during the first CP build if heap asserts appear.

Neither port implements `lv_mem_monitor_core` (no-op).

---

## Recommended first CP builds

1. Regenerate bindings: `./lv_micropython_cmod/regenerate_lvcp.sh`
2. Apply patches: `./lv_micropython_cmod/apply_cp_lvgl_patches.sh --apply`
3. Build: `./build_cp_unix.sh` (unix) or future `build_cp_esp32.sh` (embedded)
4. REPL: `import lvgl; lvgl.init()` then spot-check one widget API.

`circuitpython.mk` requires `generated/lvcp.c`; the build fails at make time if it is missing.

Display bridge remains **ON HOLD** — no flush/tick driver in these builds yet.

---

## Generator / regression (no CP tree needed)

```bash
./lv_micropython_cmod/verify_bindings.sh
./micropython/ports/unix/build-standard/micropython ./lv_micropython_cmod/test_lvgl_unix.py
```
