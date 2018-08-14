from BeamlineStatusLogger.transformers import adder


def test_adder():
    assert adder(1) == 2
