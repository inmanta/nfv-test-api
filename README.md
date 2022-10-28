# NFV Test API

This package offers a server that creates network namespaces and places interface into these network namespaces. Through the API it is possible to:
- create single and double tagged network interfaces
- set interface state and mtu
- configure ipv4 and ipv6 addresses on (sub)interfaces
- send a ping from a network namespace

This API can be used to automate testing of network service deployments.

The process requires iproute2 with full json support (>=4.15) and needs to run as root.

For testing purposes the service can also be started with the simulate option. The API will then use the configuration in the config file to create API responses without actually making changes to the system. In simulation mode, only a ping to 1.1.1.1 will return a result.

The test api works with python 3.9, python 3.10 is not supported.

## Installation

Clone the source:

```
git clone https://github.com/inmanta/nfv-test-api
cd nfv-test-api
```

Create a new virtual env for this service and activate it:

```
python3 -m venv env
source ./env/bin/activate
```

or (if you have virtualenvwrapper)

```
mkvirtualenv -p 3.9 env
workon env
```

Install poetry

```
pip install poetry
```

Install all dependencies and the project:

```
poetry install
```

## Start the server

### Either start the server directly on your host

```
python3 -m nfv_test_api.main --config config.yaml
```

You can see the swagger interface at this url :

```
http://0.0.0.0:8080/api/v2/docs
```

### Or start the server within container

We first need to build the docker image (make sure your current directory is the root of the repo, where the dockerfile is located):

```
sudo docker build -t nfv-test-api .
```

To run a container with the image, make sure you use the privileged flag to be able to use all the functionalities of the container:

```
sudo docker run -d --name client --privileged nfv-test-api
```

The server will automatically start with the container.

To get the ip address of the container :

```
docker inspect client -f "{{ .NetworkSettings.Networks.bridge.IPAddress }}"
```

You can also use the image with containerlab as done in the `examples/containerlab` folder.

## Use the testing fixtures somewhere else

The package contains on the side of the server source, a few helper fixtures, in the package named `pytest_nfv_test_api`.  To install all the dependencies required by this package, install the `nfv-test-api` python package with the `pytest` extra option:
```
pip install nfv-test-api[pytest]
```
