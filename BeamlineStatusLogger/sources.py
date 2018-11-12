import PyTango as tango
from concurrent import futures
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
