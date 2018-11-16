from setuptools import setup
from setuptools.command.install import install
from distutils import log
import os

CONFDIR = "/etc/beamline_status_logger"
SCRIPTNAME = "beamline_status_logger"
SERVICEPATH = "/lib/systemd/system/beamline_status_logger@.service"
EXAMPLEDIR = "/usr/share/doc/beamline_status_logger/examples"


def install_system_service(infile, outfile, script, confdir):
    with open(infile) as fin:
        template = fin.read()

    with open(outfile, "w") as fout:
        fout.write(template.format(script=script, confdir=confdir))


class CustomInstall(install):
    def run(self):
        super().run()
        if self.root:
            if SERVICEPATH.startswith("/"):
                servicepath = os.path.join(self.root, SERVICEPATH[1:])
            else:
                servicepath = os.path.join(self.root, SERVICEPATH)
        else:
            servicepath = SERVICEPATH
        log.info("writing " + servicepath)
        if not self.dry_run:
            install_system_service(
                "config/beamline_status_logger@.service.in",
                servicepath,
                self.get_scriptfile_path(),
                os.path.join(CONFDIR, "")
            )

    def get_scriptfile_path(self):
        bindir = self.install_scripts
        rootdir = self.root
        if rootdir and bindir.startswith(rootdir):
            bindir = bindir[len(rootdir):]
        return os.path.join(bindir, SCRIPTNAME)


setup(name="BeamlineStatusLogger",
      version="0.1.0",
      description="Log data from a source to a sink",
      author="Tim Schoof",
      author_email="tim.schoof@desy.de",
      packages=["BeamlineStatusLogger"],
      install_requires=[
          "PyTango",  # PyTango takes very long to install by pip
          "influxdb",  # not in Debian stretch
          "scipy",
          "scikit-image",
          "pytz"
      ],
      zip_safe=False,
      data_files=[
            ("/lib/systemd/system", ["config/beamline_status_logger.target"]),
            (CONFDIR, []),
            (EXAMPLEDIR, ["config/example.logger"])
      ],
      scripts=[os.path.join("bin/", SCRIPTNAME)],
      cmdclass={
            'install': CustomInstall
      },
      )
