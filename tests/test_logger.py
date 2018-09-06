from BeamlineStatusLogger.logger import Logger
from time import sleep
from threading import Thread
import pytest


class MockSource:
    def __init__(self, ret):
        self.ret = ret

    def read(self):
        return self.ret


class MockSink:
    def __init__(self):
        self.arg = None

    def write(self, arg):
        self.arg = arg
        return True


class MockProcessor:
    def __init__(self, ret):
        self.ret = ret
        self.arg = None

    def __call__(self, arg):
        self.arg = arg
        return self.ret


class MockTimer:
    def __init__(self, max_call=None):
        self.arg = None
        self.aborted = False
        self.max_call = max_call
        self.call_count = 0

    def __call__(self, arg):
        self.arg = arg
        self.call_count += 1
        if self.max_call and self.call_count >= self.max_call:
            return False
        else:
            return not self.aborted

    def abort(self):
        self.aborted = True

    def reset(self):
        self.aborted = False
        self.call_count = 0
        self.arg = None


@pytest.fixture
def mockSource():
    return MockSource(0)


@pytest.fixture
def mockSink():
    return MockSink()


@pytest.fixture
def mockTimer():
    return MockTimer()


def adder(n):
    return lambda x: x + n


class TestLogger:
    def test_init_no_proc(self, mockSource, mockSink, mockTimer):
        procs = []
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        assert logger.source is mockSource
        assert logger.processors is procs
        assert logger.sink is mockSink
        assert logger.timer is mockTimer

    def test_init_one_proc(self, mockSource, mockSink, mockTimer):
        procs = MockProcessor(1)
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        assert logger.processors == [procs]

    def test_init_proc_list(self, mockSource, mockSink, mockTimer):
        procs = [MockProcessor(1), MockProcessor(2)]
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        assert logger.processors is procs

    def test_run_finite(self, mockSource, mockSink, mockTimer):
        proc1 = MockProcessor(1)
        proc2 = MockProcessor(2)
        procs = [proc1, proc2]
        mockTimer.max_call = 10
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        logger.run()
        assert proc1.arg == 0
        assert proc2.arg == 1
        assert mockSink.arg == 2
        assert not mockTimer.aborted
        assert mockTimer.arg
        assert mockTimer.call_count == 10

    def test_run_abort(self, mockSource, mockSink, mockTimer):
        proc1 = MockProcessor(1)
        proc2 = MockProcessor(2)
        procs = [proc1, proc2]
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        t = Thread(target=logger.run)
        t.start()
        # wait until logger run at least once
        while not mockSink.arg:
            sleep(0.1)
        logger.abort()
        # wait until logger finished aborting
        t.join()
        assert proc1.arg == 0
        assert proc2.arg == 1
        assert mockSink.arg == 2
        assert mockTimer.aborted
        assert mockTimer.arg

    def test_run_restart(self, mockSource, mockSink, mockTimer):
        proc1 = MockProcessor(1)
        proc2 = MockProcessor(2)
        procs = [proc1, proc2]
        logger = Logger(mockSource, procs, mockSink, mockTimer)
        t = Thread(target=logger.run)
        t.start()
        # wait until logger run at least once
        while not mockSink.arg:
            sleep(0.1)
        logger.abort()
        # wait until logger finished aborting
        t.join()
        assert mockTimer.aborted

        t = Thread(target=logger.run)
        t.start()
        # wait until logger run at least once
        while not mockSink.arg:
            sleep(0.1)

        assert proc1.arg == 0
        assert proc2.arg == 1
        assert mockSink.arg == 2
        assert not mockTimer.aborted
        assert mockTimer.arg
        logger.abort()
        # wait until logger finished aborting
        t.join()
