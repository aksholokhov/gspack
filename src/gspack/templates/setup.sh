#!/usr/bin/env bash

# Install python
apt-get install -y python python3 python3-pip python3-dev jq
# Install gspack dependencies
pip3 install subprocess32
# Install solution script dependencies
pip3 install -r /autograder/source/requirements.txt

matlab=$(jq '.MATLAB_support' /autograder/source/config.json)
if [ $matlab = 1 ]; then
  # Set up MATLAB, if needed
  chmod +x /autograder/source/matlab_setup.sh
  /autograder/source/matlab_setup.sh
fi

echo "Main setup.sh completed"