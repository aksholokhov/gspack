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
from gspack.directories import TEST_SUITE_VALUES_FILE, RESULTS_JSON
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
    """
    Wrapper function which is called when gsgrade_gradescope is called from the terminal.
    It does not take any parameters since Environment is created with Gradescope server organization
    in mind.

    :return: 0 (zero) if everything goes okay, otherwise -1
    """
    return run_grader(Environment.from_gradescope())

def grade_on_fake_gradescope(gs_home_dir_override):
    return run_grader(Environment.from_gradescope(gs_home_dir_override=gs_home_dir_override))


@click.command(
    help="Grades solution given solution and rubric"
)
@click.version_option(
    version=__version__
)
@click.argument(
    "submission_path",
)
@click.argument(
    "rubric_path",
)
def grade_locally_from_terminal(submission_path, rubric_path):
    """
    Wrapper function which is called when gsgrade is called from the terminal.

    :param submission_path: path to the submission's file
    :param rubric_path: path to the rubric's JSON file.
    :return: 0 (zero) if everything goes okay, otherwise -1
    """
    return grade_locally(submission_path, rubric_path)


def grade_locally(submission_path, rubric_path):
    """
    Grades solution assuming grading outside of a Gradescope server. Meant to be used for
    debugging.

    :param submission_path: path to the submission's file
    :param rubric_path: path to the rubric's JSON file.
    :return: 0 (zero) if everything goes okay, otherwise -1
    """
    submission_path_absolute = Path(submission_path).absolute()
    rubric_path_absolute = Path(rubric_path).absolute()
    environment = Environment(
        submission_path=submission_path_absolute,
        submission_dir=submission_path_absolute.parent,
        rubric_path=rubric_path_absolute,
        test_values_path=rubric_path_absolute.parent / TEST_SUITE_VALUES_FILE,
        results_path=submission_path_absolute.parent / RESULTS_JSON
    )
    return run_grader(environment)


def run_grader(environment: Environment):
    """
    Contains high-level grading logic. Navigates the outer world via `environment`.

    :param environment: An instance of Environment class
    :return: 0 (zero) if everything goes okay, otherwise -1
    """
    try:
        # Load a rubric from a JSON file
        rubric = Rubric.from_json(environment.rubric_path)
        # Read true variables for the rubric's variables and attaches them to the rubric
        with open(environment.test_values_path, 'rb') as f:
            rubric.test_suite_values = pickle.load(f)
        # Environment needs some extra information to the rubric to write results correctly.
        environment.max_number_of_attempts = rubric.number_of_attempts
        environment.max_score = rubric.total_score
        # Identify the main submission file's name.
        submission_file_path = get_submission_file_path(environment.submission_dir,
                                                        main_file_name=rubric.main_file_name)
        # Copy extra files, if any, to the submission's directory
        for extra_file in rubric.extra_files:
            shutil.copyfile(environment.rubric_path.parent / extra_file, environment.submission_dir / extra_file)
        # Initialize an Executor and execute the submission file
        executor = Executor(supported_platforms=rubric.supported_platforms,
                            matlab_config=rubric.matlab_config)
        platform, submission_variables = executor.execute(submission_file_path)
        # Generates grading results based on rubric, true variables, and submission variables.
        results = get_grades(rubric, platform, submission_variables)
        # Write down results
        environment.write_results(results=results)
        return 0
    except Exception as e:
        # If, at any point above, something goes wrong,
        # write the result with error details
        environment.write_exception(exception=e)
        return -1


# TODO why do we have a submission_path on the environment if we're just going
# to ignore it and do this?
def get_submission_file_path(submission_dir: Path, main_file_name=None):
    """
    Find the student's main submission file and figure out the language by the file's extension.
    Also checks that all student's files are readable.

    :param submission_dir: Directory with the student's submission
    :param main_file_name: Name of the main file from the rubric.
    :return: tuple: path to the main submission's file and its language
    """
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
                raise GspackFailure(f"Gradescope is unable to read your file: \n {str(e)} \n" +
                                    f"This might happen if your file is damaged or improperly encoded (not in UTF-8)")
            submission_files.append(submission_dir / f)
        else:
            continue

    if len(submission_files) == 0:
        raise GspackFailure("No student solution files found. Check that you submitted either .m files or .py files.")

    main_file = None
    if main_file_name is not None:
        # Checks whether one and only one file matches the main file's name from the rubric
        # in the submission's directory
        for file in submission_files:
            if file.stem == main_file_name:
                if main_file is not None:
                    raise GspackFailure(f"More than one file matches the main file's name" +
                                        f" ({main_file_name}): {main_file} and {file}")
                main_file = file

        if main_file is None:
            raise UserFailure(f"File with the name {main_file_name} is not found. Check that you named your " +
                              f"main file properly.")
    else:
        # If no `main_file_name` is provided then we only check that there is only one file in
        # the submission directory
        if len(submission_files) > 1:
            raise GspackFailure("You should have submitted one file, but you submitted many: \n " +
                                "\n".join([str(f) for f in submission_files]))
        main_file = submission_files[0]
    return main_file


def get_grades(rubric: Rubric, platform: str, solution: dict):
    """
    Grade student's solution results

    :param rubric: An initialized instance of Rubric with `test_suite_values` attached
    :param platform: Solution's platform. Does not affect grades, only used for getting
                    language-specific hints.
    :param solution: variables from student's submission
    :return: results -- dictionary obeying Gradescope formatting for results.json if everything goes okay,
                    otherwise raises an error.
    """

    # Prepare an empty dictionary for results
    results = {"output": "", "score": 0, "tests": [], "extra_data": {"success": True, "pretest": False}}

    total_score = 0

    if rubric.test_suite is None:
        raise GspackFailure("Rubric is not initialized properly: test_suite is None")
    if rubric.test_suite_values is None:
        raise GspackFailure("Rubric's values are not attached. Call .fetch_values_for_tests() beforehand.")

    # Iterate over tests in the rubric and compare their values from `rubric.test_suite_values`
    # with the ones from the student submission
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

        # Get student's answer and simplify its type, if possible
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
        # if it happens then it's an error which is a result of a bug in gspack which happened when
        # the rubric was created, so the whole process should be aborted.
        reduced_true_answer = reduce_type(true_answer)

        # Check whether types match
        if not ((type(reduced_answer) == type(reduced_true_answer)) or (
                type(reduced_answer) in (float, int) and (type(reduced_true_answer) in (float, int)))):
            test_result[
                "output"] = (f"Wrong answer type: the type of your variable {test['variable_name']}" +
                             f" is {print_reduced_type(reduced_answer)}, " +
                             f"but it should be a {print_reduced_type(reduced_true_answer)}. ")
            test_result["output"] += get_hint(test, "hint_wrong_type", platform)

            continue

        if (type(reduced_answer) is np.ndarray) or (type(reduced_answer) is float):
            # Check whether dimensions match in case when the answers are arrays
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
            # Check whether there are NaNs in the answer
            if np.isnan(reduced_answer).any():
                test_result["output"] = f"Your variable {test['variable_name']} contains NaNs. "
                test_result["output"] += get_hint(test, "hint_nans", platform)
                continue

            # Check if the answers are close enough
            rtol = float(test.get("rtol", None) or 1e-5)
            atol = float(test.get("atol", None) or 1e-8)
            if not np.allclose(reduced_answer, reduced_true_answer, rtol=rtol, atol=atol):
                test_result["output"] = f"Your answer is not within tolerance from the right answer. "
                test_result["output"] += get_hint(test, "hint_tolerance", platform)
                continue

        # Strings are compared in lower capital.
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
    """
    Attempts to simplify the type of a: brings all numbers and matrices of one element to Python floats,
    and all lists, sets, and NumPy arrays of any type to Numpy arrays of floats, if possible.

    Meant to make 3, 3.0+1e-16, and np.array([3], dtype=double) to be just 3.

    :param a: variable which type needs to be simplified.
    :return: a with a possibly converted type.
    """
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
    """
    Returns a generalized legible name of the type (number, matrix, string).

    :param a: variable which type needs to be called
    :return: string -- name of the type.
    """
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
    """
    Gets language-specific hint from the test, otherwise gets a generic one, if any

    :param test: test from `test_suite`
    :param prefix: name of the hint, like "hint_tolerance"
    :param language: name of the language which the hint is needed for
    :return: string -- hint
    """
    result = "\nHint: "
    if test.get(prefix + "_" + language, None) is not None:
        result += str(test.get(prefix + "_" + language, None))
    elif test.get(prefix, None) is not None:
        result += str(test.get(prefix, None))
    else:
        result = ""
    return result
