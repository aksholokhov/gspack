#!/usr/bin/env bash

python3.7 -m pip uninstall -y gspack
git clone https://github.com/aksholokhov/gspack
python3.7 setup.py develop