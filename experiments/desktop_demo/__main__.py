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
    args = parser.parse_args()
    import webview

    api = DesktopAPI(output=args.output, camera_index=args.camera_index, model_name=args.model)
    window = webview.create_window(
        "Eye Tracker",
        html=html(),
        js_api=api,
        width=1280,
        height=800,
        min_size=(960, 640),
        resizable=True,
        background_color="#100e17",
        zoomable=False,
        text_select=False,
    )
    pointer = None
    if sys.platform == "darwin":
        from eye_tracker.platform_adapters.macos_window_pointer import MacOSWindowPointer

        pointer = MacOSWindowPointer(window, api.pointer_sample, api.request_pointer_pause)
        window.events.closed += pointer.close
    window.events.closing += api.close
    window.events.moved += lambda *args: pause_for_window_move(api, *args)
    window.events.resized += lambda *args: pause_for_window_move(api, *args)
    try:
        webview.start(
            pointer.start if pointer else None,
            gui="edgechromium" if sys.platform == "win32" else None,
            debug=False,
        )
    finally:
        api.close()


if __name__ == "__main__":
    main()
