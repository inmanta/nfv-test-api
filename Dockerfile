FROM python:3.6

ARG CHECKOUT=master
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Copying the source of this project
COPY poetry.lock /home/user/nfv-test-api/poetry.lock
COPY pyproject.toml //home/user/nfv-test-api/pyproject.toml
COPY src/ /home/user/nfv-test-api/src
COPY config.yaml /home/user/nfv-test-api/config.yaml

# Creating user
RUN groupadd user && \
	useradd -g user -G user -ms /bin/bash user && \
    chown -R user:user /home/user

RUN apt-get update && \
    apt-get install iproute2 -y
    
USER user
WORKDIR /home/user

# Installing 
RUN cd nfv-test-api && \
    python3 -m venv env && \
    . ./env/bin/activate && \
    pip install -U pip wheel && \
    pip install -U poetry && \
    poetry install --no-dev

USER root

EXPOSE 8080
CMD /home/user/nfv-test-api/env/bin/python -m nfv_test_api.main --config nfv-test-api/config.yaml
