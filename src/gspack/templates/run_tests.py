import json
from pathlib import Path
import pickle
import types
import os
import numpy as np
import shutil

# HOME_DIR = Path("/Users/aksh/Storage/repos/gspack/examples/python101/autograder")
HOME_DIR = Path("/autograder")
SOURCE_DIR = HOME_DIR / "source"
SUBMISSION_DIR = HOME_DIR / "submission"
TEST_SUITE_DUMP = "test_suite.dump"
RESULTS_DIR = HOME_DIR / "results"
RESULTS_JSON = "results.json"
CONFIG_JSON = "config.json"

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
    elif type(a) == int or type(a) == float:
        return a
    else:
        raise ValueError(f"Unknown MATLAB type: {type(a)}")


def execute(student_solution_path, language="python"):
    student_answers = {}
    successfully_executed = True
    mydir = os.getcwd()
    os.chdir(student_solution_path.parent)

    if language == "PYTHON":
        solution_code = open(student_solution_path, 'r').read()
        solution_module_name = os.path.basename(student_solution_path)
        solution_module = types.ModuleType(solution_module_name)
        solution_module.__file__ = os.path.abspath(student_solution_path)
        try:
            exec(solution_code, solution_module.__dict__)
        except Exception as e:
            successfully_executed = False
            student_answers["execution_error"] = f"Execution failed: \n {str(e)}"

        for test in test_suite:
            student_answers[test["test_name"]] = solution_module.__dict__.get(test["variable_name"], None)

    elif language == "MATLAB":
        if not MATLAB_SUPPORT:
            err_msg = "MATLAB Support is disabled for this assignment, but a MATLAB file is submitted."
            print(err_msg)
            raise NotImplementedError(err_msg)
        # wrap up the MATLAB main body script as a function
        with open(student_solution_path) as student_file_src:
            solution_parts = student_file_src.read().split("function ")
            main_script_body = solution_parts[0]
            other_functions = "" if len(solution_parts) == 1 else " ".join(
                ["\nfunction " + s for s in solution_parts[1:]])
            with open(SUBMISSION_DIR / 'solution.m', 'w') as student_file_dst:
                prefix = f"function [{', '.join([test['variable_name'] for test in test_suite])}] = solution() \n"
                postfix = "\nend\n"
                student_file_dst.write(prefix)
                student_file_dst.write(main_script_body)
                student_file_dst.write(postfix)
                student_file_dst.write(other_functions)
        # Execute MATLAB solution file and convert its outputs to python-compartible representation
        try:
            eng = matlab.engine.start_matlab()
        except Exception as e:
            print("MATLAB engine failed to start with the following error")
            print(e)
        try:
            output = eng.solution(nargout=len(test_suite))
            for v, test in zip(output, test_suite):
                student_answers[test["test_name"]] = matlab2python(v)
        except Exception as e:
            successfully_executed = False
            student_answers["execution_error"] = f"Execution failed: \n {str(e)}"
        finally:
            os.remove(SUBMISSION_DIR / 'solution.m')
    else:
        successfully_executed = False
        student_answers["execution_error"] = f"Unsupported language: {language}"
    os.chdir(mydir)

    return successfully_executed, student_answers


if __name__ == '__main__':
    # get test suite
    test_suite, extra_files = pickle.load(open(SOURCE_DIR / TEST_SUITE_DUMP, "rb"))

    results = {}

    # Find the student's solution file and figure out the language by its extension
    student_solution_path = []
    language = None
    for f in os.listdir(SUBMISSION_DIR):
        if f.endswith(".py"):
            language = "PYTHON"
            student_solution_path.append(SUBMISSION_DIR / f)
        elif f.endswith(".m"):
            language = "MATLAB"
            student_solution_path.append(SUBMISSION_DIR / f)
        else:
            continue
    if len(student_solution_path) == 0:
        results["output"] = "No student solution files found."
    elif len(student_solution_path) > 1:
        results["output"] = ("Don't know which one is the right solution file: \n ->" +
                             "\n ->".join([str(path) for path in student_solution_path]) +
                             "\n You need to submit only one solution file."
                             )
    else:
        student_solution_path = student_solution_path[0]
        # copy all extra files to the student's solution folder
        for f in extra_files:
            shutil.copyfile(SOURCE_DIR / f, SUBMISSION_DIR / f)

        # execute student's solution
        successfully_executed, student_answers = execute(student_solution_path, language=language)
        if not successfully_executed:
            results["output"] = student_answers["execution_error"]
            results["score"] = 0
            with open(RESULTS_DIR / RESULTS_JSON, "w") as f:
                json.dump(results, f, indent=4)
            exit(0)

        # Grade student's solution results
        results["tests"] = []
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
            if student_answers[test["test_name"]] is None:
                test_result["output"] = (f"Variable {test['variable_name']} is not defined in your solution file." +
                                         "" if test.get("hint_not_defined",
                                                        None) is None else f"\nHint: {test['hint_not_defined']}")
                continue
            answer = student_answers[test["test_name"]]

            if not ((type(answer) == type(true_answer)) or (
                    type(answer) in (float, int) and (type(true_answer) in (float, int)))):
                test_result[
                    "output"] = f"Wrong answer type: the type of your variable {test['variable_name']} is {type(answer)}, " \
                                f"but it should be {type(true_answer)}"
                test_result["output"] += "" if test.get("hint_wrong_type",
                                                        None) is None else f"\nHint: {test['hint_wrong_type']}"

                continue
            if type(answer) is np.ndarray and answer.shape != true_answer.shape:
                test_result[
                    "output"] = f"Wrong dimensions: the shape of your variable {test['variable_name']} is {answer.shape}, " \
                                f"but it should be {true_answer.shape}"
                test_result["output"] += "" if test.get("hint_wrong_size",
                                                        None) is None else f"\nHint: {test['hint_wrong_size']}"
                continue
            if np.isnan(answer).any():
                test_result["output"] = f"Your variable {test['variable_name']} contains NaNs."
                test_result["output"] += "" if test.get("hint_nans", None) is None else f"\nHint: {test['hint_nans']}"
                continue
            rtol = test.get("rtol", None) or 1e-5
            atol = test.get("atol", None) or 1e-8
            if not np.allclose(answer, true_answer, rtol=rtol, atol=atol):
                test_result["output"] = f"Your answer is not within tolerance from the right answer."
                test_result["output"] += "" if test.get("hint_tolerance",
                                                        None) is None else f"\nHint: {test['hint_tolerance']}"
                continue
            test_result["output"] = "Correct."
            test_result["score"] = test["score"]

    with open(RESULTS_DIR / RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=4)
