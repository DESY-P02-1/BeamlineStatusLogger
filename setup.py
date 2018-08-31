from distutils.core import setup

setup(name="BeamlineStatusLogger",
      version="0.0.1",
      description="Log data from a source to a sink",
      author="Tim Schoof",
      author_email="tim.schoof@desy.de",
      packages=["BeamlineStatusLogger", "tests"],
      install_requires=[
          "PyTango",  # PyTango takes very long to install by pip
          "influxdb",
          "scipy"
      ],
      )
