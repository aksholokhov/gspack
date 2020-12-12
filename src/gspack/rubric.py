import os
import json
import shutil
from zipfile import ZipFile
import pickle

from gspack.__about__ import __author__, __email__, __supported_platforms__
from gspack.helpers import UserFailure, GspackFailure
from gspack.helpers import generate_requirements, get_hint
from gspack.directories import *


class Rubric:
    def __init__(self,
                 test_suite=None,
                 total_score=10,
                 number_of_attempts=-1,
                 supported_platforms=None,
                 matlab_credentials=None,
                 extra_files=(),
                 test_suite_values=None,
                 verbose=False,
                 **kwargs):
        self.test_suite = test_suite
        self.test_suite_values = test_suite_values
        self.total_score = total_score
        self.number_of_attempts = number_of_attempts
        self.supported_platforms = supported_platforms
        self.matlab_credentials = matlab_credentials
        self.extra_files = extra_files
        self.verbose = verbose

    @staticmethod
    def from_json(rubric_path: Path, verbose=False):
        if not rubric_path.exists() or not rubric_path.is_file():
            raise UserFailure(f"Rubric file does not exist: \n -> {rubric_path}")
        with open(rubric_path, 'r') as f:
            rubric = json.load(f)
        return Rubric.from_dict(rubric, verbose=verbose)

    @staticmethod
    def from_dict(module: dict, verbose=False):
        correct = Rubric.check_rubric_correctness(module, verbose=verbose)
        if correct:
            return Rubric(**module, verbose=verbose)

    @staticmethod
    def check_rubric_correctness(rubric: dict, verbose=False):
        # Checking the correctness of the test suite
        test_suite = rubric.get('test_suite', None)
        if test_suite is None:
            raise UserFailure("No test_suite variable defined in the solution file.")
        if type(test_suite) is not list:
            raise UserFailure(f"test_suite is defined as {type(test_suite)} but it should be list.")
        score_per_test = None
        total_score = rubric.get('total_score', None)
        if total_score is not None:
            try:
                total_score = float(total_score)
            except Exception:
                raise UserFailure("Total score should be a number. Check the type of the total_score variable.")
            score_per_test = total_score / len(test_suite)
        if verbose:
            print("Found the test suite configuration:")
        actual_total_score = 0
        for test in test_suite:
            if (score_per_test is None) ^ (test.get('score', None) is None):
                if test.get('score', None) is None:
                    test['score'] = score_per_test
            else:
                if (test.get('score', None) is None) and (score_per_test is None):
                    raise UserFailure(f"{test['test_name']}: score is missing")
                else:
                    raise UserFailure(
                        f"{test['test_name']}: both total_score and this particular test's score are defined." +
                        f" You need to define either one global score to assign points evenly," +
                        f" or to define all test's scores manually. ")
            actual_total_score += float(test['score'])
            if verbose:
                print(f"-> {test['test_name']}: OK")
        if verbose:
            print("The total number of points is %.2d" % actual_total_score)

        number_of_attempts = rubric.get('number_of_attempts', None)
        if number_of_attempts is not None:
            try:
                number_of_attempts = int(number_of_attempts)
            except Exception:
                raise UserFailure("number_of_attempts should be int.")
            if verbose:
                print(f"Number of attempts: {number_of_attempts}")
        else:
            if verbose:
                print(f"Number of attempts: unlimited.")
            # manually set the unlimited number of attempts

        supported_platforms = rubric.get("supported_platforms", None)
        if supported_platforms is not None:
            if not type(supported_platforms) is list:
                raise UserFailure("supported_platforms should be a list of strings")
            for platform in supported_platforms:
                if platform not in __supported_platforms__:
                    raise UserFailure(f"Unrecognized platform: {platform}")
            if verbose:
                print(f"Supported platforms: {', '.join(supported_platforms)}")

        extra_files = rubric.get("extra_files", None)
        if extra_files is not None:
            if not type(extra_files) is list:
                raise UserFailure("extra_files should be a list of file names"
                                  " located in the same directory as the solution")
        return True

    def fetch_values_for_tests(self, variables: dict):
        if self.test_suite is None:
            raise GspackFailure("Rubric was not initialized properly: test_suite is None.")
        self.test_suite_values = {}
        for test in self.test_suite:
            test_value = variables.get(test["variable_name"], None)
            if test_value is None:
                raise UserFailure(f"{test['test_name']}: variable {test['variable_name']} is set to be checked" +
                                  f" but it's not defined after the solution finishes its execution.")
            self.test_suite_values[test["variable_name"]] = test_value

    def save_to(self, path):
        dict_to_save = {
            "test_suite": self.test_suite,
            "total_score": self.total_score,
            "number_of_attempts": self.number_of_attempts,
            "supported_platforms": self.supported_platforms,
            "extra_files": self.extra_files
        }
        with open(path / RUBRIC_JSON, "w") as f:
            json.dump(dict_to_save, f)
        if self.test_suite_values is not None:
            with open(path / TEST_SUITE_VALUES_FILE, "wb") as f:
                pickle.dump(self.test_suite_values, f)

    def create_archive(self, archive_path: Path):
        if self.verbose:
            print("Generating the archive:")
        program_dir = Path(os.path.dirname(__file__))
        archive_dir = archive_path.parent.absolute()
        try:
            # Copying all the must-have files from the templates (setup.sh, run_autograder, etc)
            os.mkdir(archive_dir / DIST_DIR)

            for file in AUTOGRADER_ARCHVE_FILES:
                full_path = program_dir / TEMPLATES_DIR / file
                if not os.path.exists(full_path):
                    raise GspackFailure(f"-> {file}: the file {full_path} does not exist." +
                                        f" It's likely a gspack installation bug." +
                                        f" You should contact {__author__} ({__email__})" +
                                        f" or post the issue on the project's Github page.")
                shutil.copyfile(full_path, archive_dir / DIST_DIR / file)
                if self.verbose:
                    print(f"-> {file}: OK")

            # pipreqs package scans the solution and generates the list of (non-standard) Python packages used.
            try:
                if self.verbose:
                    print("Generating requirements for your solution:")
                generate_reqs_output = generate_requirements(archive_dir,
                                                             output_path=archive_dir / DIST_DIR / REQUIREMENTS_FILE)
                if not generate_reqs_output[0].startswith(b"INFO: Successfully saved"):
                    raise GspackFailure(generate_reqs_output[0])
                if self.verbose:
                   print(f"-> {REQUIREMENTS_FILE}: OK")

            except Exception as e:
                raise e

            config = {}

            if "matlab" in self.supported_platforms:
                # Adding MATLAB support
                if self.matlab_credentials is None:
                    raise UserFailure("MATLAB support is requested but no matlab_credentials path is provided")
                if self.verbose:
                    print("Adding MATLAB support...")

                # Checking that all the necessary files are in the credentials folder
                matlab_folder_path = Path(self.matlab_credentials).expanduser().absolute()
                if not matlab_folder_path.exists() or not matlab_folder_path.is_dir():
                    raise UserFailure(
                        f"matlab_credentials: the directory {matlab_folder_path} does not exist" +
                        f" or it's not a directory.")

                for file in MATLAB_FILES:
                    if not (matlab_folder_path / file).exists():
                        raise UserFailure(f"-> {file}: File {(matlab_folder_path / file).absolute()} does not exist.")
                    shutil.copyfile(matlab_folder_path / file,
                                    archive_dir / DIST_DIR / file)
                    if self.verbose:
                        print(f"-> {file}: OK")

                # Getting prefix and suffix commands for the run_autograder script, if any
                run_autograder_prefix = ""
                run_autograder_suffix = ""
                if (matlab_folder_path / PROXY_SETTINGS).exists():
                    with open(matlab_folder_path / PROXY_SETTINGS, "r") as proxy_settings_file:
                        proxy_settings = json.load(proxy_settings_file)
                        if proxy_settings['open_tunnel'] is not None:
                            run_autograder_prefix += proxy_settings['open_tunnel']
                        if proxy_settings['close_tunnel'] is not None:
                            run_autograder_suffix += proxy_settings['close_tunnel']

                # Create run_autograder file given the prefix and suffix
                with open(archive_dir / DIST_DIR / RUN_AUTOGRADER_FILE, 'w') as run_autograder_dest:
                    run_autograder_dest.write("#!/usr/bin/env bash \n")
                    if run_autograder_prefix is not None:
                        run_autograder_dest.write(run_autograder_prefix + "\n")
                    with open(program_dir / TEMPLATES_DIR / RUN_AUTOGRADER_FILE, 'r') as run_autograder_src:
                        run_autograder_dest.write(run_autograder_src.read() + "\n")
                    if run_autograder_suffix is not None:
                        run_autograder_dest.write(run_autograder_suffix)
                config["matlab_support"] = 1
                if self.verbose:
                    print("MATLAB support added successfully.", end='\n')

            if "jupyter" in self.supported_platforms:
                config["jupyter_support"] = 1

            # Saving the config.json file
            json.dump(config, open(archive_dir / DIST_DIR / CONFIG_JSON, 'w'))

            # Checking and adding extra files from extra_files list,
            if self.verbose and (len(self.extra_files) > 1):
                print("Find extra files list:")

            for extra_file in self.extra_files:
                if not (archive_dir / extra_file).exists():
                    raise UserFailure(f"{extra_file}: can't find {archive_dir / extra_file}")
                shutil.copyfile(archive_dir / extra_file, archive_dir / DIST_DIR / extra_file)
                if self.verbose:
                    print(f"-> {extra_file}: OK")

            # Saving the test_suite and  as a pickle archive.
            self.save_to(archive_dir / DIST_DIR)

            # Zip all files in DIST directory
            zip_archive = ZipFile(archive_dir / AUTOGRADER_ZIP, 'w')
            for extra_file in os.listdir(archive_dir / DIST_DIR):
                zip_archive.write(archive_dir / DIST_DIR / extra_file, arcname=extra_file)
            zip_archive.close()
            return True
        finally:
            # Deleting the temporary dist directory
            if os.path.exists(archive_dir / DIST_DIR):
                shutil.rmtree(archive_dir / DIST_DIR)
