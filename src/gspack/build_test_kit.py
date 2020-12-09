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


import subprocess
import os.path
from pathlib import Path
import types
import shutil
from zipfile import ZipFile
import pickle
import click
import json

from gspack.__about__ import __author__, __email__, __version__

DIST_DIR = Path("dist")
TEMPLATES_DIR = Path("templates")
REQUIREMENTS_FILE = "requirements.txt"
RUN_AUTOGRADER_FILE = "run_autograder"
SETUP_FILE = "setup.sh"
RUN_TESTS_FILE = "run_tests.py"
TEST_SUITE_DUMP = "test_suite.dump"
AUTOGRADER_ZIP = "autograder.zip"
CONFIG_JSON = "config.json"
AUTOGRADER_ARCHVE_FILES = [SETUP_FILE, RUN_TESTS_FILE, RUN_AUTOGRADER_FILE]

# MATLAB stuff
MATLAB_INSTALL_FILE = "matlab_setup.sh"
RSA_KEY = "id_rsa"
KNOWN_HOSTS_FILE = "known_hosts"
MATLAB_NETWORK_LIC_FILE = "network.lic"
PROXY_SETTINGS = "proxy_settings.json"
MATLAB_FILES = [MATLAB_INSTALL_FILE, RSA_KEY, KNOWN_HOSTS_FILE, MATLAB_NETWORK_LIC_FILE, PROXY_SETTINGS]


def generate_requirements(filepath, output_path):
    process = subprocess.Popen(["pipreqs", "--savepath", f"{output_path}", f"{filepath}"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    return process.communicate()


def generate_solution(solution_path):
    # Reading the solution's file
    if not os.path.exists(solution_path):
        print(f"The file {os.path.abspath(solution_path)} does not exists")
        return False
    print("Found the solution file:")
    solution_code = open(solution_path, 'r').read()
    print(f"-> {os.path.abspath(solution_path)}")
    # Setting up a new Python module in real-time, and executing the solution code in that module
    # to get the variables values
    solution_module_name = os.path.basename(solution_path)
    solution_module = types.ModuleType(solution_module_name)
    solution_module.__file__ = os.path.abspath(solution_path)
    try:
        mydir = os.getcwd()
        os.chdir(solution_path.parent)
        exec(solution_code, solution_module.__dict__)
        os.chdir(mydir)
    except Exception as e:
        print("Error happened while executing the solution file:")
        print(e)
        return False

    # Checking the correctness of the test suite
    if not hasattr(solution_module, 'test_suite'):
        print("No test_suite variable defined in the solution file.")
        return False
    test_suite = solution_module.test_suite
    if type(test_suite) is not list:
        print(f"test_suite is defined as {type(test_suite)} but it should be list.")
        return False
    score_per_test = None
    total_score = None
    if hasattr(solution_module, 'total_score'):
        total_score = solution_module.total_score
        try:
            total_score = float(total_score)
        except Exception as e:
            print("Total score should be a number. Check the type of the total_score variable.")
        score_per_test = total_score / len(test_suite)

    print("Found the test suite configuration:")
    actual_total_score = 0
    for test in test_suite:
        if not hasattr(solution_module, test['variable_name']):
            print(f"-> {test['test_name']}: ERROR: variable {test['variable_name']} is set to be checked"
                  f" but it's not defined after the solution finishes its execution.")
            return False
        if (score_per_test is None) ^ (test.get('score', None) is None):
            test["value"] = solution_module.__getattribute__(test["variable_name"])
            if test.get('score', None) is None:
                test['score'] = score_per_test
        else:
            if (test.get('score', None) is None) and (score_per_test is None):
                print(f"-> {test['test_name']}: ERROR: score is missing")
                return False
            else:
                print(f"-> {test['test_name']}: ERROR: both total_score and this particular test's score are defined."
                      f"You need to define either one global score to assign points evenly,"
                      f" or to define all test's scores manually. ")
                return False
        actual_total_score += float(test['score'])
        print(f"-> {test['test_name']}: OK")
    # Generating the auto grader archive
    print("The total number of points is %.2d" % actual_total_score)
    print("The test_suite looks good. Generating the archive:")
    config = {
        "MATLAB_support": 0,
    }
    program_dir = Path(os.path.dirname(__file__))
    solution_dir = Path(solution_path).parent.absolute()
    try:
        # Copying all the must-have files from the templates (setup.sh, run_autograder, etc)
        os.mkdir(solution_dir / DIST_DIR)
        for file in AUTOGRADER_ARCHVE_FILES:
            full_path = program_dir / TEMPLATES_DIR / file
            if not os.path.exists(full_path):
                print(f"-> {file}: the file {full_path} does not exist. It's likely a gspack installation bug."
                      f" You should contact {__author__} ({__email__}) or post the issue on the project's Github page.")
                return False
            shutil.copyfile(full_path, solution_dir / DIST_DIR / file)
            print(f"-> {file}: OK")
        # pipreqs package scans the solution and generates the list of (non-standard) Python packages used.
        try:
            print("Generating requirements for your solution:")
            generate_reqs_output = generate_requirements(solution_dir, output_path=solution_dir / DIST_DIR / REQUIREMENTS_FILE)
            print(generate_reqs_output[0])
        except Exception as e:
            print("Generating requirements for your solution: FAILED with the error:")
            print(e)
            return False

        run_autograder_prefix = None
        run_autograder_suffix = None
        run_tests_py_prefix = None
        # Adding MATLAB support
        if hasattr(solution_module, 'matlab_credentials'):
            matlab = True
            print("Adding MATLAB support...")
            # Checking that all the necessary files are in the credentials folder
            matlab_folder_path = Path(solution_module.matlab_credentials).expanduser().absolute()
            if not matlab_folder_path.exists() or not matlab_folder_path.is_dir():
                print(
                    f"matlab_credentials: the directory {matlab_folder_path} does not exist"
                    f" or it's not a directory.")
                matlab = False
            else:
                for file in MATLAB_FILES:
                    if not os.path.exists(matlab_folder_path / file):
                        print(f"-> {file}: File {(matlab_folder_path / file).absolute()} does not exist.")
                        matlab = False
                    shutil.copyfile(matlab_folder_path / file,
                                    solution_dir / DIST_DIR / file)
                    print(f"-> {file}: OK")

                # Setting prefix for the run_tests.py to import matlab.
                # The reason why this is implemented in such a junky way is
                # because the "import matlab.engine" should be at the very
                # first line of the file, otherwise it crashes with some internal
                # library flags erros
                run_tests_py_prefix = "import matlab.engine \n"

                # Getting prefix and suffix commands for the run_autograder script, if any
                if (matlab_folder_path / PROXY_SETTINGS).exists():
                    with open(matlab_folder_path / PROXY_SETTINGS, "r") as proxy_settings_file:
                        proxy_settings = json.load(proxy_settings_file)
                        if proxy_settings['open_tunnel'] is not None:
                            run_autograder_prefix = proxy_settings['open_tunnel']
                        if proxy_settings['close_tunnel'] is not None:
                            run_autograder_suffix = proxy_settings['close_tunnel']

            if matlab:
                if hasattr(solution_module, 'matlab_use_template'):
                    config['matlab_use_template'] = solution_module.matlab_use_template
                    if solution_module.matlab_use_template:
                        print("MATLAB is configured to be used with a template.")
                else:
                    config['matlab_use_template'] = False
                config["MATLAB_support"] = 1
                print("MATLAB support added successfully.", end='\n')
            else:
                print("MATLAB support was NOT added, see the errors above.", end='\n')

        # Create run_tests py given the prefix
        with open(solution_dir / DIST_DIR / RUN_TESTS_FILE, 'w') as run_tests_dst:
            if run_tests_py_prefix is not None:
                run_tests_dst.write(run_tests_py_prefix + "\n")
            with open(program_dir / TEMPLATES_DIR / RUN_TESTS_FILE, 'r') as run_tests_src:
                run_tests_dst.write(run_tests_src.read())

        # files to take
        files_to_take = ["run_grader.py", "executor.py", "matlab_executor.py", "helpers.py"]
        for f in files_to_take:
            with open(solution_dir / DIST_DIR / f, 'w') as run_tests_dst:
                if run_tests_py_prefix is not None:
                    run_tests_dst.write(run_tests_py_prefix + "\n")
                with open(program_dir / f, 'r') as run_tests_src:
                    run_tests_dst.write(run_tests_src.read())

        # Create run_autograder file given the prefix and suffix
        with open(solution_dir / DIST_DIR / RUN_AUTOGRADER_FILE, 'w') as run_autograder_dest:
            run_autograder_dest.write("#!/usr/bin/env bash \n")
            if run_autograder_prefix is not None:
                run_autograder_dest.write(run_autograder_prefix + "\n")
            with open(program_dir / TEMPLATES_DIR / RUN_AUTOGRADER_FILE, 'r') as run_autograder_src:
                run_autograder_dest.write(run_autograder_src.read() + "\n")
            if run_autograder_suffix is not None:
                run_autograder_dest.write(run_autograder_suffix)

        # Checking and adding extra files from extra_files list,
        if hasattr(solution_module, 'extra_files'):
            extra_files = solution_module.extra_files
            print("Find extra files list:")
            for extra_file in extra_files:
                if os.path.exists(solution_path.parent / extra_file):
                    shutil.copyfile(solution_path.parent / extra_file, solution_dir / DIST_DIR / extra_file)
                    print(f"-> {extra_file}: OK")
                else:
                    print(f"-> {extra_file}: can't find {solution_path.parent / extra_file}")
        else:
            extra_files = []

        # Checking if the number of submission attempts is set to be limited
        config['total_score'] = actual_total_score
        if hasattr(solution_module, 'number_of_attempts'):
            config['number_of_attempts'] = solution_module.number_of_attempts
            print(f"Number of attempts: {solution_module.number_of_attempts}")
        else:
            print(f"Number of attempts: unlimited.")

        # Saving the test_suite and list of extra files as a pickle archive.
        # The reason why it's not in the config file is because it contains values
        # of the target variables too.
        pickle.dump((test_suite, extra_files), open(solution_dir / DIST_DIR / TEST_SUITE_DUMP, "wb"))
        # Saving the config.json file
        json.dump(config, open(solution_dir / DIST_DIR / CONFIG_JSON, 'w'))
        # Zip all files in DIST directory
        zip_archive = ZipFile(solution_dir / AUTOGRADER_ZIP, 'w')
        for extra_file in os.listdir(solution_dir / DIST_DIR):
            zip_archive.write(solution_dir / DIST_DIR / extra_file, arcname=extra_file)
        zip_archive.close()
        return True
    finally:
        # Deleting the temporary dist directory
        if os.path.exists(solution_dir / DIST_DIR):
            shutil.rmtree(solution_dir / DIST_DIR)


@click.command(
    help="Genreates archive for gradescope autograder"
)
@click.version_option(
    version=__version__
)
# TODO: move it to the default argument
@click.option(
    '--solution',
    type=str,
    help="path to the solution file"
)
def create_autograder_from_console(**kwargs):
    create_autograder(**kwargs)


def create_autograder(solution):
    solution_path = Path(solution).absolute()
    success = generate_solution(solution_path)
    if success:
        print(f"Archive created successfully: \n-> {solution_path.parent / AUTOGRADER_ZIP}")
    else:
        print("The process is aborted, see the error above.")


if __name__ == "__main__":
    create_autograder(solution="../../examples/python101/hw0_solution.py")
