#!/usr/bin/env bash

# Install python
apt-get install -y python python3 python3-pip python3-dev
# Install gspack dependencies
pip3 install subprocess32
# Install solution script dependencies
pip3 install -r /autograder/source/requirements.txt

# Set up MATLAB, if needed
# chmod +x /autograder/source/matlab_setup.sh
# /autograder/source/matlab_setup.sh

# echo "Main setup.sh completed"