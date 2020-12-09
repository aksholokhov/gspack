import matlab

import json
import types
import os
import sys
import numbers

import numpy as np
import pickle
import shutil
from pathlib import Path

from executor import Executor, ExecutorFailure, ExecutionIncomplete

# HOME_DIR = Path("/Users/aksh/Storage/repos/gspack/examples/python101/autograder")
HOME_DIR = Path("/autograder")
SOURCE_DIR = HOME_DIR / "source"
SUBMISSION_DIR = HOME_DIR / "submission"
TEST_SUITE_DUMP = "test_suite.dump"
RESULTS_DIR = HOME_DIR / "results"
RESULTS_JSON = "results.json"
CONFIG_JSON = "config.json"
SUBMISSION_METADATA_JSON = "submission_metadata.json"

with open(SOURCE_DIR / CONFIG_JSON) as f:
    config = json.load(f)
if config["MATLAB_support"] == 1:
    MATLAB_SUPPORT = True
else:
    MATLAB_SUPPORT = False
    matlab = None

def matlab2python(a):
    matlab_array_types = (matlab.double,
                          matlab.single,
                          matlab.int8,
                          matlab.int16,
                          matlab.int32,
                          matlab.int64,
                          matlab.uint8,
                          matlab.uint16,
                          matlab.uint32,
                          matlab.uint64
                          )
    if type(a) in matlab_array_types:
        return np.array(a)
    elif type(a) == int or type(a) == float or type(a) == str:
        return a
    else:
        raise ValueError(f"Unknown MATLAB type: {type(a)}")

def dump_results_and_exit(results, keep_previous_maximal_score=True, print_score=True):
    current_score = results.get("score", 0)
    if print_score:
        results['output'] += f"\n Your score for this submission is {current_score:.2f}."
    if keep_previous_maximal_score:
        previous_submissions = submission_metadata['previous_submissions']
        if len(previous_submissions) > 0:
            previous_maximal_score = round(max([float(submission['score']) for submission in previous_submissions]), 2)
            results["score"] = round(max(current_score, previous_maximal_score), 2)
            if current_score < previous_maximal_score:
                results['output'] += f"\n The score is set to your previous maximal score of {previous_maximal_score:.2f}."
            total_achievable_score = round(config.get("total_score", None), 2)
            if total_achievable_score is not None:
                if total_achievable_score <= previous_maximal_score:
                    results['output'] = "\n You already achieved maximum score possible."
                    results['tests'] = []

    with open(RESULTS_DIR / RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=4)
    exit(0)


def reduce_type(a):
    if isinstance(a, numbers.Number):
        return float(a)
    elif isinstance(a, np.ndarray) and a.flatten().shape == (1,):
        return float(a.flatten()[0])
    elif isinstance(a, np.ndarray) or isinstance(a, list) or isinstance(a, set):
        try:
            res = np.array(a, dtype=float)
        except Exception as e:
            print(f"Conversion error to numpy array: {e}. \n Object: {a}")
            res = a
        return res
    else:
        return a

def print_reduced_type(a):
    if isinstance(a, numbers.Number):
        return "number"
    elif isinstance(a, np.ndarray) or isinstance(a, list) or isinstance(a, set):
        try:
            res = np.array(a, dtype=float)
        except Exception as e:
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


if __name__ == '__main__':
    results = {
        "output": "",
        "score": 0
    }

    # Reading submission metadata
    with open(HOME_DIR / SUBMISSION_METADATA_JSON, 'r') as metadata_file:
        submission_metadata = json.load(metadata_file)

    number_of_attempts = config.get("number_of_attempts", None)
    if number_of_attempts is not None:
        number_of_used_attempts = len(submission_metadata['previous_submissions'])
        test_student = False
        try:
            test_student = submission_metadata["users"][0]["name"] == "Test Student"
        except Exception as e:
            print(f"Can't access student's name: {e}")
        if test_student:
            results["output"] += f"Submitted as Test Student (unlimited attempts)"
        else:
            if number_of_used_attempts >= number_of_attempts:
                results["output"] += f"You've already used all {number_of_attempts} allowed attempts."
                dump_results_and_exit(results, print_score=False)
            else:
                results["output"] += f"This is your attempt {number_of_used_attempts + 1} out of {number_of_attempts}. \n"

    # get test suite
    test_suite, extra_files = pickle.load(open(SOURCE_DIR / TEST_SUITE_DUMP, "rb"))

    # copy all extra files to the student's solution folder
    for f in extra_files:
        shutil.copyfile(SOURCE_DIR / f, SUBMISSION_DIR / f)

    # Find the student's solution file and figure out the language by its extension
    student_solution_path = []
    for f in os.listdir(SUBMISSION_DIR):
        if f.endswith(".py") or f.endswith(".ipynb") or f.endswith(".m"):
            try:
                _ = open(SUBMISSION_DIR / f, 'r').read()
                # we don't do anything with the output because at this point we just want to check
                # that the file is readable.
            except Exception as e:
                results["output"] += f"Gradescope is unable to read your submission file: \n {str(e)} \n" \
                                     f"This might happen if your file is damaged or improperly encoded (not in UTF-8)"
                dump_results_and_exit(results)
            student_solution_path.append(SUBMISSION_DIR / f)
        else:
            continue

    if len(student_solution_path) == 0:
        results[
            "output"] += "No student solution files found. Check that you submitted either .m files or .py files."
        dump_results_and_exit(results)

    # execute student's solution
    executor = Executor(["python", "matlab"], matlab_settings={
        "nargout": len(test_suite)+1,
        "matlab_use_template": True
    })
    try:
        language, student_solution_output = executor.execute(student_solution_path[0])
    except ExecutionIncomplete as e:
        results["output"] = f"Execution failed: {e}"
        dump_results_and_exit(results, print_score=True)
    except Exception as e:
        results["output"] = f"Execution failed for an unusual reason: {str(e)}. \n Please contact your instructor for assistance."
        dump_results_and_exit(results, print_score=False)

    # Pull gradable variables out of student's solution
    student_answers_dict = {}
    if language == "python" or language == "jupyter":
        for test in test_suite:
            answer_value = student_solution_output.get(test["variable_name"], None)
            if answer_value is None:
                results[
                    "output"] += f"Variable {test['variable_name']} (and maybe others) is not assigned in your solution."
                dump_results_and_exit(results)
            else:
                student_answers_dict[test["variable_name"]] = answer_value
    elif language == "matlab":
        for v, test in zip(student_solution_output[1:], test_suite):
            student_answers_dict[test["variable_name"]] = matlab2python(v)

    # Grade student's solution results
    results["tests"] = []
    total_score = 0
    for i, test in enumerate(test_suite):
        true_answer = test["value"]
        test_result = {
            "name": f"{i + 1}. {test['test_name']}",
            "score": 0,
            "visibility": "visible"
        }

        if test.get("description", None) is not None:
            test_result["name"] += f": {test['description']}"

        results["tests"].append(test_result)
        answer = student_answers_dict.get(test["variable_name"], None)
        if answer is None:
            test_result["output"] = (f"Variable {test['variable_name']} is not defined in your solution file. " +
                                     get_hint(test, "hint_not_defined", language))
            continue

        reduced_answer = reduce_type(answer)
        reduced_true_answer = reduce_type(true_answer)

        if not ((type(reduced_answer) == type(reduced_true_answer)) or (
                type(reduced_answer) in (float, int) and (type(reduced_true_answer) in (float, int)))):
            test_result[
                "output"] = f"Wrong answer type: the type of your variable {test['variable_name']} is {print_reduced_type(reduced_answer)}, " \
                            f"but it should be {print_reduced_type(reduced_true_answer)}. "
            test_result["output"] += get_hint(test, "hint_wrong_type", language)

            continue
        if (type(reduced_answer) is np.ndarray) or (type(reduced_answer) is float):
            if (type(reduced_answer) is np.ndarray) and (type(reduced_true_answer) is np.ndarray):
                if reduced_answer.shape != reduced_true_answer.shape:
                    test_result[
                        "output"] = f"Wrong dimensions: the shape of your variable {test['variable_name']} is {reduced_answer.shape}, " \
                                    f"but it should be {reduced_true_answer.shape}. "
                    test_result["output"] += get_hint(test, "hint_wrong_size", language)
                    continue

                if reduced_answer.dtype != reduced_true_answer.dtype:
                    test_result[
                        "output"] = f"Wrong data type of the array: the data type of your array {test['variable_name']} is {reduced_answer.dtype}, " \
                                    f"but it should be {reduced_true_answer.dtype}. "
                    test_result["output"] += get_hint(test, "hint_wrong_type", language)
                    continue

            if np.isnan(reduced_answer).any():
                test_result["output"] = f"Your variable {test['variable_name']} contains NaNs. "
                test_result["output"] += get_hint(test, "hint_nans", language)
                continue

            rtol = test.get("rtol", None) or 1e-5
            atol = test.get("atol", None) or 1e-8
            if not np.allclose(reduced_answer, reduced_true_answer, rtol=rtol, atol=atol):
                test_result["output"] = f"Your answer is not within tolerance from the right answer. "
                test_result["output"] += get_hint(test, "hint_tolerance", language)
                continue

        elif type(reduced_answer) == str:
            if not reduced_answer.lower().strip() == reduced_true_answer.lower().strip():
                test_result["output"] = f"Your answer does not match the right answer. "
                continue

        test_result["output"] = "Correct."
        test_result["score"] = test["score"]
        total_score += test["score"]
    results["score"] = total_score
    dump_results_and_exit(results)
