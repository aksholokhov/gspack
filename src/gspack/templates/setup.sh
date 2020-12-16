#!/usr/bin/env bash

# Install python
apt-get install -y python python3 python3-pip python3-dev jq git
git clone --branch jupyter https://github.com/aksholokhov/gspack.git
cd gspack || exit
python setup.py install
cd ..
# Install gspack dependencies
pip3 install subprocess32 numpy scipy matplotlib
# Install solution script dependencies
pip3 install -r /autograder/source/requirements.txt

matlab=$(jq '.matlab_support' /autograder/source/config.json)
if [ $matlab = 1 ]; then
  # Set up MATLAB, if needed
  chmod +x /autograder/source/matlab_setup.sh
  /autograder/source/matlab_setup.sh
fi

jupyter=$(jq '.jupyter_support' /autograder/source/config.json)
if [ $jupyter = 1 ]; then
    pip3 install ipython nbformat
fi

echo "Main setup.sh completed"