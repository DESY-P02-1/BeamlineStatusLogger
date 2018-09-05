from BeamlineStatusLogger.timer import SynchronizedPeriodicTimer
from BeamlineStatusLogger.timer import PeriodicTimer
import BeamlineStatusLogger.timer as timer
import random
import pytest
from pytest import approx


class MockTime:
    def __init__(self, time=100):
        self.time = time

    def mocktime(self):
        return self.time


class MockEvent:
    def __init__(self):
        self.arg = None
        self._set = False

    def wait(self, t):
        self.arg = t

    def set(self):
        self._set = True

    def is_set(self):
        return self._set

    def clear(self):
        self.arg = None
        self._set = False


@pytest.fixture
def mockTime(monkeypatch):
    mt = MockTime()
    monkeypatch.setattr(timer, 'time', mt.mocktime)
    return mt


@pytest.fixture
def mockEvent(monkeypatch):
    me = MockEvent()
    monkeypatch.setattr(timer, 'Event', lambda: me)
    return me


class TestSynchronizedPeriodicTimer:
    def test_init(self):
        t = SynchronizedPeriodicTimer(5)
        assert t.period == 5
        assert t.p_min == t.period
        assert t.p_max >= t.period

    def test_timer(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5)
        for time, arg in [(100, 5), (100.1, 4.9), (104.9, 0.1), (105, 5)]:
            mockTime.time = time
            ret = t()
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_offset(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5, 0.1)
        for time, arg in [(100, 0.1), (100.1, 5), (104.9, 0.2), (105, 0.1)]:
            mockTime.time = time
            ret = t()
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_offset_negative(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5, -0.1)
        for time, arg in [(100, 4.9), (100.1, 4.8), (104.9, 5), (105, 4.9)]:
            mockTime.time = time
            ret = t(True)
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_occasional_failure(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5)
        for success, time, arg in [(True, 100, 5), (False, 100.1, 4.9),
                                   (False, 104.9, 0.1), (True, 105, 5),
                                   (False, 106, 4), (False, 112, 3),
                                   (False, 118, 2), (True, 124, 1)]:
            mockTime.time = time
            ret = t(success)
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_repeated_failure(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5)
        for success, time, arg in [(False, 100, 5), (False, 105, 5),
                                   (False, 110, 5), (False, 115, 5),
                                   (False, 120, 5), (False, 125, 5),
                                   (False, 130, 5), (True, 135, 5),
                                   (False, 140, 5), (True, 145, 5)]:
            mockTime.time = time
            ret = t(success)
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_repeated_failure_p_max(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5, p_max=50)
        for success, time, arg in [(False, 100, 5), (False, 105, 5),
                                   (False, 110, 5), (False, 115, 10),
                                   (False, 125, 20), (False, 145, 40),
                                   (False, 185, 40), (True, 225, 5),
                                   (False, 230, 5), (True, 235, 5)]:
            mockTime.time = time
            ret = t(success)
            assert ret
            assert mockEvent.arg == approx(arg)

    def test_timer_abort(self, mockTime, mockEvent):
        t = SynchronizedPeriodicTimer(5)
        ret = t()
        assert ret
        mockTime.time = 104
        t.abort()
        ret = t()
        assert not ret
        assert mockEvent.arg == 1

    @pytest.mark.parametrize('repeat', range(10))
    def test_timer_reset(self, mockTime, mockEvent, repeat):
        t = SynchronizedPeriodicTimer(5, p_max=2000)
        input_list = []
        response_list = []
        time = mockTime.time
        # create a random series of calls and save responses
        for i in range(30):
            success = random.randint(0, 1)
            time += random.randint(1, 6)
            input_list.append((success, time))
            mockTime.time = time
            ret = t(success)
            arg = mockEvent.arg
            response_list.append((ret, arg))

        if random.randint(0, 1):
            t.abort()

        t.reset()
        # replay the same series of call and check that all responses are
        # the same
        for (success, time), (ret, arg) in zip(input_list, response_list):
            mockTime.time = time
            assert t(success) == ret
            assert mockEvent.arg == arg


class TestPeriodicTimer:
    def test_init(self, mockTime):
        mt = mockTime
        mt.time = 103
        t = PeriodicTimer(5)
        assert t.period == 5
        assert t.offset == 3
        assert t.p_min == t.period
        assert t.p_max >= t.period
