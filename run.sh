#!/bin/bash

cd $(dirname $0)
if [ ! -e env ]; then
   python3 -m venv env
   env/bin/pip install -r requirements.txt
fi
export FLASK_APP=src/main.py
env/bin/python -m flask run --host=0.0.0.0
