from influxdb import InfluxDBClient
from collections.abc import Mapping
import os


def filter_nones(dic):
    return {key: value for key, value in dic.items() if value is not None}


class InfluxDBSink:
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
