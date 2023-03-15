import datetime
from pathlib import Path
from influxdb import InfluxDBClient
from collections.abc import Mapping
import os
import numpy as np
from pytz import timezone


def filter_nones(dic):
    return {key: value for key, value in dic.items() if value is not None}


def none_to_nan(value):
    if value is None:
        return np.nan
    else:
        return value


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
    create_db : Boolean
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


def column_width_from_timespec(timespec):
    timestamp = datetime.datetime(
        2000, 1, 1, 12, 0, 0, 0, tzinfo=timezone("Europe/Berlin"))
    return len(timestamp.isoformat(timespec=timespec))


def column_width_from_value_format(value_format):
    value = 1/3
    return len(f"{value:{value_format}}")


class TextFileSink:
    """Write log data to a text file.

    If the file does not exist, it is created automatically. If the file does
    not already have a header, one is written the file first. Otherwise, only a
    new row is appended to the file.

    If the file did not already contain a header, the header is inferred from
    the first healthy (no failure) data point. Therefore, no rows are written
    until the first healthy data point is received and most importantly all
    healthy data points *must* have the same fields. If later data points
    contain unseen fields, a ValueError is thrown.

    Values of type None are written as "nan".

    Parameters
    ----------
    path : string
        Full path of the file to be written.
    sep : string
        Separator between columns (Default: "\\t")
    timespec : string
        Precision of the timestamps, see datetime.isoformat
        (default: "milliseconds")
    value_format : string
        Format used for all values
    create_dirs : Boolean
        If True, all parent directories are created if not already existing
        (Default: True)
    metadata : mapping
        Key-value pairs that will be added as comments before the header
    """
    def __init__(
        self,
        path,
        sep="\t",
        timespec="milliseconds",
        # TODO: There should be separate string and number formats
        value_format="<12.10g",
        create_dirs=True,
        metadata=None
    ):
        self.path = Path(path)
        self.file = None
        self.fieldnames = None
        self.sep = sep
        self.timespec = timespec
        self.timestamp_width = column_width_from_timespec(timespec)
        self.value_format = value_format
        if metadata is None:
            metadata = {}
        self.metadata = metadata
        parent_dir = self.path.parent
        if create_dirs:
            parent_dir.mkdir(parents=True, exist_ok=True)

    def _open_file(self):
        if self.file is None:
            # Without a file, fields cannot be known (fields from data and
            # fields from existing header might be different)
            assert self.fieldnames is None
            # read file to extract header
            try:
                with open(self.path, "r") as file:
                    self.fieldnames = self._get_fieldnames_from_file_header(
                        file)
            except OSError:
                # File does not exist or is not readable
                pass

            # reopen file in append only mode
            self.file = open(self.path, "a")

        return self.file

    def write(self, data):
        self._open_file()
        data_fieldnames = self._get_fieldnames_from_data(data)
        if data_fieldnames is None and self.fieldnames is None:
            # cannot write a header or row until the fields are determined from
            # the first healthy data point
            return False

        if self.fieldnames is None:
            # file didn't have a header when it was opened
            self.fieldnames = data_fieldnames
            header = self._format_header(data_fieldnames, data.metadata)
            self.file.write(header)
        elif data_fieldnames:
            # Check that fields in data are a subset of known fields
            for field in data_fieldnames:
                if field not in self.fieldnames:
                    raise ValueError(
                        f"Data contains previously unseen field: '{field}'")

        row = self._format_row(data)
        self.file.write(row)

        self.file.flush()
        if data.failure or data.value is None:
            return False
        elif isinstance(data.value, Mapping) and not filter_nones(data.value):
            # All entries are None
            return False
        else:
            return True

    def _get_fieldnames_from_data(self, data):
        if data.failure is not None or data.value is None:
            # This is not a healthy data point from which the fields can be
            # determined
            return None

        if isinstance(data.value, Mapping):
            fields = list(data.value.keys())
            fields.sort()
        else:
            fields = ["value"]

        if "error" in fields:
            raise ValueError("The field 'error' is a reserved name")

        return fields

    def _format_header(self, fieldnames, metadata):
        header = ""
        # The quality tag doesn't make sense in the header
        tags = {
            key: value for key, value in metadata.items() if key != "quality"}
        tags.update(self.metadata)
        if tags:
            for key, value in tags.items():
                header += f"# {key}: {value}\n"

        value_width = column_width_from_value_format(self.value_format)
        header += f"{'timestamp':<{self.timestamp_width}}\t"
        header += "\t".join(
            f"{field:<{value_width}}" for field in fieldnames)
        header += "\terror\n"
        return header

    def _format_row(self, data):
        if data.failure:
            error = data.failure.__class__.__name__
            fields = {}
        else:
            error = ""
            if isinstance(data.value, Mapping):
                fields = data.value
            else:
                fields = {"value": data.value}

        w = self.timestamp_width
        t = data.timestamp.isoformat(timespec=self.timespec)
        row = f"{t:<{w}}\t"
        row += "\t".join(
            f"{none_to_nan(fields[key]):{self.value_format}}"
            if key in fields else f"{np.nan:{self.value_format}}"
            for key in self.fieldnames)
        if error:
            row += "\t" + error
        else:
            # Remove unnecessary whitespace at the end of the line
            row = row.rstrip()
        row += "\n"
        return row

    def _get_fieldnames_from_file_header(self, file):
        header = None
        for line in file:
            if line and not line.startswith("#"):
                header = line
                break

        if header:
            if not (
                header.startswith("timestamp") and header.endswith("error\n")
            ):
                raise ValueError(
                    f"File '{file.name}' has invalid header: '{header}'")

            fields = [field.strip() for field in header.split()]
            # remove timestamp and error
            return fields[1:-1]
        else:
            return None
