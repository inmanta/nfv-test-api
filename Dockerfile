FROM registry.access.redhat.com/ubi8/python-311:latest

# We need to be root to setup the container image
USER root

COPY misc/centos.repo /etc/yum.repos.d/centos.repo

# Install required packages
RUN yum install -y yum-utils curl nc iproute iputils git gcc lksctp-tools-devel traceroute nmap tcpdump

# Installing ueransim
RUN git clone https://github.com/aligungr/UERANSIM && \
    cd UERANSIM && \
    git checkout ab5cd8607f914c6ca6bbb48114a008b6bf8e21d0 && \
    make && \
    mv build/* /bin

# Copying the source of this project
COPY setup.cfg /opt/nfv-test-api/setup.cfg
COPY pyproject.toml /opt/nfv-test-api/pyproject.toml
COPY src/ /opt/nfv-test-api/src
COPY config.yaml /etc/nfv-test-api.yaml
COPY entrypoint.sh /entrypoint.sh

# Installing nfv-test-api
RUN cd /opt/nfv-test-api && \
    python3 -m venv env && \
    . ./env/bin/activate && \
    pip install .  && \
    ln -s /opt/nfv-test-api/env/bin /opt/nfv-test-api/bin && \
    chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8080
CMD nfv-test-api
