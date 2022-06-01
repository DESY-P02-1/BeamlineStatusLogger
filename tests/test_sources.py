from BeamlineStatusLogger import sources
from BeamlineStatusLogger.sources import (
    TangoDeviceAttributeSource, TINECameraSource)
import numpy as np
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
        source = TangoDeviceAttributeSource(device_name, attribute_name)
        data = source.read()
        assert data.failure

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
        now = datetime.datetime.now(timezone("Europe/Berlin"))
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
        now = datetime.datetime.now(timezone("Europe/Berlin"))
        assert data.timestamp - now < maxdelta
        assert data.failure is ex
        assert data.value is None
        assert data.metadata is not s.metadata
        assert data.metadata["attribute"] == attribute_name


@pytest.fixture
def tine_data():
    img = np.arange(15, dtype="u1").reshape(3, 5)
    frameHeader = dict(
        aoiHeight=-1,
        sourceHeight=3,
        aoiWidth=-1,
        sourceWidth=5,
        bytesPerPixel=1
    )
    bytes = img.tobytes()
    data = dict(
        frameHeader=frameHeader,
        imageBytes=bytes
    )
    reply = dict(
        status=0,
        data=data,
        timestamp=1571409806.054523
    )
    return img, reply


class TestTINECameraImage:
    def test_get_height(self):
        height = 1234
        frameHeader = dict(
            aoiHeight=-1,
            sourceHeight=height)
        assert sources.get_tine_image_height(frameHeader) == height

    def test_get_height_aoi(self):
        height = 1234
        frameHeader = dict(
            aoiHeight=height,
            sourceHeight=2*height)
        assert sources.get_tine_image_height(frameHeader) == height

    def test_get_height_invalid(self):
        height = -1
        frameHeader = dict(
            aoiHeight=height,
            sourceHeight=height)
        with pytest.raises(ValueError):
            sources.get_tine_image_height(frameHeader)

    def test_get_width(self):
        width = 1234
        frameHeader = dict(
            aoiWidth=-1,
            sourceWidth=width)
        assert sources.get_tine_image_width(frameHeader) == width

    def test_get_width_aoi(self):
        width = 1234
        frameHeader = dict(
            aoiWidth=width,
            sourceWidth=2*width)
        assert sources.get_tine_image_width(frameHeader) == width

    def test_get_width_invalid(self):
        width = -1
        frameHeader = dict(
            aoiWidth=width,
            sourceWidth=width)
        with pytest.raises(ValueError):
            sources.get_tine_image_width(frameHeader)

    @pytest.mark.parametrize(
        ("bytesPerPixel", "dtype"), [(1, "u1"), (2, "u2")])
    def test_get_dtype(self, bytesPerPixel, dtype):
        frameHeader = dict(bytesPerPixel=bytesPerPixel)
        assert sources.get_tine_image_dtype(frameHeader) == dtype

    def test_get_dtype_unknown(self):
        frameHeader = dict(bytesPerPixel=4)
        with pytest.raises(ValueError):
            sources.get_tine_image_dtype(frameHeader)

    def test_get_tine_image(self, tine_data):
        img, reply = tine_data
        data = reply["data"]
        np.testing.assert_array_equal(sources.tine_image_to_numpy(data), img)

    def test_get_tine_image_mismatch(self, tine_data):
        img, reply = tine_data
        data = reply["data"]
        data["frameHeader"]["sourceHeight"] = 4
        with pytest.raises(ValueError):
            sources.tine_image_to_numpy(data)


class TestTINECameraSource:
    dummy_address = "/CONTEXT/server/device"
    dummy_property = "frame"

    @pytest.fixture(autouse=True)
    def tine_mock(self, mocker, tine_data):
        img, reply = tine_data
        mock = mocker.patch.object(sources, "tine")

        def get(device_name, property_name):
            if (device_name != self.dummy_address
                    or property_name != self.dummy_property):
                raise RuntimeError("Unknown Device")
            return reply
        mock.get.side_effect = get

        def strerror(status):
            if status == 0:
                return "RMT: success"
            else:
                return "RMT: failure"
        mock.strerror.side_effect = strerror

        return mock

    def test_init_success(self):
        s = TINECameraSource(self.dummy_address, self.dummy_property)
        assert s.device_address == self.dummy_address
        assert s.property_name == self.dummy_property
        assert s.metadata == {}

    def test_init_failure(self):
        device_address = "/CONTEXT/server/other_device"
        property_name = "frame"
        source = TINECameraSource(device_address, property_name)
        data = source.read()
        assert data.failure

    def test_init_metadata_contains_status(self):
        with pytest.raises(ValueError):
            TINECameraSource(
                self.dummy_address, self.dummy_property,
                metadata={"status": "bad"})

    def test_read_success(self, tine_data):
        img, reply = tine_data
        s = TINECameraSource(self.dummy_address, self.dummy_property,
                             metadata={"device": self.dummy_address})
        data = s.read()
        timestamp = datetime.datetime.fromtimestamp(
                reply["timestamp"], timezone("Europe/Berlin"))
        assert data.timestamp == timestamp
        assert data.failure is None
        np.testing.assert_array_equal(data.value[self.dummy_property], img)
        assert data.metadata is not s.metadata
        assert data.metadata["device"] == self.dummy_address

    def test_read_error(self, tine_mock):
        maxdelta = datetime.timedelta(seconds=5)
        s = TINECameraSource(self.dummy_address, self.dummy_property,
                             metadata={"device": self.dummy_address})
        ex = RuntimeError("Some error")
        tine_mock.get.side_effect = ex
        data = s.read()
        now = datetime.datetime.now(timezone("Europe/Berlin"))
        assert data.timestamp - now < maxdelta
        assert data.failure is ex
        assert data.value is None
        assert data.metadata is not s.metadata
        assert data.metadata["device"] == self.dummy_address

    def test_read_wrong_status(self, tine_mock):
        maxdelta = datetime.timedelta(seconds=5)
        s = TINECameraSource(self.dummy_address, self.dummy_property,
                             metadata={"device": self.dummy_address})
        tine_mock.get.side_effect = None
        tine_mock.get.return_value = dict(status=1)
        data = s.read()
        now = datetime.datetime.now(timezone("Europe/Berlin"))
        assert data.timestamp - now < maxdelta
        assert data.failure is None
        assert data.value is None
        assert data.metadata is not s.metadata
        assert data.metadata["device"] == self.dummy_address

    def test_read_corrupted_data(self, tine_data):
        img, reply = tine_data
        reply["data"]["imageBytes"] = b"bad"
        s = TINECameraSource(self.dummy_address, self.dummy_property,
                             metadata={"device": self.dummy_address})
        data = s.read()
        timestamp = datetime.datetime.fromtimestamp(
                reply["timestamp"], timezone("Europe/Berlin"))
        assert data.timestamp == timestamp
        assert isinstance(data.failure, ValueError)
        assert data.value is None
        assert data.metadata is not s.metadata
        assert data.metadata["device"] == self.dummy_address
