from BeamlineStatusLogger.processors import adder


def test_adder():
    assert adder(1) == 2
