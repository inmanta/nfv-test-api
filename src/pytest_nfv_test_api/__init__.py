"""
       Copyright 2021 Inmanta

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import logging
import threading
import time
import typing
from ipaddress import ip_address

import docker  # type: ignore
import docker.errors  # type: ignore
import pytest
import requests
from docker.models import containers, images  # type: ignore

LOGGER = logging.getLogger(__name__)

__version__ = "2.6.0"


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    """
    Build a docker client object.
    """
    return docker.from_env()


@pytest.fixture(scope="session")
def nfv_test_api_image(docker_client: docker.DockerClient) -> images.Image:
    """
    Pull the latest version of the nfv-test-api container published on dockerhub
    and return an object representing it.
    """
    return docker_client.images.pull("inmantaci/nfv-test-api")


@pytest.fixture(scope="function")
def nfv_test_api_instance_pre(
    docker_client: docker.DockerClient, nfv_test_api_image: images.Image
) -> typing.Generator[containers.Container, None, None]:
    """
    Create the container and make sure it is removed after the test.  The container
    is not started or stopped.
    """
    container = docker_client.containers.create(
        image=nfv_test_api_image.id,
        detach=True,
        privileged=True,
    )
    assert isinstance(container, containers.Container), type(container)

    yield container

    container.remove()
    try:
        container.wait(condition="removed")
    except docker.errors.NotFound:
        # The container is already removed
        pass


@pytest.fixture(scope="function")
def nfv_test_api_instance(
    docker_client: docker.DockerClient,
    nfv_test_api_instance_pre: containers.Container,
) -> typing.Generator[containers.Container, None, None]:
    """
    This fixture create and starts a container running the nfv-test-api and returns it api object.
    """
    container = nfv_test_api_instance_pre
    container.start()

    # Waiting for the container to be started
    while container.status == "created":
        time.sleep(1)
        container_info = docker_client.containers.get(container.id)
        assert isinstance(container_info, containers.Container)
        container = container_info

    if container.status != "running":
        LOGGER.error("%s", container.logs().decode("utf-8"))
        raise RuntimeError("Failed to start container")

    yield container

    container.kill()
    container.wait(condition="not-running")


@pytest.fixture(scope="function")
def nfv_test_api_endpoint(nfv_test_api_instance: containers.Container) -> str:
    """
    This fixture waits for the api to be reachable then returns the url it can be reached at.
    """
    # Waiting for the server to be up
    container_ip = ip_address(
        nfv_test_api_instance.attrs["NetworkSettings"]["IPAddress"]
    )
    api = f"http://{container_ip}:8080/api/v2"

    max_attempts = 10
    while (
        requests.get(f"{api}/docs", timeout=0.5).status_code != 200 and max_attempts > 0
    ):
        time.sleep(1)
        max_attempts -= 1

    if max_attempts == 0:
        raise RuntimeError("Failed to start server")

    return api


@pytest.fixture(scope="function")
def nfv_test_api_logs(
    nfv_test_api_instance: containers.Container, nfv_test_api_endpoint: str
) -> typing.Generator[None, None, None]:
    """
    Starts a thread that will log all the logs from the container.
    """
    stop = False

    def logs_logger() -> None:
        logs = iter(nfv_test_api_instance.logs(stream=True))
        while not stop:
            LOGGER.debug(next(logs).decode().strip("\n"))

    thread = threading.Thread(target=logs_logger)
    thread.start()

    yield None

    time.sleep(1)
    stop = True
    # Sending one last request to generate a log line
    response = requests.get(f"{nfv_test_api_endpoint}/docs")
    response.raise_for_status()

    thread.join()
