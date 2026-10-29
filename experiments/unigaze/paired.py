"""Same-frame local worker + UniGaze, no camera or file-based image transfer."""

import hashlib
import os
import socket
import subprocess
import time

from .adapter import Candidate
from .settings import BASELINE_PYTHON, ROOT
from .wire import receive, send


class PairedExtractor:
    def __init__(self):
        self.sock = None
        self.worker = None
        self.last_id = -1
        self.last_timestamp = -1
        try:
            self.candidate = Candidate()
            self.provenance = self.candidate.provenance
            self.sock, child = socket.socketpair()
            self.sock.settimeout(30)
            try:
                self.worker = subprocess.Popen(
                    [
                        str(BASELINE_PYTHON),
                        "-m",
                        "experiments.unigaze.vision_worker",
                        str(child.fileno()),
                    ],
                    pass_fds=(child.fileno(),),
                    env=dict(
                        os.environ,
                        PYTHONDONTWRITEBYTECODE="1",
                        PYTHONPATH=str(ROOT / "src") + os.pathsep + str(ROOT),
                    ),
                    cwd=ROOT,
                    stdout=subprocess.DEVNULL,
                )
            finally:
                child.close()
            ready, _ = receive(self.sock)
            if ready.get("status") != "ready":
                raise RuntimeError(str(ready))
            self.provenance["baseline"] = ready["baseline"]
        except BaseException:
            self.close()
            raise

    def process(self, frame, frame_id, timestamp_ns):
        if self.sock is None:
            raise RuntimeError("Extractor closed")
        if frame_id <= self.last_id or timestamp_ns <= self.last_timestamp:
            raise ValueError("Non-increasing frame identity")
        start = time.perf_counter()
        raw = frame.copy()
        corrected = self.candidate.prepare(raw)
        payload = raw.tobytes()
        corrected_digest = hashlib.sha256(corrected.tobytes()).hexdigest()
        digest = hashlib.sha256(payload).hexdigest()
        # Same capture: MGaze original raw; candidate/landmarks measured-undistorted.
        send(
            self.sock,
            dict(command="frame", frame_id=frame_id, timestamp_ns=timestamp_ns),
            payload + corrected.tobytes(),
        )
        result, _ = receive(self.sock)
        expected = dict(
            status="ok",
            frame_id=frame_id,
            timestamp_ns=timestamp_ns,
            raw_sha256=digest,
            corrected_sha256=corrected_digest,
        )
        if any(result.get(k) != v for k, v in expected.items()):
            raise ValueError(f"Worker identity/error: {result.get('error')}")
        self.last_id = frame_id
        self.last_timestamp = timestamp_ns
        landmarks = result.pop("landmarks")
        t = time.perf_counter()
        result.update(
            self.candidate.infer(corrected, landmarks, result["diagnostics"]["mgaze_face_rect"])
        )
        result["unigaze_ms"] = (time.perf_counter() - t) * 1000
        result["candidate_raw_sha256"] = digest
        result["candidate_corrected_sha256"] = corrected_digest
        result["paired_total_ms"] = (time.perf_counter() - start) * 1000
        result["joint_valid"] = result["mgaze_valid"] and result["unigaze_valid"]
        return result

    def close(self):
        if self.sock is not None:
            try:
                send(self.sock, {"command": "close"})
            except OSError:
                pass
            self.sock.close()
            self.sock = None
        if self.worker is not None:
            try:
                self.worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.worker.terminate()
                try:
                    self.worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.worker.kill()
                    self.worker.wait()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
