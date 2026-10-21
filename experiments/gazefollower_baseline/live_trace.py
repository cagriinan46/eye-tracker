"""Bounded local diagnostic trace; never reads historical participant records."""

import json
import sys
import time


class LiveTrace:
    """Append complete JSON lines, with periodic flush and no in-memory history."""

    def __init__(
        self,
        folder,
        model_info,
        *,
        max_bytes=32 * 1024 * 1024,
        flush_seconds=1.0,
        clock=time.monotonic,
    ):
        self.folder = folder
        self.clock = clock
        self.last_flush = clock()
        self.max_bytes = max_bytes
        self.flush_seconds = flush_seconds
        self.rows = self.bytes = self.skipped_rows = 0
        self.status = "closed"
        with (folder / "live-trace.json").open("x", encoding="utf-8") as stream:
            json.dump(
                dict(
                    schema_version=1,
                    model=model_info,
                    max_bytes=max_bytes,
                    flush_seconds=flush_seconds,
                    started_monotonic_s=self.last_flush,
                    coordinates="drawable pixels; command_px is a returned backend move call, "
                    "not an observed OS cursor position",
                    accuracy_measurement=False,
                ),
                stream,
                allow_nan=False,
                indent=2,
            )
        self.stream = (folder / "live.jsonl").open("xb")

    def __enter__(self):
        return self

    def record(self, row):
        if self.status == "size_limit":
            self.skipped_rows += 1
            return
        try:
            encoded = (json.dumps(row, allow_nan=False, separators=(",", ":")) + "\n").encode()
            if self.bytes + len(encoded) > self.max_bytes:
                self.stream.flush()
                self.status = "size_limit"
                self.skipped_rows += 1
                print(
                    "Live trace size limit reached; logging stopped, live control continues.",
                    file=sys.stderr,
                    flush=True,
                )
                return
            self.stream.write(encoded)
            self.bytes += len(encoded)
            self.rows += 1
            now = self.clock()
            if now - self.last_flush >= self.flush_seconds:
                self.stream.flush()
                self.last_flush = now
        except Exception:
            self.status = "failed"
            print("Live trace write/flush failed; stopping live mode.", file=sys.stderr, flush=True)
            raise

    def __exit__(self, exc_type, exc, tb):
        try:
            self.stream.close()
        except Exception as close_error:
            exc_type = type(close_error)
            self.status = "failed"
            print("Live trace close failed.", file=sys.stderr, flush=True)
            raise
        finally:
            with (self.folder / "live-trace-summary.json").open("x", encoding="utf-8") as stream:
                json.dump(
                    dict(
                        status=self.status,
                        rows=self.rows,
                        bytes=self.bytes,
                        skipped_rows=self.skipped_rows,
                        live_exit="escape"
                        if exc_type is InterruptedError
                        else ("error" if exc_type else "returned"),
                        error_type=exc_type.__name__ if exc_type else None,
                    ),
                    stream,
                    allow_nan=False,
                    indent=2,
                )
