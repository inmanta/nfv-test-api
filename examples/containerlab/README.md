# Containerlab example

This folder contains a simple containerlab topology which is using the image created in the main README.
The purpose of this lab is to test the creation of bond interface with the API.

## Deployement

Deploy the topology:

```
sudo clab deploy -t topology.clab.yml
```

## Manual setup

The `setup_hosts` script configure the bonding automatically, and assign an ip address for the `bond0` interface on each side.

```
bash setup_hosts
```

## Setup through API

The following instructions should be done for both container `R1` and `R2`.

First go to the following url to access the swagger api:

```
http://CONTAINER_IP:8080/api/v2/docs
```

Then create a new interface for the POST method `/interfaces` with the following parameters:
```
{
  "name": "bond0",
  "parent_dev": null,
  "mtu": 1500,
  "type": "bond",
  "peer": null,
  "slave_interfaces": [
    "eth1", "eth2"
  ]
}
```

You still need to assign an ip address to the `bond0` interface, which can be done with the PATCH method `/interfaces/{name}`.

## Verify the bonding

To check that the bonding is working you can check the content of `/proc/net/bonding/bond0`.

You can also monitor the traffic on one of the interfaces to see if LACP messages are exchanged.

In order to do that, you can use the networking namespace of the container from the host and run tcpdump with one of the interfaces of the container :

```
sudo ip netns exec clab-bonding-R1 tcpdump -i eth1
```

Now, you should see LACP messages.