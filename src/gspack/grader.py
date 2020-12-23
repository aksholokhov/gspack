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


import numbers
import os
import pickle
import shutil
from pathlib import Path

import click
import numpy as np

from gspack.__about__ import __version__
from gspack.directories import TEST_SUITE_VALUES_FILE, GS_RESULTS_JSON
from gspack.environment import Environment
from gspack.executor import Executor
from gspack.helpers import UserFailure, GspackFailure, determine_platform
from gspack.rubric import Rubric


@click.command(
    help="Grades submission in Gradescope environment"
)
@click.version_option(
    version=__version__
)
def grade_on_gradescope():
    return run_grader(Environment.from_gradescope())


@click.command(
    help="Grades solution given solution and rubric"
)
@click.argument(
    "submission_path",
)
@click.argument(
    "rubric_path",
)
def grade_locally_from_terminal(submission_path, rubric_path):\
    return grade_locally(submission_path, rubric_path)


def grade_locally(submission_path, rubric_path):
    submission_path_absolute = Path(submission_path).absolute()
    rubric_path_absolute = Path(rubric_path).absolute()
    environment = Environment(
        submission_path=submission_path_absolute,
        submission_dir=submission_path_absolute.parent,
        rubric_path=rubric_path_absolute,
        test_values_path=rubric_path_absolute.parent / TEST_SUITE_VALUES_FILE,
        results_path=submission_path_absolute.parent / GS_RESULTS_JSON.name
    )
    return run_grader(environment)


def run_grader(environment):
    try:
        rubric = Rubric.from_json(environment.rubric_path)
        with open(environment.test_values_path, 'rb') as f:
            rubric.test_suite_values = pickle.load(f)
        environment.max_number_of_attempts = rubric.number_of_attempts
        environment.max_score = rubric.total_score
        submission_file_path = get_submission_file_path(environment.submission_dir,
                                                        main_file_name=rubric.main_file_name)
        for extra_file in rubric.extra_files:
            shutil.copyfile(environment.rubric_path.parent / extra_file, environment.submission_dir / extra_file)
        rubric.matlab_config["variables_to_take"].append("pretest")
        executor = Executor(supported_platforms=rubric.supported_platforms,
                            matlab_config=rubric.matlab_config)
        platform, submission_variables = executor.execute(submission_file_path)
        results = get_grades(rubric, platform, submission_variables)
        environment.write_results(results=results)
    except Exception as e:
        environment.write_results(exception=e)


def get_submission_file_path(submission_dir: Path, main_file_name=None):
    # Find the student's solution file and figure out the language by its extension
    submission_files = []
    if not submission_dir.is_dir():
        raise GspackFailure(f"Not a directory: {submission_dir}")

    for f in os.listdir(submission_dir):
        platform = determine_platform(submission_dir / f)
        if platform is not None:
            try:
                # we don't do anything with the output because at this point we just want to check
                # that the file is readable.
                with open(submission_dir / f, 'r') as f2:
                    _ = f2.read()
            except Exception as e:
                raise UserFailure(f"Gradescope is unable to read your file: \n {str(e)} \n" +
                                  f"This might happen if your file is damaged or improperly encoded (not in UTF-8)")
            submission_files.append(submission_dir / f)
        else:
            continue

    if len(submission_files) == 0:
        raise UserFailure("No student solution files found. Check that you submitted either .m files or .py files.")

    main_file = None
    if main_file_name is not None:
        for file in submission_files:
            if file.stem == main_file_name:
                main_file = file
                break
    else:
        if len(submission_files) > 1:
            raise UserFailure("You should have submitted one file, but you submitted many: \n " +
                              "\n".join([str(f) for f in submission_files]))
        main_file = submission_files[0]
    return main_file


def get_grades(rubric, platform: str, solution: dict):
    # Grade student's solution results
    results = {"output": "", "score": 0, "tests": [], "extra_data": {"success": True, "pretest": False}}
    total_score = 0
    if rubric.test_suite is None:
        raise GspackFailure("Rubric is not initialized properly: test_suite is None")
    if rubric.test_suite_values is None:
        raise GspackFailure("Rubric's values are not attached. Call .fetch_values_for_tests() beforehand.")

    pretest = solution.get("pretest")
    results["extra_data"]["pretest"] = False
    if pretest is not None:
        if not type(pretest) is bool:
            raise UserFailure(f"pretest should be boolean value, but in your submission it's {type(pretest)}")
        if pretest:
            results["extra_data"]["pretest"] = True

    for i, test in enumerate(rubric.test_suite):
        true_answer = rubric.test_suite_values[test["variable_name"]]
        test_result = {
            "name": f"{i + 1}. {test['test_name']}",
            "score": 0,
            "visibility": "visible"
        }

        if test.get("description", None) is not None:
            test_result["name"] += f": {test['description']}"

        results["tests"].append(test_result)
        answer = solution.get(test["variable_name"], None)
        if answer is None:
            test_result["output"] = (f"Variable {test['variable_name']} is not defined in your solution file. " +
                                     get_hint(test, "hint_not_defined", platform))
            continue

        try:
            reduced_answer = reduce_type(answer)
        except GspackFailure:
            # This is a student's failure.
            test_result["output"] = f"Variable {test['variable_name']} has an unrecognized type. "
            continue

        # The error from this one is not captured here because
        # if it happens then it's a gspack failure and
        # it will be handled above
        reduced_true_answer = reduce_type(true_answer)

        if not ((type(reduced_answer) == type(reduced_true_answer)) or (
                type(reduced_answer) in (float, int) and (type(reduced_true_answer) in (float, int)))):
            test_result[
                "output"] = (f"Wrong answer type: the type of your variable {test['variable_name']}" +
                             f" is {print_reduced_type(reduced_answer)}, " +
                             f"but it should be a {print_reduced_type(reduced_true_answer)}. ")
            test_result["output"] += get_hint(test, "hint_wrong_type", platform)

            continue
        if (type(reduced_answer) is np.ndarray) or (type(reduced_answer) is float):
            if (type(reduced_answer) is np.ndarray) and (type(reduced_true_answer) is np.ndarray):
                if reduced_answer.shape != reduced_true_answer.shape:
                    test_result[
                        "output"] = (f"Wrong dimensions: the shape of your variable" +
                                     f" {test['variable_name']} is {reduced_answer.shape}, " +
                                     f"but it should be {reduced_true_answer.shape}. ")
                    test_result["output"] += get_hint(test, "hint_wrong_size", platform)
                    continue

                if reduced_answer.dtype != reduced_true_answer.dtype:
                    test_result[
                        "output"] = (f"Wrong data type of the array: the data type" +
                                     f" of your array {test['variable_name']} is {reduced_answer.dtype}, " +
                                     f"but it should be {reduced_true_answer.dtype}. ")
                    test_result["output"] += get_hint(test, "hint_wrong_type", platform)
                    continue

            if np.isnan(reduced_answer).any():
                test_result["output"] = f"Your variable {test['variable_name']} contains NaNs. "
                test_result["output"] += get_hint(test, "hint_nans", platform)
                continue

            rtol = test.get("rtol", None) or 1e-5
            atol = test.get("atol", None) or 1e-8
            if not np.allclose(reduced_answer, reduced_true_answer, rtol=rtol, atol=atol):
                test_result["output"] = f"Your answer is not within tolerance from the right answer. "
                test_result["output"] += get_hint(test, "hint_tolerance", platform)
                continue

        elif type(reduced_answer) == str:
            if not reduced_answer.lower().strip() == reduced_true_answer.lower().strip():
                test_result["output"] = f"Your answer does not match the right answer. "
                continue

        test_result["output"] = "Correct."
        test_result["score"] = test["score"]
        total_score += test["score"]
    results["score"] = round(total_score, 2)
    return results


def reduce_type(a):
    if isinstance(a, numbers.Number):
        return float(a)
    elif isinstance(a, np.ndarray) and a.flatten().shape == (1,):
        return float(a.flatten()[0])
    elif isinstance(a, np.ndarray) or isinstance(a, list) or isinstance(a, set):
        try:
            res = np.array(a, dtype=float)
        except Exception as e:
            raise GspackFailure(f"Conversion error to numpy array: {e}. \n Object: {a}")
        return res
    else:
        return a


def print_reduced_type(a):
    if isinstance(a, numbers.Number):
        return "number"
    elif isinstance(a, np.ndarray) or isinstance(a, list) or isinstance(a, set):
        try:
            res = np.array(a, dtype=float)
        except ValueError:
            return str(type(a))
        return f"matrix of shape {res.shape}"
    elif isinstance(a, str):
        return "string"
    else:
        return str(type(a))


def get_hint(test, prefix, language):
    result = "\nHint: "
    if test.get(prefix + "_" + language, None) is not None:
        result += str(test.get(prefix + "_" + language, None))
    elif test.get(prefix, None) is not None:
        result += str(test.get(prefix, None))
    else:
        result = ""
    return result
