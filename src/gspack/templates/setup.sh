#!/usr/bin/env bash

# Install python
apt-get install -y python python3 python3.7 python3-pip python3-dev jq
# Install gspack dependencies
python3.7 -m pip install subprocess32 numpy scipy matplotlib
# Install solution script dependencies
python3.7 -m pip install -r /autograder/source/requirements.txt

git clone https://github.com/aksholokhov/gspack
cd gspack || exit
python3.7 setup.py install
cd .. || exit

matlab=$(jq '.matlab_support' /autograder/source/config.json)
if [ $matlab = 1 ]; then
  echo "Adding MATLAB components"
  # Set up MATLAB, if needed
  chmod +x /autograder/source/matlab_setup.sh
  /autograder/source/matlab_setup.sh
fi

jupyter=$(jq '.jupyter_support' /autograder/source/config.json)
if [ $jupyter = 1 ]; then
    echo "Adding Jupyter components"
    python3.7 -m pip install ipython nbformat
fi

echo "Main setup.sh completed"