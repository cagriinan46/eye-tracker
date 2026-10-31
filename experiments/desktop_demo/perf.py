"""Opt-in timing summaries for the desktop demo (issue #145).

Measurement only: no camera frames, eye crops, gaze points or per-frame logs are
written. Each calibration/check/demo segment is summarized as two windows, the
first 3 s and the following 15 s, into one small JSON file plus console lines.
"""

import json
import math
import os
import platform
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import uuid4

VERSION = 1
WINDOWS = (("first_3s", 0.0, 3.0), ("next_15s", 3.0, 18.0))
PHASES = ("calibration", "check", "demo")
MAX_SEGMENTS = 40
MS_KEYS = (
    "age_ms",
    "interval_ms",
    "request_ms",
    "transport_ms",
    "reset_ms",
    "lock_wait_ms",
    "gui_ms",
    "wait_ms",
    "start_age_ms",
    "worker_ms",
    "paired_ms",
    "prepare_ms",
    "vision_ms",
    "mgaze_ms",
    "landmarks_ms",
    "vision_diag_ms",
    "vision_overhead_ms",
    "unigaze_ms",
    "ug_detect_ms",
    "ug_normalize_ms",
    "ug_model_ms",
    "post_ms",
)


def distribution(values):
    v = sorted(float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(x))
    if not v:
        return None

    def rank(p):
        return v[min(len(v) - 1, max(0, math.ceil(p * len(v)) - 1))]

    return dict(
        n=len(v),
        mean=round(sum(v) / len(v), 1),
        median=round(rank(0.5), 1),
        p90=round(rank(0.9), 1),
        max=round(v[-1], 1),
    )


def process_cpu_seconds():
    t = os.times()
    return t.user + t.system


class PerfRecorder:
    """Thread-safe; every public method costs a lock and a list append or less."""

    def __init__(self, output_dir, model_name, clock=time.monotonic, cpu=process_cpu_seconds):
        self._mutex = threading.Lock()
        self._clock, self._cpu = clock, cpu
        stamp = datetime.now().astimezone()
        self.path = (
            Path(output_dir)
            / f"desktop-perf-{stamp.strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:6]}.json"
        )
        self.header = dict(
            kind="desktop-perf-diagnostics",
            version=VERSION,
            created=stamp.isoformat(timespec="seconds"),
            model_name=model_name,
            platform=platform.platform(),
            machine=platform.machine(),
            cpu_count=os.cpu_count(),
            python=platform.python_version(),
            freshness_limit_ms=300,
            windows={name: [start, end] for name, start, end in WINDOWS},
            privacy="aggregate timings and counts only; no images, video or gaze points",
        )
        self.windows = []
        self._segment = None
        self._segments = 0
        self._phase = None
        self._last_fresh = None
        self._announced = False

    def set_model(self, metadata, camera_index=None):
        provenance = (metadata or {}).get("provenance") or {}
        with self._mutex:
            self.header.update(
                camera_index=(metadata or {}).get("camera_index", camera_index),
                model=(metadata or {}).get("model"),
                device=provenance.get("device"),
                torch_threads=provenance.get("threads"),
            )

    def phase(self, phase, now=None):
        now = self._clock() if now is None else now
        with self._mutex:
            if phase == self._phase:
                return
            self._phase = phase
            self._finish_window(now, complete=False)
            self._segment = None
            if phase in PHASES and self._segments < MAX_SEGMENTS:
                self._segments += 1
                self._segment = dict(index=self._segments, phase=phase, start=now)
                self._open_window(0, now)

    def frame(self, now, **values):
        with self._mutex:
            self._advance(now)
            if self._segment is not None:
                values["t"] = now
                self._segment["window"]["frames"].append(values)

    def gui_done(self, ms):
        with self._mutex:
            if self._segment is not None and self._segment["window"]["frames"]:
                self._segment["window"]["frames"][-1]["gui_ms"] = ms

    def pointer(self, now, outcome, captured=None):
        """outcome: busy (lock contended), none (no point) or delivered."""
        with self._mutex:
            self._advance(now)
            fresh = outcome == "delivered" and captured != self._last_fresh
            if fresh:
                self._last_fresh = captured
            if self._segment is not None:
                counts = self._segment["window"]["pointer"]
                counts[outcome] += 1
                counts["fresh"] += fresh

    def close(self, now=None):
        now = self._clock() if now is None else now
        with self._mutex:
            self._finish_window(now, complete=False)
            self._segment = None
            self._phase = None
            if self.windows and not self._announced:
                self._announced = True
                print(f"[perf] summary file: {self.path}", file=sys.stderr, flush=True)

    def _open_window(self, number, now):
        self._segment.update(
            window_number=number,
            window=dict(
                opened=now,
                cpu=self._cpu(),
                frames=[],
                pointer=dict(busy=0, none=0, delivered=0, fresh=0),
            ),
        )

    def _advance(self, now):
        while self._segment is not None:
            name, _, end = WINDOWS[self._segment["window_number"]]
            boundary = self._segment["start"] + end
            if now < boundary:
                return
            self._finish_window(boundary, complete=True)
            if self._segment["window_number"] + 1 < len(WINDOWS):
                self._open_window(self._segment["window_number"] + 1, boundary)
            else:
                self._segment = None

    def _finish_window(self, now, complete):
        seg = self._segment
        if seg is None:
            return
        w = seg["window"]
        name, start, _ = WINDOWS[seg["window_number"]]
        duration = max(now - w["opened"], 1e-6)
        summary = summarize(
            w["frames"], w["pointer"], duration, cpu_gui=self._cpu() - w["cpu"]
        ) | dict(
            segment=seg["index"],
            phase=seg["phase"],
            window=name,
            start_s=start,
            end_s=round(start + duration, 3),
            complete=complete,
        )
        self.windows.append(summary)
        print(console_line(summary), file=sys.stderr, flush=True)
        self._write()

    def _write(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix(".tmp")
            temp.write_text(
                json.dumps(dict(self.header, summaries=self.windows), indent=1, allow_nan=False)
                + "\n"
            )
            temp.replace(self.path)
        except OSError as error:
            print(f"[perf] could not write {self.path}: {error}", file=sys.stderr, flush=True)


def summarize(frames, pointer, duration, cpu_gui=None):
    n = len(frames)
    status = Counter(f.get("status") for f in frames)
    times = [f["t"] for f in frames]
    for f, previous in zip(frames[1:], times):
        f["interval_ms"] = (f["t"] - previous) * 1000
    with_seq = [f for f in frames if f.get("camera_sequence") is not None]
    camera_fps = None
    if len(with_seq) >= 2:
        span = with_seq[-1]["captured"] - with_seq[0]["captured"]
        if span > 0:
            camera_fps = round(
                (with_seq[-1]["camera_sequence"] - with_seq[0]["camera_sequence"]) / span, 2
            )

    def cpu_pct(key):
        values = [f[key] for f in frames if isinstance(f.get(key), (int, float))]
        return round(sum(values) / duration / 10, 1) if values else None

    rss = [f["worker_rss_mb"] for f in frames if isinstance(f.get("worker_rss_mb"), (int, float))]
    skipped = [f["skipped_frames"] for f in frames if isinstance(f.get("skipped_frames"), int)]
    return dict(
        duration_s=round(duration, 3),
        frames=n,
        processed_fps=round(n / duration, 2),
        status_counts=dict(status),
        on_time_pct=round(100 * status.get("tracking", 0) / n, 1) if n else None,
        eligibility_counts=dict(Counter(f.get("eligibility") for f in frames)),
        paused_frames=sum(bool(f.get("paused")) for f in frames),
        camera_fps=camera_fps,
        skipped_frames_mean=round(sum(skipped) / len(skipped), 2) if skipped else None,
        cursor=dict(
            polls_per_s=round(
                (pointer["busy"] + pointer["none"] + pointer["delivered"]) / duration, 2
            ),
            lock_busy_per_s=round(pointer["busy"] / duration, 2),
            point_per_s=round(pointer["delivered"] / duration, 2),
            fresh_estimate_per_s=round(pointer["fresh"] / duration, 2),
        ),
        cpu_pct=dict(
            gui=round(100 * cpu_gui / duration, 1) if cpu_gui is not None else None,
            worker=cpu_pct("worker_cpu_ms"),
            vision=cpu_pct("vision_cpu_ms"),
        ),
        worker_rss_mb_max=round(max(rss), 1) if rss else None,
        ms={k: d for k in MS_KEYS if (d := distribution(f.get(k) for f in frames))},
    )


def console_line(s):
    def m(key):
        d = s["ms"].get(key)
        return f"{d['median']:.0f}/{d['p90']:.0f}" if d else "-"

    cpu = s["cpu_pct"]
    return (
        f"[perf] #{s['segment']} {s['phase']} {s['window']} {s['duration_s']:.1f}s"
        f"{'' if s['complete'] else ' (partial)'}: frames {s['frames']} "
        f"({s['processed_fps']:.1f}/s) on-time {s['on_time_pct']}% camera {s['camera_fps']} fps "
        f"cursor-fresh {s['cursor']['fresh_estimate_per_s']}/s | med/p90 ms: age {m('age_ms')} "
        f"interval {m('interval_ms')} worker {m('worker_ms')} vision {m('vision_ms')} "
        f"unigaze {m('unigaze_ms')} (detect {m('ug_detect_ms')} model {m('ug_model_ms')}) "
        f"wait {m('wait_ms')} lock {m('lock_wait_ms')} | CPU% gui {cpu['gui']} "
        f"worker {cpu['worker']} vision {cpu['vision']}"
    )
