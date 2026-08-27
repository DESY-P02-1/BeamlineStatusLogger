FROM debian:12

# Adapted from reszelaz/sardana-test for installing a minimal tango setup following
# http://tango-controls.readthedocs.io/en/latest/installation/tango-on-linux.html#debian-ubuntu
# The container must be started with --hostname tango-test


# change installation dialogs policy to noninteractive
# otherwise debconf raises errors: unable to initialize frontend: Dialog
# Do not use ENV because that would be persisting at runtime
ARG DEBIAN_FRONTEND=noninteractive


# install mysql
# and workaround for problems with starting mysqld
RUN apt-get update && apt-get -y install default-mysql-server \
    && mkdir -p /var/run/mysqld \
    && chown mysql /var/run/mysqld


# install tango
RUN echo 'tango-common tango-common/tango-host string tango-test:10000' \
    | debconf-set-selections \
    && echo 'tango-db tango-db/dbconfig-install boolean false' \
    | debconf-set-selections \
    && apt-get update && apt-get install -y \
        tango-db \
        tango-test


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
# apt install default-mysql-server
# service mariadb start
# apt install tango-db # answers: tango-test:1000, yes, test1234, test1234
# service tango-db start
# apt install tango-test
# /usr/lib/tango/TangoTest test
# tar -zcvf tango-test-db.tar.gz /var/lib/mysql/tango/ /etc/tangorc /var/lib/tango/.my.cnf
# exit
# docker container cp tango-test:tango-test-db.tar.gz .
ADD tango-test-db.tar.gz /

ENV TANGO_HOST=tango-test:10000

# start supervisor as deamon
CMD /usr/bin/supervisord
