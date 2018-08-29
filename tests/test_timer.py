from BeamlineStatusLogger.timer import SynchronizedPeriodicTimer
from BeamlineStatusLogger.timer import PeriodicTimer
import BeamlineStatusLogger.timer as timer
import pytest
from pytest import approx


class MockTime:
    def __init__(self, time=100):
        self.time = time
        self.arg = None

    def mocktime(self):
        return self.time

    def mocksleep(self, t):
        self.arg = t


@pytest.fixture
def mockTime(monkeypatch):
    mt = MockTime()
    monkeypatch.setattr(timer, 'sleep', mt.mocksleep)
    monkeypatch.setattr(timer, 'time', mt.mocktime)
    return mt


class TestSynchronizedPeriodicTimer:
    def test_init(self):
        t = SynchronizedPeriodicTimer(5)
        assert t.period == 5
        assert t.p_min == t.period
        assert t.p_max >= t.period

    def test_timer(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5)
        for time, arg in [(100, 5), (100.1, 4.9), (104.9, 0.1), (105, 5)]:
            mt.time = time
            t(True)
            assert mt.arg == approx(arg)

    def test_timer_offset(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5, 0.1)
        for time, arg in [(100, 0.1), (100.1, 5), (104.9, 0.2), (105, 0.1)]:
            mt.time = time
            t(True)
            assert mt.arg == approx(arg)

    def test_timer_offset_negative(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5, -0.1)
        for time, arg in [(100, 4.9), (100.1, 4.8), (104.9, 5), (105, 4.9)]:
            mt.time = time
            t(True)
            assert mt.arg == approx(arg)

    def test_timer_occasional_failure(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5)
        for success, time, arg in [(True, 100, 5), (False, 100.1, 4.9),
                                   (False, 104.9, 0.1), (True, 105, 5),
                                   (False, 106, 4), (False, 112, 3),
                                   (False, 118, 2), (True, 124, 1)]:
            mt.time = time
            t(success)
            assert mt.arg == approx(arg)

    def test_timer_repeated_failure(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5)
        for success, time, arg in [(False, 100, 5), (False, 105, 5),
                                   (False, 110, 5), (False, 115, 5),
                                   (False, 120, 5), (False, 125, 5),
                                   (False, 130, 5), (True, 135, 5),
                                   (False, 140, 5), (True, 145, 5)]:
            mt.time = time
            t(success)
            assert mt.arg == approx(arg)

    def test_timer_repeated_failure_p_max(self, mockTime):
        mt = mockTime
        t = SynchronizedPeriodicTimer(5, p_max=50)
        for success, time, arg in [(False, 100, 5), (False, 105, 5),
                                   (False, 110, 5), (False, 115, 10),
                                   (False, 125, 20), (False, 145, 40),
                                   (False, 185, 40), (True, 225, 5),
                                   (False, 230, 5), (True, 235, 5)]:
            mt.time = time
            t(success)
            assert mt.arg == approx(arg)


class TestPeriodicTimer:
    def test_init(self, mockTime):
        mt = mockTime
        mt.time = 103
        t = PeriodicTimer(5)
        assert t.period == 5
        assert t.offset == 3
        assert t.p_min == t.period
        assert t.p_max >= t.period
