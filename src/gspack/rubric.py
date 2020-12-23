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

import json
import pickle
from itertools import chain

from gspack.directories import *
from gspack.helpers import UserFailure, GspackFailure
from gspack.helpers import all_supported_platforms


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
                 main_file_name=None,
                 requirements=None,
                 **kwargs):
        self.test_suite = test_suite
        self.test_suite_values = test_suite_values
        self.total_score = round(total_score, 2)
        self.number_of_attempts = number_of_attempts
        self.supported_platforms = supported_platforms
        self.matlab_credentials = matlab_credentials
        self.extra_files = extra_files
        self.verbose = verbose
        self.main_file_name = main_file_name
        self.requirements = requirements
        if "matlab" in self.supported_platforms:
            self.matlab_config = {
                "variables_to_take": [test["variable_name"] for test in test_suite]
            }
        else:
            self.matlab_config = None

    @staticmethod
    def from_json(rubric_path: Path, verbose=False, **kwargs):
        if not rubric_path.exists() or not rubric_path.is_file():
            raise UserFailure(f"Rubric file does not exist: \n -> {rubric_path}")
        with open(rubric_path, 'r') as f:
            try:
                rubric = json.load(f)
            except json.JSONDecodeError as e:
                raise UserFailure(f"Rubric file can not be loaded. Error:\n{e}\n" +
                                  "Make sure the path is right and the are no typos in JSON syntax.")
        return Rubric.from_dict(rubric, verbose=verbose, **kwargs)

    @staticmethod
    def from_dict(module: dict, verbose=False, **kwargs):
        correct = Rubric.check_rubric_correctness(module, verbose=verbose, **kwargs)
        if correct:
            return Rubric(**module, verbose=verbose)

    @staticmethod
    def check_rubric_correctness(rubric: dict, verbose=False, solution_platform=None, **kwargs):
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
                    raise UserFailure(f"{test['test_name']}: score is missing and total_score is not defined." +
                                      " You need to either define scores for each test or define total_score.")
                else:
                    score_from_rubric = float(test['score'])
                    if abs(score_from_rubric - score_per_test) > 1e-2:
                        raise UserFailure(
                            f"{test['test_name']}: score for this test is not consistent with total_score:" +
                            f" {score_from_rubric:.2f} vs {score_per_test:.2f} ({total_score}/{len(test_suite)})."
                            f" You need to define either one global score to assign points evenly," +
                            f" or to define all test's scores manually. When you do both make sure they're consistent.")
            actual_total_score += float(test['score'])
            if verbose:
                print(f"-> {test['test_name']}: OK")
        if verbose:
            print(f"The total number of points is {actual_total_score:.0f}.")
        rubric["total_score"] = actual_total_score

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
                if platform not in all_supported_platforms.keys():
                    raise UserFailure(f"Unrecognized platform: {platform}")
        else:
            if solution_platform is not None:
                supported_platforms = [solution_platform, ]
            else:
                raise GspackFailure("Neither supported_platforms nor solution's platform is provided.")
        rubric["supported_platforms"] = supported_platforms
        if verbose:
            print(f"Supported platforms: {', '.join(supported_platforms)}")

        main_file_name = rubric.get("main_file_name", None)
        if main_file_name is not None:
            if verbose:
                print(f"Main file's name: {main_file_name}" +
                      f"[{';'.join(chain(*[all_supported_platforms[platform] for platform in supported_platforms]))}]")

        extra_files = rubric.get("extra_files", None)
        if extra_files is not None:
            if not type(extra_files) is list:
                raise UserFailure("extra_files should be a list of file names"
                                  " located in the same directory as the solution")

        requirements = rubric.get("requirements", None)
        if requirements is not None:
            if not type(requirements) is list:
                raise UserFailure("requirements variables should be a list of package names")

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
            "extra_files": self.extra_files,
            "main_file_name": self.main_file_name,
        }
        with open(path / RUBRIC_JSON, "w") as f:
            json.dump(dict_to_save, f)
        if self.test_suite_values is not None:
            with open(path / TEST_SUITE_VALUES_FILE, "wb") as f:
                pickle.dump(self.test_suite_values, f)
