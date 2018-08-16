from BeamlineStatusLogger.sinks import InfluxDBSink
from BeamlineStatusLogger.sources import Data
from influxdb import InfluxDBClient
from datetime import datetime
import pytest
import os


@pytest.fixture
def influx_client():
    host = os.environ.get("INFLUXDB_HOST", "localhost")
    port = os.environ.get("INFLUXDB_PORT", "8086")
    client = InfluxDBClient(host=host, port=port)
    return client


@pytest.fixture
def new_db_name(influx_client):
    i = 2
    db_name = "test" + str(i)
    while {"name": db_name} in influx_client.get_list_database():
        i += 1
        db_name = "test" + str(i)
    yield db_name
    if {"name": db_name} in influx_client.get_list_database():
        influx_client.drop_database(db_name)


@pytest.fixture
def influxdb(influx_client, new_db_name):
    database = new_db_name
    influx_client.create_database(database)
    influx_client.switch_database(database)
    return database


@pytest.fixture
def influx_sink(influxdb):
    database = influxdb
    measurement = "dummy"
    return InfluxDBSink(database, measurement)


class TestInfluxDBSink:
    def test_init_success(self, influxdb):
        database = influxdb
        measurement = "dummy"
        sink = InfluxDBSink(database, measurement)
        assert sink.measurement == measurement
        assert sink.client

    def test_init_create_db_succes(self, influx_client, new_db_name):
        database = new_db_name
        measurement = "dummy"
        sink = InfluxDBSink(database, measurement, create_db=True)
        assert sink.measurement == measurement
        assert sink.client
        assert {"name": database} in influx_client.get_list_database()

    def test_init_wrong_db(self, new_db_name):
        database = new_db_name
        measurement = "dummy"
        with pytest.raises(ValueError):
            InfluxDBSink(database, measurement)

    def test_format_number(self, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, 1, metadata={"id": 1234})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["fields"]["value"] == 1

    def test_format_dict(self, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, {"value1": 1, "value2": 2}, metadata={"id": 1234})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["fields"]["value1"] == 1
        assert res["fields"]["value2"] == 2

    def test_format_error(self, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, None, failure=Exception("msg"),
                    metadata={"id": 1234})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["fields"]["error"] == "msg"

    def test_write(self, influx_client, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, 1, metadata={"id": 1234})
        influx_sink.write(data)
        res = influx_client.query("SELECT * FROM " +
                                  influx_sink.measurement)
        rows = list(res[None])
        assert len(rows) == 1
        assert rows[0]["time"] == '2018-08-15T17:37:39.660509952Z'
        assert rows[0]["value"] == 1
        assert rows[0]["id"] == "1234"
