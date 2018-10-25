#!/usr/bin/env bash

. .venv/bin/activate
./report.py $@
deactivate
