from pathlib import Path

DIST_DIR = Path("dist")
TEMPLATES_DIR = Path("templates")
REQUIREMENTS_FILE = "requirements.txt"
RUN_AUTOGRADER_FILE = "run_autograder"
SETUP_FILE = "setup.sh"
RUN_TESTS_FILE = "run_tests.py"
TEST_SUITE_DUMP = "test_suite.dump"
AUTOGRADER_ZIP = "autograder.zip"
CONFIG_JSON = "config.json"
AUTOGRADER_ARCHVE_FILES = [SETUP_FILE, RUN_AUTOGRADER_FILE]

# MATLAB stuff
MATLAB_INSTALL_FILE = "matlab_setup.sh"
RSA_KEY = "id_rsa"
KNOWN_HOSTS_FILE = "known_hosts"
MATLAB_NETWORK_LIC_FILE = "network.lic"
PROXY_SETTINGS = "proxy_settings.json"
MATLAB_FILES = [MATLAB_INSTALL_FILE, RSA_KEY, KNOWN_HOSTS_FILE, MATLAB_NETWORK_LIC_FILE, PROXY_SETTINGS]