import PyTango as tango
try:
    import PyTine as tine
except ImportError as err:
    tine = None
    tine_import_err = err
from concurrent import futures
from datetime import datetime
import numpy as np
from pytz import timezone


class MissingDataException(Exception):
    """Can be used to indicate a reason for a missing value in a Data object.
    """
    pass


class Data:
    """Contains a value with a corresponding timestamp and some metadata.

    If the `value` at a given `timestamp` does not exist, `failure` holds a
    related exception.

    Attributes
    ----------
    timestamp : datetime
    value : any
    failure : Exception or None
    metadata : dict
    """
    def __init__(self, timestamp, value,
                 failure=None, metadata={}):
        self.timestamp = timestamp
        self.value = value
        self.failure = failure
        self.metadata = metadata


class TangoDeviceAttributeSource:
    """A wrapper around a PyTango DeviceProxy that satisfies the Source interface.

    The "quality" tag of the device attribute is returned as part of the
    metadata.

    Parameters
    ----------
    device_name : string
        Name of the device
    attribute_name :
        Name of the attribute
    metadata : dict_like
        The metadata is added to every returned data object
    """
    def __init__(self, device_name, attribute_name, metadata={}, tz=None):
        self.device_name = device_name
        self.attribute_name = attribute_name
        # TODO: Should a possible exception be wrapped?
        self.device = tango.DeviceProxy(device_name)
        # Test if attribute exists
        self.device.attribute_query(attribute_name)
        self.metadata = metadata
        if "quality" in self.metadata:
            raise ValueError("The metadata entry 'quality' is reserved for the"
                             "device attribute field of the same name. Choose"
                             "a different name instead.")
        if tz:
            self.localtz = tz
        else:
            self.localtz = timezone('Europe/Berlin')

    def read(self):
        try:
            device_attribute = self.device.read_attribute(self.attribute_name)
        # TODO: Should also handle Timeout from gevent
        except (tango.DevFailed, futures.TimeoutError) as err:
            # TODO: Check if this is close enough to the would be time of
            #       a successful read
            timestamp = tango.TimeVal.todatetime(tango.TimeVal.now())
            timestamp = self.localtz.localize(timestamp)
            return Data(timestamp, None, err, metadata=self.metadata.copy())
        timestamp = tango.TimeVal.todatetime(device_attribute.get_date())
        timestamp = self.localtz.localize(timestamp)
        value = {self.attribute_name: device_attribute.value}
        metadata = self.metadata.copy()
        metadata["quality"] = str(device_attribute.quality)
        return Data(timestamp, value, metadata=metadata)


def get_tine_image_height(frameHeader):
    if frameHeader["aoiHeight"] > 0:
        height = frameHeader["aoiHeight"]
    else:
        height = frameHeader["sourceHeight"]

    if not 0 < height <= 65535:
        raise ValueError("Invalid height = {}".format(height))

    return height


def get_tine_image_width(frameHeader):
    if frameHeader["aoiWidth"] > 0:
        width = frameHeader["aoiWidth"]
    else:
        width = frameHeader["sourceWidth"]

    if not 0 < width <= 65535:
        raise ValueError("Invalid width = {}".format(width))

    return width


def get_tine_image_dtype(frameHeader):
    # TODO: Endianness?
    if frameHeader["bytesPerPixel"] == 1:
        dtype = "u1"
    elif frameHeader["bytesPerPixel"] == 2:
        dtype = "u2"
    else:
        raise ValueError("Invalid bytesPerPixel = {}".format(
            frameHeader["bytesPerPixel"]))

    return dtype


def tine_image_to_numpy(data):
    frameHeader = data["frameHeader"]

    height = get_tine_image_height(frameHeader)
    width = get_tine_image_width(frameHeader)
    dtype = get_tine_image_dtype(frameHeader)

    bytes = np.frombuffer(data["imageBytes"], dtype=dtype)

    if len(bytes) != height*width:
        raise ValueError(
            "Dimension mismatch: len(bytes) = {}, height*width = {}".format(
                len(bytes), height*width))

    return bytes.reshape((height, width))


class TINECameraSource:
    """A specialized interface to the TINE beam position cameras

    Parameters
    ----------
    device_address : string
        Name of the device
    property_name : string
        Name of the property
    metadata : dict_like
        The metadata is added to every returned data object
    """
    def __init__(self, device_address, property_name, metadata={}, tz=None):
        if tine is None:
            raise tine_import_err
        self.device_address = device_address
        self.property_name = property_name
        # Test if device and property exists
        tine.get(self.device_address, self.property_name)
        self.metadata = metadata
        if "status" in self.metadata:
            raise ValueError("The metadata entry 'status' is reserved for the"
                             "readback value key of the same name. Choose"
                             "a different name instead.")
        if tz:
            self.localtz = tz
        else:
            self.localtz = timezone('Europe/Berlin')

    def read(self):
        try:
            device_property = tine.get(self.device_address, self.property_name)
        except (OSError, RuntimeError) as err:
            # TODO: Check if this is close enough to the would be time of
            #       a successful read
            timestamp = datetime.now()
            timestamp = self.localtz.localize(timestamp)
            return Data(timestamp, None, err, metadata=self.metadata.copy())

        status = tine.strerror(device_property["status"])
        metadata = self.metadata.copy()
        metadata["status"] = status
        if status.endswith(": success"):
            timestamp = datetime.fromtimestamp(device_property["timestamp"])
            timestamp = self.localtz.localize(timestamp)
            try:
                img = tine_image_to_numpy(device_property["data"])
            except ValueError as err:
                return Data(timestamp, None, err, metadata=metadata)
            value = {self.property_name: img}
        else:
            timestamp = datetime.now()
            timestamp = self.localtz.localize(timestamp)
            value = None
        return Data(timestamp, value, metadata=metadata)
