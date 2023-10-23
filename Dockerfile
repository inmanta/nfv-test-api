FROM rockylinux:9

# We need to be root to setup the container image
USER root

# Enable more repos
RUN dnf install -y epel-release dnf-plugins-core
RUN dnf install -y --allowerasing curl
RUN dnf config-manager --set-enabled devel
#COPY misc/rocky.repo /etc/yum.repos.d/rocky.repo

# Install required packages
RUN dnf install -y vim yum-utils curl nc iproute iputils git gcc lksctp-tools-devel traceroute nmap tcpdump \
    fftw-libs fftw-devel fftw-static mbedtls-devel libconfig glibc-devel czmq-devel cmake gcc gcc-c++ python3.11-devel \
    boost-devel libconfig-devel

# Install ueransim
RUN git clone https://github.com/aligungr/UERANSIM && \
    cd UERANSIM && \
    git checkout ab5cd8607f914c6ca6bbb48114a008b6bf8e21d0 && \
    make && \
    mv build/* /bin

# Install srsLTE
RUN git clone https://github.com/srsRAN/srsRAN_4G.git && \
    cd srsRAN_4G && \
    mkdir build && \
    cd build && \
    cmake ../ && \
    make && \
    make install

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
