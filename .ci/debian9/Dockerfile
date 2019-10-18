FROM debian:stretch

# Adapted from reszelaz/sardana-test for installing a minimal tango setup following
# http://tango-controls.readthedocs.io/en/latest/installation/tango-on-linux.html#debian-ubuntu
# The container must be started with --hostname tango-test


# change installation dialogs policy to noninteractive
# otherwise debconf raises errors: unable to initialize frontend: Dialog
# Do not use ENV because that would be persisting at runtime
ARG DEBIAN_FRONTEND=noninteractive


# install mysql
# and workaround for problems with starting mysqld
RUN apt-get update && apt-get -y install mysql-server \
    && sed -i 's/\/var\/run\/mysqld\/mysqld.pid/\/tmp\/mysqld.pid/g' \
            /etc/mysql/mariadb.conf.d/50-server.cnf \
    && sed -i 's/\/var\/run\/mysqld\/mysqld.sock/\/tmp\/mysqld.sock/g' \
            /etc/mysql/mariadb.conf.d/50-server.cnf \
    && mkdir /var/run/mysqld \
    && ln -s /tmp/mysqld.sock /var/run/mysqld/mysqld.sock \
    && ln -s /tmp/mysqld.pid /var/run/mysqld/mysqld.pid


# install tango
RUN echo 'tango-common tango-common/tango-host string tango-test:10000' \
    | debconf-set-selections \
    && echo 'tango-db tango-db/dbconfig-install boolean false' \
    | debconf-set-selections \
    && apt-get update && apt-get install -y \
        tango-db \
        tango-test \
        python3-pytango


# Install additional dependencies for package testing
RUN apt-get update && apt-get install -y \
        procps \
        python3-pip \
        python3-pytest \
        python3-pytest-cov \
        python3-pytest-mock \
        python3-flake8 \
        python3-scipy \
        python3-skimage \
        devscripts \
        debhelper \
        quilt \
        adduser \
        git-buildpackage \
    && pip3 install influxdb


# more info at https://docs.docker.com/config/containers/multi-service_container/
# install and configure supervisor
RUN apt-get install -y supervisor \
    && mkdir -p /var/log/supervisor


# configure supervisord
COPY supervisord.conf /etc/supervisor/conf.d/


# This file was created with the following commands
# docker run -it --name tango-test --hostname tango-test debian:stretch /bin/bash
# apt update
# apt install dialog
# apt install mysql-server
# service mysql start
# apt install tango-db # answers: tango-test:1000, yes, test1234, test1234
# service tango-db start
# apt install tango-test
# /usr/lib/tango/TangoTest test
# tar -zcvf tango-test-db.tar.gz /var/lib/mysql/tango/ /etc/tangorc /var/lib/tango/.my.cnf
# exit
# docker container cp tango-test:tango-test-db.tar.gz .
ADD tango-test-db.tar.gz /


ENV TANGO_HOST=tango-test:10000

WORKDIR /code

# start supervisor as deamon
CMD /usr/bin/supervisord
