# NFV Test API

This package offers a server that creates network namespaces and places interface into these network namespaces. Through the API it is possible to:
- create single and double tagged network interfaces
- set interface state and mtu
- configure ipv4 and ipv6 addresses on (sub)interfaces
- send a ping from a network namespace

This API can be used to automate testing of network service deployments.

The process requires iproute2 with full json support (>=4.15) and needs to run as root.

For testing purposes the service can also be started with the simulate option. The API will then use the configuration in the config file to create API responses without actually making changes to the system. In simulation mode, only a ping to 1.1.1.1 will return a result.