#     GSPack: Programming Assignment Packager for GradeScope AutoGrader
#     Copyright (C) 2020  Aleksei Sholokhov
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.


from pathlib import Path

DIST_DIR = Path("dist")
TEMPLATES_DIR = Path("templates")
REQUIREMENTS_FILE = "requirements.txt"
RUN_AUTOGRADER_FILE = "run_autograder"
SETUP_FILE = "setup.sh"
RUN_TESTS_FILE = "run_tests.py"
AUTOGRADER_ZIP = "autograder.zip"
CONFIG_JSON = "config.json"
RUBRIC_JSON = "rubric.json"
TEST_SUITE_VALUES_FILE = "test_suite_values.dump"
AUTOGRADER_ARCHIVE_FILES = [SETUP_FILE, RUN_AUTOGRADER_FILE]

# MATLAB stuff
MATLAB_INSTALL_FILE = "matlab_setup.sh"
RSA_KEY = "id_rsa"
KNOWN_HOSTS_FILE = "known_hosts"
MATLAB_NETWORK_LIC_FILE = "network.lic"
PROXY_SETTINGS = "proxy_settings.json"
MATLAB_FILES = [MATLAB_INSTALL_FILE, RSA_KEY, KNOWN_HOSTS_FILE, MATLAB_NETWORK_LIC_FILE, PROXY_SETTINGS]

# Gradescope structure
GS_HOME_DIR = Path("/autograder")
GS_SOURCE_DIR = GS_HOME_DIR / "source"
GS_SUBMISSION_DIR = GS_HOME_DIR / "submission"
GS_RESULTS_DIR = GS_HOME_DIR / "results"
GS_RESULTS_JSON = GS_RESULTS_DIR / "results.json"
GS_SUBMISSION_METADATA_JSON = GS_HOME_DIR / "submission_metadata.json"

TEST_STUDENT_NAME = "Test Student"
TEST_STUDENT_EMAIL = "test_student@gspack.com"
DEFAULT_STUDENT_NAME = "John Smith"
DEFAULT_STUDENT_EMAIL = "john_smith@gspack.com"
