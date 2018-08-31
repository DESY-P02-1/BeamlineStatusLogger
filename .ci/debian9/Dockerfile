FROM debian:stretch

# Adapted from reszelaz/sardana-test for installing a minimal tango setup following
# http://tango-controls.readthedocs.io/en/latest/installation/tango-on-linux.html#debian-ubuntu
# The container must be started with --hostname tango-test


RUN apt-get update


# change installation dialogs policy to noninteractive
# otherwise debconf raises errors: unable to initialize frontend: Dialog
ENV DEBIAN_FRONTEND noninteractive


# install mysql
RUN apt-get -y install mysql-server
# workarounds for problems with starting mysqld
RUN sed -i 's/\/var\/run\/mysqld\/mysqld.pid/\/tmp\/mysqld.pid/g' /etc/mysql/mariadb.conf.d/50-server.cnf
RUN sed -i 's/\/var\/run\/mysqld\/mysqld.sock/\/tmp\/mysqld.sock/g' /etc/mysql/mariadb.conf.d/50-server.cnf
RUN mkdir /var/run/mysqld
RUN ln -s /tmp/mysqld.sock /var/run/mysqld/mysqld.sock
RUN ln -s /tmp/mysqld.pid /var/run/mysqld/mysqld.pid


# install tango-db
RUN echo 'tango-common tango-common/tango-host string tango-test:10000' | debconf-set-selections \
    && echo 'tango-db tango-db/dbconfig-install boolean false' | debconf-set-selections \
    && apt-get install -y tango-db


#install tango-test
RUN apt-get install -y tango-test


# install PyTango
RUN apt-get -y install python3-pytango


# Install additional dependencies for package testing
RUN apt-get -y install procps python3-pip python3-pytest python3-flake8 python3-scipy

RUN pip3 install influxdb


# more info at https://docs.docker.com/config/containers/multi-service_container/
# install and configure supervisor
RUN apt-get install -y supervisor
RUN mkdir -p /var/log/supervisor


# configure supervisord
COPY supervisord.conf /etc/supervisor/conf.d/


ADD tango-test-db.tar.gz /


ENV TANGO_HOST=tango-test:10000


# start supervisor as deamon
CMD /usr/bin/supervisord
