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
import os
import threading
import time
import uuid
from ipaddress import ip_address
from typing import Generator

import docker  # type: ignore
import pytest
import requests
from docker.errors import ImageNotFound, NotFound  # type: ignore
from docker.models import containers, images  # type: ignore

LOGGER = logging.getLogger(__name__)

__version__ = "2.1.0"


@pytest.fixture(scope="session")
def docker_client() -> docker.DockerClient:
    return docker.from_env()


@pytest.fixture(scope="session")
def free_image_tag(docker_client: docker.DockerClient) -> Generator[str, None, None]:
    """
    This fixture ensures that we have a tag that we can use to build our image
    and that the image will be deleted once we are done with it.
    """
    new_id = str(uuid.uuid4()) + ":tmp"

    try:
        docker_client.images.remove(new_id)
    except ImageNotFound:
        pass

    yield new_id

    try:
        docker_client.images.remove(new_id)
    except ImageNotFound:
        pass


@pytest.fixture(scope="session")
def nfv_test_api_image(docker_client: docker.DockerClient, free_image_tag: str) -> Generator[images.Image, None, None]:
    """
    This fixture builds a container image containing the nfv-test-api server.
    """
    try:
        docker_client.images.build(
            path=os.path.realpath(os.path.join(__file__, "../../..")),
            rm=True,
            tag=free_image_tag,
        )
    except docker.errors.BuildError as e:
        # Ensure that the build log is outputted on failure to allow troubleshooting the issue
        LOGGER.error("Docker build log:\n%s", e.build_log)
        raise e

    image = docker_client.images.get(free_image_tag)
    assert isinstance(image, images.Image)
    return image


@pytest.fixture(scope="function")
def nfv_test_api_instance(
    docker_client: docker.DockerClient, nfv_test_api_image: images.Image
) -> Generator[containers.Container, None, None]:
    """
    This fixture create and starts a container running the nfv-test-api and returns it api object.
    """
    container = docker_client.containers.run(
        image=nfv_test_api_image.id,
        remove=True,
        detach=True,
        privileged=True,
    )
    assert isinstance(container, containers.Container)

    # Waiting for the container to be started
    while container.status == "created":
        time.sleep(1)
        container_info = docker_client.containers.get(container.id)
        assert isinstance(container_info, containers.Container)
        container = container_info

    yield container

    container.kill()
    try:
        container.wait(condition="removed")
    except NotFound:
        # The container is already removed
        pass


@pytest.fixture(scope="function")
def nfv_test_api_endpoint(nfv_test_api_instance: containers.Container) -> str:
    """
    This fixture waits for the api to be reachable then returns the url it can be reached at.
    """
    # Waiting for the server to be up
    container_ip = ip_address(nfv_test_api_instance.attrs["NetworkSettings"]["IPAddress"])
    api = f"http://{container_ip}:8080/api/v2"

    max_attempts = 10
    while requests.get(f"{api}/docs", timeout=0.5).status_code != 200 and max_attempts > 0:
        time.sleep(1)
        max_attempts -= 1

    if max_attempts == 0:
        raise RuntimeError("Failed to start server")

    return api


@pytest.fixture(scope="function")
def nfv_test_api_logs(nfv_test_api_instance: containers.Container, nfv_test_api_endpoint: str) -> Generator[None, None, None]:
    """
    Starts a thread that will log all the logs from the container
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
