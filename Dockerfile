FROM registry.access.redhat.com/ubi8/python-39:latest

# We need to be root to setup the container image
USER root

COPY misc/centos.repo /etc/yum.repos.d/centos.repo
#RUN yum repolist all

# Install required packages
RUN yum install -y yum-utils curl nc iproute iputils git gcc lksctp-tools-devel 

# Copying the source of this project
COPY poetry.lock /opt/nfv-test-api/poetry.lock
COPY pyproject.toml /opt/nfv-test-api/pyproject.toml
COPY src/ /opt/nfv-test-api/src
COPY config.yaml /etc/nfv-test-api.yaml
COPY entrypoint.sh /entrypoint.sh

# Installing ueransim
RUN git clone https://github.com/aligungr/UERANSIM && \
    cd UERANSIM && \
    make && \
    mv build/* /bin

# Installing nfv-test-api
RUN cd /opt/nfv-test-api && \
    python3 -m venv env && \
    . ./env/bin/activate && \
    pip install -U pip wheel && \
    pip install -U poetry && \
    poetry install --no-dev && \
    ln -s /opt/nfv-test-api/env/bin /opt/nfv-test-api/bin && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8080
CMD nfv-test-api
