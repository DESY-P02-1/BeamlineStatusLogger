from BeamlineStatusLogger.sinks import InfluxDBSink, TextFileSink, filter_nones
from BeamlineStatusLogger.sources import Data
from influxdb import InfluxDBClient
from datetime import datetime
from pytz import timezone
import pytest
import os
import uuid


def test_filter_nones():
    d = {"a": 1, "b": "foo", "c": None,
         "d": {"a": 2, "b": None, "c": "None"}}
    res = filter_nones(d)
    assert res == {"a": 1, "b": "foo",
                   "d": {"a": 2, "b": None, "c": "None"}}


@pytest.fixture
def influx_client():
    host = os.environ.get("INFLUXDB_HOST", "localhost")
    port = os.environ.get("INFLUXDB_PORT", "8086")
    client = InfluxDBClient(host=host, port=port)
    return client


@pytest.fixture
def new_db_name(influx_client):
    db_name = "test_" + str(uuid.uuid4())
    while {"name": db_name} in influx_client.get_list_database():
        db_name = "test_" + str(uuid.uuid4())
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
    return InfluxDBSink(database, measurement, metadata={"id": 1234})


class TestInfluxDBSink:
    def test_init_success(self, influxdb):
        database = influxdb
        measurement = "dummy"
        sink = InfluxDBSink(database, measurement)
        assert sink.measurement == measurement
        assert sink.client
        assert sink.metadata == {}

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
        data = Data(time, 1, metadata={"attribute": "postition"})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["tags"]["attribute"] == "postition"
        assert res["fields"]["value"] == 1

    def test_format_dict(self, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, {"value1": 1, "value2": 2, "value": None},
                    metadata={"attribute": "postition"})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["tags"]["attribute"] == "postition"
        assert res["fields"]["value1"] == 1
        assert res["fields"]["value2"] == 2
        assert "value3" not in res["fields"]

    def test_format_error(self, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, None, failure=Exception("msg"),
                    metadata={"attribute": "postition"})
        res = influx_sink._format(data)
        assert res["measurement"] == influx_sink.measurement
        assert res["time"] == time
        assert res["tags"]["id"] == 1234
        assert res["tags"]["attribute"] == "postition"
        assert res["fields"]["error"] == "msg"

    def test_write(self, influx_client, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 524288)
        time = timezone("Europe/Berlin").localize(time)
        data = Data(time, 1, metadata={"attribute": "postition"})
        success = influx_sink.write(data)
        assert success
        res = influx_client.query("SELECT * FROM " +
                                  influx_sink.measurement)
        rows = list(res.get_points())
        assert len(rows) == 1
        assert rows[0]["time"] == '2018-08-15T15:37:39.524288Z'
        assert rows[0]["value"] == 1
        assert rows[0]["id"] == "1234"
        assert rows[0]["attribute"] == "postition"

    @pytest.mark.parametrize("value", [None, {"value": None}])
    def test_write_none(self, influx_client, influx_sink, value):
        time = datetime(2018, 8, 15, 17, 37, 39, 524288)
        data = Data(time, value, metadata={"attribute": "postition"})
        success = influx_sink.write(data)
        assert not success
        res = influx_client.query("SELECT * FROM " +
                                  influx_sink.measurement)
        rows = list(res.get_points())
        assert len(rows) == 1
        assert len(rows[0]) == 4
        assert rows[0]["time"] == '2018-08-15T17:37:39.524288Z'
        assert rows[0]["NoValue"]
        assert rows[0]["id"] == "1234"
        assert rows[0]["attribute"] == "postition"

    def test_write_failure(self, influx_client, influx_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 524288)
        data = Data(time, None, failure=Exception("msg"),
                    metadata={"attribute": "postition"})
        success = influx_sink.write(data)
        assert not success
        res = influx_client.query("SELECT * FROM " +
                                  influx_sink.measurement)
        rows = list(res.get_points())
        assert len(rows) == 1
        assert rows[0]["time"] == '2018-08-15T17:37:39.524288Z'
        assert rows[0]["error"] == "msg"


@pytest.fixture
def text_file_sink(tmp_path):
    filename = tmp_path / "out.dat"
    return TextFileSink(filename, metadata={"id": 1234})


class TestTextFileSink:
    def test_init_success(self, tmp_path):
        filename = tmp_path / "out.dat"
        sink = TextFileSink(filename)
        assert sink.path == filename
        assert sink.file is None
        assert sink.metadata == {}

    def test_init_create_parent_dirs(self, tmp_path):
        filename = tmp_path / "does_not_exist" / "out.dat"
        TextFileSink(filename)
        assert filename.parent.exists()

    def test_init_do_not_create_parent_dirs(self, tmp_path):
        filename = tmp_path / "does_not_exist" / "out.dat"
        TextFileSink(filename, create_dirs=False)
        assert not filename.parent.exists()

    def test_write_number(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, 1, metadata={"attribute": "position"})
        success = text_file_sink.write(data)
        assert success
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == (
            "# attribute: position\n"
            "# id: 1234\n"
            "timestamp                    	value       	error\n"
            "2018-08-15T17:37:39.660      	1\n"
        )

    def test_write_dict(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, {"value1": 1, "value2": 2, "value": None},
                    metadata={"attribute": "position"})
        success = text_file_sink.write(data)
        assert success
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == (
            "# attribute: position\n"
            "# id: 1234\n"
            "timestamp                    	value       	value1      	value2      	error\n"
            "2018-08-15T17:37:39.660      	nan         	1           	2\n"
        )

    def test_write_error_first_data_point(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, None, failure=RuntimeError("msg"),
                    metadata={"attribute": "position"})
        success = text_file_sink.write(data)
        assert not success
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == ""

    def test_write_error_second_data_point(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, 1, metadata={"attribute": "position"})
        res = text_file_sink.write(data)
        assert res
        data = Data(time, None, failure=RuntimeError("msg"),
                    metadata={"attribute": "position"})
        res = text_file_sink.write(data)
        assert not res
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == (
            "# attribute: position\n"
            "# id: 1234\n"
            "timestamp                    	value       	error\n"
            "2018-08-15T17:37:39.660      	1\n"
            "2018-08-15T17:37:39.660      	nan         \tRuntimeError\n"
        )

    @pytest.mark.parametrize("value", [None, {"value": None}])
    def test_write_none(self, text_file_sink, value):
        # Write header so that writing a None value succeeds
        text_file_sink.path.write_text(
            "timestamp                    	value       	error\n")
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, value, metadata={"attribute": "position"})
        success = text_file_sink.write(data)
        assert not success
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == (
            "timestamp                    	value       	error\n"
            "2018-08-15T17:37:39.660      	nan\n"
        )

    def test_write_data_points_mismatching_fieldnames(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(time, {"foo": 1})
        success = text_file_sink.write(data)
        assert success
        time = datetime(2018, 8, 15, 17, 37, 44, 660510)
        data = Data(time, {"bar": 1})
        with pytest.raises(ValueError, match="previously unseen"):
            text_file_sink.write(data)

    def test_write_data_points_mismatching_header(self, text_file_sink):
        text_file_sink.path.write_text(
            "timestamp              	foo 	error\n")
        time = datetime(2018, 8, 15, 17, 37, 44, 660510)
        data = Data(time, {"bar": 1})
        with pytest.raises(ValueError, match="previously unseen"):
            text_file_sink.write(data)

    def test_read_header_from_file(self, text_file_sink):
        text_file_sink.path.write_text(
            "# some: 1\n"
            "# metadata: True\n"
            "timestamp                    	foo 	error\n"
            "2018-08-15T17:37:39.660      	1\n")
        time = datetime(2018, 8, 15, 17, 37, 44, 660510)
        data = Data(time, None)
        success = text_file_sink.write(data)
        assert not success
        assert text_file_sink.path.read_text() == (
            "# some: 1\n"
            "# metadata: True\n"
            "timestamp                    	foo 	error\n"
            "2018-08-15T17:37:39.660      	1\n"
            "2018-08-15T17:37:44.660      	nan\n"
        )

    def test_read_header_from_file_invalid(self, text_file_sink):
        text_file_sink.path.write_text(
            "# some: 1\n"
            "# metadata: True\n"
            "foo                          	bar 	error\n"
            "2018-08-15T17:37:39.660      	1\n")
        time = datetime(2018, 8, 15, 17, 37, 44, 660510)
        data = Data(time, {"foo": 1})
        with pytest.raises(ValueError, match="invalid"):
            text_file_sink.write(data)

    def test_filter_quality_tag_from_header(self, text_file_sink):
        time = datetime(2018, 8, 15, 17, 37, 39, 660510)
        data = Data(
            time, 1,
            metadata={"attribute": "position", "quality": "ATTR_VALID"})
        success = text_file_sink.write(data)
        assert success
        assert text_file_sink.path.exists()
        assert text_file_sink.path.read_text() == (
            "# attribute: position\n"
            "# id: 1234\n"
            "timestamp                    	value       	error\n"
            "2018-08-15T17:37:39.660      	1\n"
        )
