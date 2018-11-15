from influxdb import InfluxDBClient
from collections.abc import Mapping
import os


def filter_nones(dic):
    return {key: value for key, value in dic.items() if value is not None}


class InfluxDBSink:
    """A wrapper around an InfluxDBClient that satisfies the Sink interface.

    Values of type None are removed before a point is written to the database.
    If the data to be written contains no fields or only fields of type None,
    A NoValue field with the value True is written instead.

    Parameters
    ----------
    database : string
        Name of the database that data is written to
    measurement : string
        Name of the measurement that data is written to
    host : string
        InfluxDB host. If not given, the environment variable INFLUXDB_HOST is
        used instead
    port : string or int
        InfluxDB port. If not given, the environment variable INFLUXDB_PORT is
        used instead
    create_db : Booolean
        If True, the database is created if it does not already exist
    metadata : mapping
        These entries are appended as the tags to each point

    Additional parameters are forwarded to the InfluxDBClient.
    """
    def __init__(self, database, measurement,
                 host=os.environ.get("INFLUXDB_HOST", "localhost"),
                 port=os.environ.get("INFLUXDB_PORT", "8086"),
                 create_db=False,
                 metadata={},
                 **kwargs):
        self.client = InfluxDBClient(host, port, database=database, **kwargs)
        self.measurement = measurement
        self.metadata = metadata
        if create_db:
            self.client.create_database(database)
        else:
            # Test if data base exists
            if not {"name": database} in self.client.get_list_database():
                raise ValueError("Database " + database + " does not exist")

    def write(self, data):
        point = self._format(data)
        if point["fields"]:
            success = self.client.write_points([point])
            success = success and data.failure is None
            return success
        else:
            point["fields"] = {"NoValue": True}
            self.client.write_points([point])
            return False

    def _format(self, data):
        if data.failure:
            fields = {"error": str(data.failure)}
        elif isinstance(data.value, Mapping):
            fields = data.value
        else:
            fields = {"value": data.value}
        fields = filter_nones(fields)
        tags = data.metadata
        tags.update(self.metadata)
        return {
            "measurement": self.measurement,
            # TODO: handle time zones
            "time": data.timestamp,
            "fields": fields,
            "tags": tags
        }
