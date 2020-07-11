from pathlib import Path
import pickle
import types
import os
import numpy as np
import json
import shutil


HOME_DIR = Path("/autograder")
SOURCE_DIR = HOME_DIR / "source"
SUBMISSION_DIR = HOME_DIR / "submission"
TEST_SUITE_DUMP = "test_suite.dump"
RESULTS_DIR = HOME_DIR / "results"
RESULTS_JSON = "results.json"

if __name__ == '__main__':
    # get test suite
    test_suite, extra_files = pickle.load(open(SOURCE_DIR / TEST_SUITE_DUMP, "rb"))

    results = {
        "tests": []
    }
    # launch student code
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
                             "\n ->".join(student_solution_path) +
                             "\n You need to submit only one solution file."
                             )
    else:
        student_solution_path = student_solution_path[0]

        if language == "PYTHON":
            for f in extra_files:
                shutil.copyfile(SOURCE_DIR / f, SUBMISSION_DIR / f)

            solution_code = open(student_solution_path, 'r').read()
            solution_module_name = os.path.basename(student_solution_path)
            solution_module = types.ModuleType(solution_module_name)
            solution_module.__file__ = os.path.abspath(student_solution_path)
            try:
                mydir = os.getcwd()
                os.chdir(student_solution_path.parent)
                exec(solution_code, solution_module.__dict__)
                os.chdir(mydir)
            except Exception as e:
                results["score"] = 0
                results["output"] = f"Execution failed: \n {str(e)}"
            for i, (test_name, test) in enumerate(test_suite.items()):
                true_value = test["value"]
                test_result = {
                    "name": f"{i+1}. {test_name}",
                    "score": 0,
                    "visibility": "visible"
                }

                if test.get("description", None) is not None:
                    test_result["name"] += f": {test['description']}"

                results["tests"].append(test_result)
                if not hasattr(solution_module, test["variable_name"]):
                    test_result["output"] = (f"Variable {test['variable_name']} is not defined in your python101." +
                                             "" if test.get("hint", None) is None else f" Hint: {test['hint']}")
                    continue
                answer = solution_module.__getattribute__(test["variable_name"])
                if type(answer) != type(true_value):
                    test_result["output"] = f"Wrong answer type: the type of your variable {test['variable_name']} is {type(answer)}, " \
                                            f"but it should be {type(true_value)}"
                    test_result["output"] += "" if test.get("hint", None) is None else f" Hint: {test['hint']}"

                    continue
                if type(answer) is np.ndarray and answer.shape != true_value.shape:
                    test_result["output"] = f"Wrong dimensions: the shape of your variable {test['variable_name']} is {answer.shape}, " \
                                            f"but it should be {true_value.shape}"
                    test_result["output"] += "" if test.get("hint", None) is None else f" Hint: {test['hint']}"
                    continue
                if np.isnan(answer).any():
                    test_result["output"] = f"Your variable {test['variable_name']} contains NaNs."
                    test_result["output"] += "" if test.get("hint", None) is None else f" Hint: {test['hint']}"
                    continue
                rtol = test.get("rtol", None) or 1e-5
                atol = test.get("atol", None) or 1e-8
                if not np.allclose(answer, true_value, rtol=rtol, atol=atol):
                    test_result["output"] = f"Your answer is not within tolerance from the right answer."
                    test_result["output"] += "" if test.get("hint", None) is None else f" Hint: {test['hint']}"
                    continue
                test_result["output"] = "Correct."
                test_result["score"] = test["score"]

        elif language == "MATLAB":
            # TODO: implement matlab grader
            pass
        else:
            results["output"] = f"Unsupported language: {language}"

    with open(RESULTS_DIR / RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=4)