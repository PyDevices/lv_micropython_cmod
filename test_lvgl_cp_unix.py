#!/usr/bin/env python3
"""LVGL binding smoke tests for CircuitPython unix port.

Run:
  ./circuitpython/ports/unix/build-coverage/micropython ./lv_micropython_cmod/test_lvgl_cp_unix.py

Exercises init, minimal display, widgets, event callbacks, and GC visibility
(see binding/gc_callback_audit.md).
"""
import gc
import sys


def _fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _warn(msg):
    print(f"WARN: {msg}", file=sys.stderr)


def _setup_display(lvgl):
    """Minimal headless display so screen_active() and widgets behave like embedded."""

    def flush_cb(disp, area, color_p):
        disp.flush_ready()

    disp = lvgl.display_create(240, 240)
    disp.set_flush_cb(flush_cb)
    disp.set_color_format(lvgl.COLOR_FORMAT.RGB565)
    buf = lvgl.draw_buf_create(240, 240, lvgl.COLOR_FORMAT.RGB565, 0)
    disp.set_draw_buffers(buf, None)
    disp.set_render_mode(lvgl.DISPLAY_RENDER_MODE.PARTIAL)


def test_basic(lvgl):
    lvgl.init()
    if not lvgl.is_initialized():
        _fail("lvgl.init() did not initialize LVGL")
    assert hasattr(lvgl, "deinit")
    assert hasattr(lvgl, "label") or hasattr(lvgl, "obj")
    assert hasattr(lvgl, "EVENT") and hasattr(lvgl.EVENT, "CLICKED")
    print("OK: import lvgl; lvgl.init(); core symbols present")


def test_widget(lvgl):
    scr = lvgl.screen_active()
    label = lvgl.label(scr)
    label.set_text("cmods smoke")
    if label.get_text() != "cmods smoke":
        _fail(f"label text mismatch: {label.get_text()!r}")
    print("OK: label create/set_text on active screen")


def test_event_callback(lvgl):
    scr = lvgl.screen_active()
    fired = []

    def on_clicked(event):
        fired.append(event.get_code())

    scr.add_event_cb(on_clicked, lvgl.EVENT.CLICKED, None)
    scr.send_event(lvgl.EVENT.CLICKED, None)
    if not fired:
        _fail("screen CLICKED callback did not run")
    print("OK: add_event_cb + send_event")


def test_callback_gc_with_widget_ref(lvgl):
    scr = lvgl.screen_active()
    fired = []

    def handler(event):
        fired.append(1)

    scr.add_event_cb(handler, lvgl.EVENT.CLICKED, None)
    del handler
    gc.collect()
    scr.send_event(lvgl.EVENT.CLICKED, None)
    if fired:
        print("OK: callback survived gc.collect() while widget referenced")
    else:
        _warn(
            "callback was collected after del handler (widget still referenced); "
            "see binding/gc_callback_audit.md"
        )


def test_button_callback(lvgl):
    scr = lvgl.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == lvgl.EVENT.CLICKED:
            fired.append(1)

    btn = lvgl.button(scr)
    btn.set_size(80, 40)
    btn.add_event_cb(on_click, lvgl.EVENT.CLICKED, None)
    btn.send_event(lvgl.EVENT.CLICKED, None)
    if not fired:
        _fail("button CLICKED callback did not run")
    print("OK: button event callback")


def test_callback_gc_without_widget_ref(lvgl):
    scr = lvgl.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == lvgl.EVENT.CLICKED:
            fired.append(1)

    btn = lvgl.button(scr)
    btn.add_event_cb(on_click, lvgl.EVENT.CLICKED, None)
    del on_click
    btn_idx = scr.get_child_count() - 1
    del btn
    gc.collect()

    child = scr.get_child(btn_idx)
    child.send_event(lvgl.EVENT.CLICKED, None)
    if fired:
        print("OK: callback survived gc with no Python ref to widget (reached via get_child)")
    else:
        _warn(
            "callback lost after del widget + gc.collect(); "
            "LVGL user_data may not keep callbacks rooted — see binding/gc_callback_audit.md"
        )


def main():
    import lvgl

    if lvgl.is_initialized():
        lvgl.deinit()
    test_basic(lvgl)
    _setup_display(lvgl)
    test_widget(lvgl)
    test_event_callback(lvgl)
    test_callback_gc_with_widget_ref(lvgl)
    test_callback_gc_without_widget_ref(lvgl)
    test_button_callback(lvgl)
    lvgl.deinit()
    print("All smoke tests finished.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
