# BeamlineStatusLogger

Log beamline attributes to a database.

A *logger* reads data from a *source* and writes it to a *sink*, optionally applying one or more *processors*. It is triggered by a *timer*. The whole pipeline can be defined by INI style configuration files.

In the current version, only [Tango](http://www.tango-controls.org/) attributes are supported as sources and only [InfluxDB](https://www.influxdata.com/time-series-platform/influxdb/) as the sink. The only processor currently available fits a 2D Gaussian to an image and returns the fit parameters. The current timer allows for periodic polling with automatic slow down in case of repeated errors.

## Usage

A logger process can be started with `beamline_status_logger path/to/config.logger`

An example configuration file using most of the currently implemented features can be found in the `config` directory.

The configuration files are parsed using the Python [configparser](https://docs.python.org/3/library/configparser.html#supported-ini-file-structure) module in the extended configuration mode. An additional feature is recursive parsing of configuration files. A derived configuration file can specify one parent file in the following way:
```
[based on]
path/to/file
```
where `path/to/file` is either absolute or relative to the path of the derived configuration file. The parser follows the chain of parents until it reaches a file without this section. Options in derived files overwrite options in parent files. This allows for the definition of many similar logger instances with minimal repetition.

## Extending BeamlineStatusLogger

The BeamlineStatusLogger uses duck typing and can therefore easily extended by new classes implementing the informal interfaces of the various components:

* A *source* class must provide a `read` method, which returns a *data* object
* A *sink* class must provide a `write` method, which accepts a *data* object and returns `True` or `False` to signal success or failure, respectively
* A *processor* must be a callable which takes a data object and returns a possibly different data object
* A timer must be a callable which accepts the return value of a sink's `write` method, i.e., a Boolean, and return `True` when logging should continue or `False`, otherwise, e.g., when its `abort` method was called

The exchange of data objects relies on the dynamic nature of Python. The fields of a *data* object can contain values of any type. It is therefore the responsibility of the user to ensure that each part of the processing pipeline works with the return type of the previous step.
