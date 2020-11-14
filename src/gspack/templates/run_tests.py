import json
from pathlib import Path
import pickle
import types
import os
import numpy as np
import shutil

import numbers

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


def execute():
    # Find the student's solution file and figure out the language by its extension
    student_solution_path = []
    for f in os.listdir(SUBMISSION_DIR):
        if f.endswith(".py") or f.endswith(".m"):
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
        results["output"] += "No student solution files found. Check that you submitted either .m files or .py files."
        dump_results_and_exit(results)

    language = None
    if all([str(file).endswith(".py") for file in student_solution_path]):
        language = "python"
    elif all([str(file).endswith(".m") for file in student_solution_path]):
        language = "matlab"
    else:
        results["output"] += f"You need to submit either only .py files or only .m files. " \
                            f"It looks like you submitted a mix of both:" \
                            f"\n ->".join([str(path) for path in student_solution_path])
        dump_results_and_exit(results)

    student_answers = {}
    mydir = os.getcwd()
    os.chdir(SUBMISSION_DIR)

    if language == "python":
        if len(student_solution_path) > 1:
            results["output"] += ("You need to submit only one file, but you submitted multiple: \n ->" +
                                 "\n ->".join([str(path) for path in student_solution_path])
                                 )
            dump_results_and_exit(results)
        student_solution_path = student_solution_path[0]
        solution_code = open(student_solution_path, 'r').read()
        solution_module_name = os.path.basename(student_solution_path)
        solution_module = types.ModuleType(solution_module_name)
        solution_module.__file__ = os.path.abspath(student_solution_path)
        try:
            exec(solution_code, solution_module.__dict__)
        except Exception as e:
            results["output"] += f"Execution failed: \n {str(e)} \n"
            dump_results_and_exit(results)

        for test in test_suite:
            answer_value = solution_module.__dict__.get(test["variable_name"], None)
            if answer_value is None:
                results["output"] += f"Variable {test['variable_name']} (and maybe others) is not assigned in your solution."
                dump_results_and_exit(results)
            else:
                student_answers[test["variable_name"]] = answer_value

    elif language == "matlab":
        if not MATLAB_SUPPORT:
            results["output"] += "MATLAB support is disabled for this assignment, but a MATLAB file is submitted."
            dump_results_and_exit(results)

        # wrap up the MATLAB main body script as a function
        if config.get("matlab_use_template", None) is True:
            if all([file.name != "solution.m" for file in student_solution_path]):
                results["output"] += (f"Your main file should be called solution.m and it should be based on the template provided. \n" +
                                    f"The files you submitted are: \n" +
                                    f"\n ->".join([str(path) for path in student_solution_path]))
                dump_results_and_exit(results)

        else:
            if len(student_solution_path) > 1:
                results["output"] += ("You need to submit only one file, but you submitted multiple: \n ->" +
                                     "\n ->".join([str(path) for path in student_solution_path])
                                     )
                dump_results_and_exit(results)
            student_solution_path = student_solution_path[0]
            solution_code = open(student_solution_path, 'r').read()
            solution_parts = solution_code.split("function ")
            main_script_body = solution_parts[0]
            other_functions = "" if len(solution_parts) == 1 else " ".join(
                ["\nfunction " + s for s in solution_parts[1:]])
            with open(SUBMISSION_DIR / 'solution.m', 'w') as student_file_dst:
                all_variables = ', '.join([test['variable_name'] for test in test_suite])
                prefix = f"function [consoleout, {all_variables}] = solution() \n " \
                         f"[consoleout, {all_variables}] = evalc('student_solution(0)'); \n" \
                         f"end \n" \
                         f"\n" \
                         f"function [{all_variables}] = student_solution(arg) \n "
                postfix = "\nend\n"
                student_file_dst.write(prefix)
                student_file_dst.write(main_script_body)
                student_file_dst.write(postfix)
                student_file_dst.write(other_functions)

        # Execute MATLAB solution file and convert its outputs to python-compartible representation
        try:
            eng = matlab.engine.start_matlab()
        except Exception as e:
            successfully_executed = False
            results["output"] += f"MATLAB failed to start with the following error: \n {e}." \
                                f" Please contact your instructor for assistance."
            dump_results_and_exit(results)
        try:
            output = eng.solution(nargout=len(test_suite) + 1)
            # console_output = output[0]  # decide later what to do with it
            for v, test in zip(output[1:], test_suite):
                student_answers[test["variable_name"]] = matlab2python(v)
        except Exception as e:
            results["output"] += f"Execution failed: \n {str(e)}"
            if str(e) == "MATLAB function cannot be evaluated":
                results["output"] += "\n Check that you suppress all console outputs " \
                                                      "(semicolumn at the end of line), especially in loops."
            elif str(e).endswith(
                    ' (and maybe others) not assigned during call to "solution>student_solution".\n'):
                results["output"] += "\n Check that you defined the aformentioned variable in your solution file."
            dump_results_and_exit(results)
        finally:
            if not config.get("matlab_use_template", None) is True:
                os.remove(SUBMISSION_DIR / 'solution.m')
    else:
        results["output"] = f"Gradescope can not determine the language. \n" \
                            f"Please check that you're submitting either .py files or .m files."
        dump_results_and_exit(results)
    os.chdir(mydir)

    return language, student_answers


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
    elif isinstance(a, np.ndarray):
        if a.flatten().shape == (1,):
            return float(a.flatten()[0])
    elif (isinstance(a, list) or isinstance(a, set)) and len(a) == 1:
          return np.array(a)[0]
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
    elif ((isinstance(a, np.ndarray) and a.flatten().shape == (1,))
          or (isinstance(a, list) and len(a) == 1)
          or (isinstance(a, set) and len(a) == 1)):
        return "number"
    elif isinstance(a, np.ndarray) or isinstance(a, list) or isinstance(a, set):
        res = np.array(a, dtype=float)
        # if len(res.shape) == 2:
        #     if res.shape[0] == 1:
        #         # make all row vectors (1, x) to be arrays(x, )
        #         res = res[0, :]
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
        if submission_metadata["users"][0]["name"] == "Test Student":
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

    # execute student's solution
    try:
        language, student_answers_dict = execute()
    except Exception as e:
        results["output"] = f"Execution failed for an unusual reason: {str(e)}. \n Please contact your instructor for assistance."
        dump_results_and_exit(results, print_score=False)

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
