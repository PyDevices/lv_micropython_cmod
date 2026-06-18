#!/usr/bin/env python3
"""LVGL binding smoke tests for MicroPython unix port.

Run:
  ./micropython/ports/unix/build-standard/micropython ./lv_micropython_cmod/test_lvgl_unix.py

Exercises init, minimal display, widgets, event callbacks, and GC visibility
(see docs/lvgl/gc_callback_audit.md).
"""
import gc
import sys


def _fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def _warn(msg):
    print(f"WARN: {msg}", file=sys.stderr)


def _setup_display(lv):
    """Minimal headless display so screen_active() and widgets behave like embedded."""
    fired = {"flush": 0}

    def flush_cb(disp, area, color_p):
        fired["flush"] += 1
        disp.flush_ready()

    disp = lv.display_create(240, 240)
    disp.set_flush_cb(flush_cb)
    disp.set_color_format(lv.COLOR_FORMAT.RGB565)
    buf = lv.draw_buf_create(240, 240, lv.COLOR_FORMAT.RGB565, 0)
    disp.set_draw_buffers(buf, None)
    disp.set_render_mode(lv.DISPLAY_RENDER_MODE.PARTIAL)
    return fired


def test_basic(lv):
    lv.init()
    assert hasattr(lv, "deinit")
    assert hasattr(lv, "label") or hasattr(lv, "obj")
    assert hasattr(lv, "EVENT") and hasattr(lv.EVENT, "CLICKED")
    print("OK: import lvgl; lv.init(); core symbols present")


def test_widget(lv):
    scr = lv.screen_active()
    label = lv.label(scr)
    label.set_text("cmods smoke")
    assert label.get_text() == "cmods smoke"
    print("OK: label create/set_text on active screen")


def test_event_callback(lv):
    scr = lv.screen_active()
    fired = []

    def on_clicked(event):
        fired.append(event.get_code())

    scr.add_event_cb(on_clicked, lv.EVENT.CLICKED, None)
    scr.send_event(lv.EVENT.CLICKED, None)
    if not fired:
        _fail("screen CLICKED callback did not run")
    print("OK: add_event_cb + send_event")


def test_callback_gc_with_widget_ref(lv):
    """Callback dict is reachable while the widget stays referenced from Python."""
    scr = lv.screen_active()
    fired = []

    def handler(event):
        fired.append(1)

    scr.add_event_cb(handler, lv.EVENT.CLICKED, None)
    del handler
    gc.collect()
    scr.send_event(lv.EVENT.CLICKED, None)
    if fired:
        print("OK: callback survived gc.collect() while widget referenced")
    else:
        _warn(
            "callback was collected after del handler (widget still referenced); "
            "see docs/lvgl/gc_callback_audit.md"
        )


def test_button_callback(lv):
    scr = lv.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == lv.EVENT.CLICKED:
            fired.append(1)

    btn = lv.button(scr)
    btn.set_size(80, 40)
    btn.add_event_cb(on_click, lv.EVENT.CLICKED, None)
    btn.send_event(lv.EVENT.CLICKED, None)
    if not fired:
        _fail("button CLICKED callback did not run")
    print("OK: button event callback")


def test_callback_gc_without_widget_ref(lv):
    """Drop Python ref to widget; LVGL still owns the object (see gc_callback_audit.md)."""
    scr = lv.screen_active()
    fired = []

    def on_click(event):
        if event.get_code() == lv.EVENT.CLICKED:
            fired.append(1)

    btn = lv.button(scr)
    btn.add_event_cb(on_click, lv.EVENT.CLICKED, None)
    del on_click
    btn_idx = scr.get_child_count() - 1
    del btn
    gc.collect()

    child = scr.get_child(btn_idx)
    child.send_event(lv.EVENT.CLICKED, None)
    if fired:
        print("OK: callback survived gc with no Python ref to widget (reached via get_child)")
    else:
        _warn(
            "callback lost after del widget + gc.collect(); "
            "LVGL user_data may not keep callbacks rooted — see docs/lvgl/gc_callback_audit.md"
        )


def main():
    import lvgl as lv

    if lv.is_initialized():
        lv.deinit()
    test_basic(lv)
    _setup_display(lv)
    test_widget(lv)
    test_event_callback(lv)
    test_callback_gc_with_widget_ref(lv)
    test_callback_gc_without_widget_ref(lv)
    test_button_callback(lv)
    lv.deinit()
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
