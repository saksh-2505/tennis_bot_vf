import pytest

from observability.metrics import get_metrics, MetricsStore


class TestMetrics:
    def setup_method(self):
        get_metrics().reset()

    def test_counter(self):
        store = get_metrics()
        c = store.counter("test_counter")
        assert c.get() == 0.0
        c.inc()
        assert c.get() == 1.0
        c.inc(5)
        assert c.get() == 6.0

    def test_gauge(self):
        store = get_metrics()
        g = store.gauge("test_gauge")
        g.set(42.0)
        assert g.get() == 42.0

    def test_histogram(self):
        store = get_metrics()
        h = store.histogram("test_hist")
        for v in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
            h.observe(float(v))
        snap = h.snapshot()
        assert snap["count"] == 10
        assert snap["min"] == 1.0
        assert snap["max"] == 10.0
        assert snap["avg"] == 5.5

    def test_snapshot(self):
        store = get_metrics()
        store.counter("c1").inc(3)
        store.gauge("g1").set(10)
        store.histogram("h1").observe(5.0)
        snap = store.snapshot()
        assert snap["counters"]["c1"] == 3.0
        assert snap["gauges"]["g1"] == 10.0
        assert snap["histograms"]["h1"]["count"] == 1

    def test_record(self):
        store = get_metrics()
        store.record("test_point", 1.0, {"label": "val"})
        snap = store.snapshot()
        assert "test_point" not in snap["counters"]

    def test_singleton(self):
        s1 = MetricsStore()
        s2 = MetricsStore()
        assert s1 is s2

    def test_reset(self):
        store = get_metrics()
        store.counter("c").inc(10)
        store.reset()
        assert store.counter("c").get() == 0.0
