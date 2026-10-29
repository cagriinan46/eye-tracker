"""Local socket framing. No disk images or network listeners."""

import json
import select
import struct
import time


def read_exact(sock, size, cancelled=None, deadline=None):
    chunks = bytearray()
    while len(chunks) < size:
        if cancelled is not None and cancelled():
            raise InterruptedError("Worker operation cancelled")
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("Worker response timed out")
        if cancelled is not None or deadline is not None:
            if not select.select([sock], [], [], 0.1)[0]:
                continue
        part = sock.recv(size - len(chunks))
        if not part:
            raise EOFError("Worker connection closed")
        chunks.extend(part)
    return bytes(chunks)


def send(sock, metadata, payload=b""):
    header = json.dumps(metadata, allow_nan=False).encode()
    sock.sendall(struct.pack("!II", len(header), len(payload)) + header + payload)


def receive(sock, cancelled=None, timeout=None):
    deadline = None if timeout is None else time.monotonic() + timeout

    def read(size):
        return read_exact(sock, size, cancelled, deadline)

    n, p = struct.unpack("!II", read(8))
    if n > 1_000_000 or p > 2 * 640 * 480 * 3:
        raise ValueError("Oversized local packet")
    return json.loads(read(n)), read(p)
