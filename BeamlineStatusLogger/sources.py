import PyTango as tango
from concurrent import futures


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

    Parameters
    ----------
    device_name : string
        Name of the device
    attribute_name :
        Name of the attribute
    metadata : dict_like
        The metadata is added to every returned data object
    """
    def __init__(self, device_name, attribute_name, metadata={}):
        self.device_name = device_name
        self.attribute_name = attribute_name
        # TODO: Should a possible exception be wrapped?
        self.device = tango.DeviceProxy(device_name)
        # Test if attribute exists
        self.device.attribute_query(attribute_name)
        self.metadata = metadata

    def read(self):
        try:
            device_attribute = self.device.read_attribute(self.attribute_name)
        # TODO: Should also handle Timeout from gevent
        except (tango.DevFailed, futures.TimeoutError) as err:
            # TODO: Check if this is close enough to the would be time of
            #       a successful read
            timestamp = tango.TimeVal.todatetime(tango.TimeVal.now())
            return Data(timestamp, None, err, metadata=self.metadata)
        timestamp = tango.TimeVal.todatetime(device_attribute.get_date())
        return Data(timestamp, device_attribute.value, metadata=self.metadata)
