#!/usr/bin/env bash

# Install python
apt-get update
apt-get install -y python python3 python3-pip python3-dev python3.7 jq git
# Install gspack dependencies
python3.7 -m pip install subprocess32 numpy scipy matplotlib
# Install solution script dependencies
python3.7 -m pip install -r /autograder/source/requirements.txt
# Install gspack
git clone https://github.com/aksholokhov/gspack.git
cd gspack || exit
python3.7 setup.py install
cd ..

matlab=$(jq '.matlab_support' /autograder/source/config.json)
if [ $matlab = 1 ]; then
  # Set up MATLAB, if needed
  chmod +x /autograder/source/matlab_setup.sh
  /autograder/source/matlab_setup.sh
fi

jupyter=$(jq '.jupyter_support' /autograder/source/config.json)
if [ $jupyter = 1 ]; then
    python3.7 -m pip install ipython nbformat
fi

echo "Main setup.sh completed"