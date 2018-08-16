from influxdb import InfluxDBClient
from collections.abc import Mapping
import os


class InfluxDBSink:
    def __init__(self, database, measurement,
                 host=os.environ.get("INFLUXDB_HOST", "localhost"),
                 port=os.environ.get("INFLUXDB_PORT", "8086"),
                 create_db=False,
                 **kwargs):
        self.client = InfluxDBClient(host, port, database=database, **kwargs)
        self.measurement = measurement
        if create_db:
            self.client.create_database(database)
        else:
            # Test if data base exists
            if not {"name": database} in self.client.get_list_database():
                raise ValueError("Database " + database + " does not exist")

    def write(self, data):
        self.client.write_points([self._format(data)])

    def _format(self, data):
        if data.failure:
            fields = {"error": str(data.failure)}
        elif isinstance(data.value, Mapping):
            fields = data.value
        else:
            fields = {"value": data.value}
        return {
            "measurement": self.measurement,
            # TODO: handle time zones
            "time": data.timestamp,
            "fields": fields,
            "tags": data.metadata
        }
