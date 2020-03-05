#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: workon [namespace]"
  exit 2
fi

sudo ip netns exec $1 bash
