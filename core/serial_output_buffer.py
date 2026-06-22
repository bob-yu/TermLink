import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional


DEFAULT_MAX_BYTES_PER_PORT = 10 * 1024 * 1024


@dataclass(frozen=True)
class SerialOutputChunk:
    seq: int
    timestamp: float
    data: str


class SerialOutputBuffer:
    """Per-port ring buffer with bounded wait semantics for automation reads."""

    def __init__(self, max_bytes_per_port: int = DEFAULT_MAX_BYTES_PER_PORT):
        self._max_bytes_per_port = max(1, int(max_bytes_per_port))
        self._buffers: Dict[str, Deque[SerialOutputChunk]] = {}
        self._buffer_sizes: Dict[str, int] = {}
        self._latest_seq: Dict[str, int] = {}
        self._dropped_bytes: Dict[str, int] = {}
        self._dropped_chunks: Dict[str, int] = {}
        self._last_drop_time: Dict[str, float] = {}
        self._condition = threading.Condition()

    def append(self, port: str, data: str) -> int:
        if not port or not data:
            return self.latest_seq(port)
        now = time.monotonic()
        with self._condition:
            seq = self._latest_seq.get(port, 0) + 1
            self._latest_seq[port] = seq
            buffer = self._buffers.setdefault(port, deque())
            chunk = SerialOutputChunk(seq=seq, timestamp=now, data=data)
            buffer.append(chunk)
            self._buffer_sizes[port] = self._buffer_sizes.get(port, 0) + len(data.encode("utf-8", errors="replace"))
            self._trim_locked(port)
            self._condition.notify_all()
            return seq

    def latest_seq(self, port: str) -> int:
        with self._condition:
            return self._latest_seq.get(port, 0)

    def watch(
        self,
        port: str,
        start_seq: Optional[int] = None,
        from_position: str = "latest",
        duration: float = 2.0,
        expect: Optional[str] = None,
        idle_timeout: Optional[float] = None,
        regex: bool = False,
    ) -> dict:
        started_at = time.monotonic()
        deadline = started_at + max(0.0, float(duration))
        collected: List[str] = []
        matched = False
        lost = False
        reason = "duration"
        pattern = re.compile(expect) if expect and regex else None

        with self._condition:
            start_seq = self._resolve_start_seq_locked(port, start_seq, from_position)

            last_data_at = None
            cursor = int(start_seq)

            while True:
                chunks, cursor, was_lost = self._read_available_locked(port, cursor)
                if was_lost:
                    lost = True
                if chunks:
                    collected.extend(chunk.data for chunk in chunks)
                    last_data_at = time.monotonic()
                    text = "".join(collected)
                    if expect:
                        matched = bool(pattern.search(text) if pattern else expect in text)
                        if matched:
                            reason = "expect"
                            break

                now = time.monotonic()
                if last_data_at is not None and idle_timeout is not None:
                    idle_remaining = float(idle_timeout) - (now - last_data_at)
                    if idle_remaining <= 0:
                        reason = "idle_timeout"
                        break
                else:
                    idle_remaining = None

                duration_remaining = deadline - now
                if duration_remaining <= 0:
                    reason = "duration"
                    break

                wait_time = duration_remaining
                if idle_remaining is not None:
                    wait_time = min(wait_time, max(0.0, idle_remaining))
                self._condition.wait(timeout=max(0.01, wait_time))

        elapsed = time.monotonic() - started_at
        latest_seq = self.latest_seq(port)
        oldest_seq = self.oldest_seq(port)
        return {
            "output": "".join(collected),
            "matched": matched,
            "reason": reason,
            "duration": elapsed,
            "start_seq": start_seq,
            "end_seq": cursor,
            "oldest_seq": oldest_seq,
            "latest_seq": latest_seq,
            "lost": lost,
        }

    def state(self, port: str) -> dict:
        with self._condition:
            return {
                "port": port,
                "current_bytes": self._buffer_sizes.get(port, 0),
                "max_bytes": self._max_bytes_per_port,
                "oldest_seq": self._oldest_seq_locked(port),
                "latest_seq": self._latest_seq.get(port, 0),
                "dropped_bytes": self._dropped_bytes.get(port, 0),
                "dropped_chunks": self._dropped_chunks.get(port, 0),
                "last_drop_time": self._last_drop_time.get(port, 0),
            }

    def clear(self):
        with self._condition:
            self._buffers.clear()
            self._buffer_sizes.clear()
            self._latest_seq.clear()
            self._dropped_bytes.clear()
            self._dropped_chunks.clear()
            self._last_drop_time.clear()
            self._condition.notify_all()

    def oldest_seq(self, port: str) -> int:
        with self._condition:
            return self._oldest_seq_locked(port)

    def _oldest_seq_locked(self, port: str) -> int:
        buffer = self._buffers.get(port)
        if not buffer:
            return self._latest_seq.get(port, 0)
        return buffer[0].seq

    def _resolve_start_seq_locked(self, port: str, start_seq: Optional[int], from_position: str) -> int:
        mode = (from_position or "latest").lower()
        if mode == "latest":
            return self._latest_seq.get(port, 0) if start_seq is None else int(start_seq)
        if mode == "oldest":
            return max(0, self._oldest_seq_locked(port) - 1)
        if mode == "seq":
            return int(start_seq) if start_seq is not None else self._latest_seq.get(port, 0)
        return self._latest_seq.get(port, 0) if start_seq is None else int(start_seq)

    def _read_available_locked(self, port: str, start_seq: int):
        buffer = self._buffers.get(port)
        if not buffer:
            return [], start_seq, False

        oldest = buffer[0].seq
        lost = start_seq < oldest - 1
        effective_start = max(start_seq, oldest - 1)
        chunks = [chunk for chunk in buffer if chunk.seq > effective_start]
        cursor = chunks[-1].seq if chunks else effective_start
        return chunks, cursor, lost

    def _trim_locked(self, port: str):
        buffer = self._buffers.get(port)
        if not buffer:
            self._buffer_sizes[port] = 0
            return

        size = self._buffer_sizes.get(port, 0)
        while len(buffer) > 1 and size > self._max_bytes_per_port:
            removed = buffer.popleft()
            removed_bytes = len(removed.data.encode("utf-8", errors="replace"))
            size -= removed_bytes
            self._dropped_bytes[port] = self._dropped_bytes.get(port, 0) + removed_bytes
            self._dropped_chunks[port] = self._dropped_chunks.get(port, 0) + 1
            self._last_drop_time[port] = time.monotonic()
        self._buffer_sizes[port] = max(0, size)
