"""Run with PYTHONPATH=src:. python -m experiments.desktop_demo."""

import argparse
import sys
from pathlib import Path

from .runtime import DesktopAPI


def html():
    ui = Path(__file__).parent / "ui"
    return (
        (ui / "index.html")
        .read_text()
        .replace("/*STYLE*/", (ui / "style.css").read_text())
        .replace("/*SCRIPT*/", (ui / "app.js").read_text())
    )


def pause_for_window_move(api, *args):
    api.command("pause")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--model", choices=("unigaze", "mgaze"), default="unigaze")
    parser.add_argument(
        "--perf-diagnostics",
        action="store_true",
        help="print and save timing aggregates (first 3 s / next 15 s of each phase); "
        "no images or gaze points are saved",
    )
    args = parser.parse_args()
    import webview

    api = DesktopAPI(
        output=args.output,
        camera_index=args.camera_index,
        model_name=args.model,
        perf_diagnostics=args.perf_diagnostics,
    )
    window = webview.create_window(
        "Eye Tracker",
        html=html(),
        js_api=api,
        width=1280,
        maximized=sys.platform == "darwin",
        height=800,
        min_size=(960, 640),
        resizable=True,
        background_color="#100e17",
        zoomable=False,
        text_select=False,
    )
    pointer = keyboard = None
    if sys.platform == "darwin":
        from eye_tracker.platform_adapters.macos_window_pointer import MacOSWindowPointer

        from .macos_keyboard import FocusKeyboard

        keyboard = FocusKeyboard()
        window.events.closed += keyboard.close
        pointer = MacOSWindowPointer(window, api.pointer_sample, api.request_pointer_pause)
        window.events.closed += pointer.close

        from .macos_desktop_dwell import AX, DesktopDwell

        desktop = DesktopDwell(window, api, keyboard)
        api._desktop_supported = True
        api._desktop_permission = AX.AXIsProcessTrusted
        window.events.closed += desktop.close
    window.events.closing += api.close
    window.events.moved += lambda *args: pause_for_window_move(api, *args)
    window.events.resized += lambda *args: pause_for_window_move(api, *args)

    def start_native():
        if pointer:
            pointer.start()
            keyboard.start()
            desktop.start()

    try:
        webview.start(
            start_native if pointer else None,
            gui="edgechromium" if sys.platform == "win32" else None,
            debug=False,
        )
    finally:
        api.close()


if __name__ == "__main__":
    main()
