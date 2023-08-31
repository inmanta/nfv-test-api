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
import pathlib
import typing
import uuid

import docker  # type: ignore
import docker.errors  # type: ignore
import pytest
from docker.models import images  # type: ignore

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def free_image_tag(
    docker_client: docker.DockerClient,
) -> typing.Generator[str, None, None]:
    """
    This fixture ensures that we have a tag that we can use to build our image
    and that the image will be deleted once we are done with it.
    """
    new_id = str(uuid.uuid4()) + ":tmp"

    try:
        docker_client.images.remove(new_id)
    except docker.errors.ImageNotFound:
        pass

    yield new_id

    try:
        docker_client.images.remove(new_id)
    except docker.errors.ImageNotFound:
        pass


@pytest.fixture(scope="session")
def nfv_test_api_image(
    docker_client: docker.DockerClient, free_image_tag: str
) -> images.Image:
    """
    This fixture builds a container image containing the nfv-test-api server.
    """
    try:
        docker_client.images.build(
            path=str(pathlib.Path(__file__).parent.parent),
            tag=free_image_tag,
        )
    except docker.errors.BuildError as e:
        # Ensure that the build log is outputted on failure to allow troubleshooting the issue
        LOGGER.error("Docker build log:\n%s", e.build_log)
        raise e

    image = docker_client.images.get(free_image_tag)
    assert isinstance(image, images.Image)
    return image
