from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from observability.models import Counter, Gauge, Histogram, MetricPoint


class MetricsStore:
    _instance: MetricsStore | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> MetricsStore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._counters = {}
                    cls._instance._gauges = {}
                    cls._instance._histograms = {}
                    cls._instance._history: list[MetricPoint] = []
                    cls._instance._history_lock = threading.Lock()
                    cls._instance._max_history = 100000
        return cls._instance

    def counter(self, name: str) -> Counter:
        if name not in self._counters:
            self._counters[name] = Counter(name=name)
        return self._counters[name]

    def gauge(self, name: str) -> Gauge:
        if name not in self._gauges:
            self._gauges[name] = Gauge(name=name)
        return self._gauges[name]

    def histogram(self, name: str) -> Histogram:
        if name not in self._histograms:
            self._histograms[name] = Histogram(name=name)
        return self._histograms[name]

    def record(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        point = MetricPoint(name=name, value=value, timestamp=__import__("datetime").datetime.now(), labels=labels)
        with self._history_lock:
            self._history.append(point)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def snapshot(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "counters": {},
            "gauges": {},
            "histograms": {},
        }
        for name, c in self._counters.items():
            result["counters"][name] = c.get()
        for name, g in self._gauges.items():
            result["gauges"][name] = g.get()
        for name, h in self._histograms.items():
            result["histograms"][name] = h.snapshot()
        return result

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        with self._history_lock:
            self._history.clear()


def get_metrics() -> MetricsStore:
    return MetricsStore()
