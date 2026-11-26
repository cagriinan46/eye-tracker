"""Bounded Turkish microphone dictation with a local Whisper checkpoint."""

import hashlib
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

from experiments.unigaze.settings import PYTHON

ASSETS = Path(
    os.environ.get("EYE_TRACKER_DICTATION_DIR", Path.home() / ".eye-tracker" / "dictation")
)
WEIGHT_SHA = "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def microphone():
    listing = subprocess.run(
        [FFMPEG, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
        capture_output=True,
        text=True,
        timeout=6,
    ).stderr.partition("AVFoundation audio devices:")[2]
    match = re.search(r"\[(\d+)\]\s+.*MacBook", listing)
    if not match:
        raise RuntimeError("MacBook mikrofonu bulunamadı.")
    return match[1]


def transcribe_audio(audio):
    import numpy as np

    sys.path.insert(0, str(ASSETS / "speech-runtime"))
    import whisper

    audio = np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768
    if len(audio) < 8000 or np.abs(audio).max() < 0.008:
        raise RuntimeError("Yeterli konuşma sesi alınamadı.")
    model = whisper.load_model(str(ASSETS / "tiny.pt"), device="cpu")
    return model.transcribe(
        audio,
        language="tr",
        fp16=False,
        temperature=0,
        condition_on_previous_text=False,
    )["text"].strip()


class Dictation:
    def __init__(self, results):
        self.results = results
        self.stop = threading.Event()
        self.cancelled = threading.Event()
        self.process = None
        self.thread = None

    def start(self, target):
        if self.thread is not None and self.thread.is_alive():
            self.stop.set()
            return False
        self.stop.clear()
        self.cancelled.clear()
        self.thread = threading.Thread(target=self._run, args=(target,), daemon=True)
        self.thread.start()
        return True

    def _run(self, target):
        try:
            weights = ASSETS / "tiny.pt"
            if not weights.is_file():
                raise RuntimeError("Yerel Türkçe dikte modeli bulunamadı.")
            if hashlib.sha256(weights.read_bytes()).hexdigest() != WEIGHT_SHA:
                raise RuntimeError("Türkçe dikte modeli doğrulanamadı.")
            mic = microphone()
            self.process = subprocess.Popen(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "avfoundation",
                    "-i",
                    f":{mic}",
                    "-t",
                    "10",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-f",
                    "s16le",
                    "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )
            while True:
                try:
                    audio, error = self.process.communicate(timeout=0.15)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancelled.is_set() or self.stop.is_set():
                        self.process.send_signal(signal.SIGINT)
                        audio, error = self.process.communicate(timeout=3)
                        break
            if self.cancelled.is_set():
                return
            if not audio and error:
                raise RuntimeError("Mikrofon açılamadı. macOS mikrofon iznini kontrol et.")
            result = subprocess.run(
                [str(PYTHON), "-m", "experiments.desktop_demo.dictation"],
                input=audio,
                capture_output=True,
                timeout=45,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.decode(errors="replace").strip())
            text = result.stdout.decode().strip()
            if not self.cancelled.is_set():
                self.results.put((target, text, None))
        except Exception as error:
            if not self.cancelled.is_set():
                self.results.put((target, None, str(error)))
        finally:
            if self.process is not None and self.process.poll() is None:
                self.process.kill()
                self.process.communicate()
            self.process = None

    def close(self):
        self.cancelled.set()
        self.stop.set()


if __name__ == "__main__":
    try:
        print(transcribe_audio(sys.stdin.buffer.read()))
    except Exception as error:
        sys.exit(str(error))
