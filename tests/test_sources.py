from BeamlineStatusLogger.sources import TangoDeviceAttributeSource
import PyTango as tango
import datetime
from pytz import timezone
import pytest


# TODO: Should the underlying DeviceProxy be mocked?
#       Or should the CI runner always create a fresh tango server
#       with "sys/tg_test/1"
class TestTangoDeviceAttributeSource:
    def test_init_success(self):
        device_name = "sys/tg_test/1"
        attribute_name = "float_scalar"
        s = TangoDeviceAttributeSource(device_name, attribute_name)
        assert s.device_name == device_name
        assert s.attribute_name == attribute_name
        assert s.metadata == {}

    def test_init_wrong_device(self):
        device_name = "sys/tg_test/2"
        attribute_name = "float_scalar"
        with pytest.raises(tango.DevFailed):
            TangoDeviceAttributeSource(device_name, attribute_name)

    def test_init_wrong_attribute(self):
        device_name = "sys/tg_test/1"
        attribute_name = "float_scala"
        with pytest.raises(tango.DevFailed):
            TangoDeviceAttributeSource(device_name, attribute_name)

    def test_init_metadata_contains_quality(self):
        device_name = "sys/tg_test/1"
        attribute_name = "float_scalar"
        with pytest.raises(ValueError):
            TangoDeviceAttributeSource(device_name, attribute_name,
                                       metadata={"quality": "bad"})

    def test_read_success(self):
        device_name = "sys/tg_test/1"
        attribute_name = "float_scalar"
        maxdelta = datetime.timedelta(seconds=5)
        s = TangoDeviceAttributeSource(device_name, attribute_name,
                                       metadata={"attribute": attribute_name})
        data = s.read()
        now = datetime.datetime.now()
        now = timezone("Europe/Berlin").localize(now)
        assert data.timestamp - now < maxdelta
        assert data.failure is None
        assert data.value[attribute_name] == 0
        assert data.metadata is not s.metadata
        assert data.metadata["attribute"] == attribute_name

    def test_read_failure(self, monkeypatch):
        device_name = "sys/tg_test/1"
        attribute_name = "float_scalar"
        maxdelta = datetime.timedelta(seconds=5)
        s = TangoDeviceAttributeSource(device_name, attribute_name,
                                       metadata={"attribute": attribute_name})
        ex = tango.DevFailed()

        # TODO: How to test handling of tango exceptions?
        def mockreturn(attribute_name):
            raise ex
        monkeypatch.setattr(s.device, 'read_attribute', mockreturn)

        data = s.read()
        now = datetime.datetime.now()
        now = timezone("Europe/Berlin").localize(now)
        assert data.timestamp - now < maxdelta
        assert data.failure is ex
        assert data.value is None
        assert data.metadata is not s.metadata
        assert data.metadata["attribute"] == attribute_name
