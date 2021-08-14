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

from gspack.directories import *
from gspack.directories import TEST_STUDENT_NAME, TEST_STUDENT_EMAIL
from gspack.helpers import UserFailure


class Environment:
    """
    This class administers all interactions of `grader` with the outer world:
    accessing meta-data, student credentials, output directories etc.
    """

    def __init__(self,
                 name=TEST_STUDENT_NAME,
                 email=TEST_STUDENT_EMAIL,
                 attempt_number=1,
                 max_number_of_attempts=-1,
                 max_score=0,
                 max_previous_score=0,
                 submission_dir=None,
                 submission_path=None,
                 rubric_path=None,
                 results_path=None,
                 test_values_path=None):
        """
        Creates an instance of Environment

        :param name: Student's name
        :param email: Student's email
        :param attempt_number: number of the current submission attempt
        :param max_number_of_attempts: maximal number of attempts from Rubric
        :param max_score: maximal score from Rubric
        :param max_previous_score: maximal previous score archived by this student
        :param submission_dir: path to submission directory
        :param submission_path: path to the main file in submission directory
        :param rubric_path: path to the rubric JSON file
        :param results_path: where to write a JSON file with results
        :param test_values_path: path to a pickle file with true values from the rubric's test suite
        """
        self.name = name
        self.email = email
        if name == TEST_STUDENT_NAME and email == TEST_STUDENT_EMAIL:
            self.test_student = True
        else:
            self.test_student = False
        self.attempt_number = attempt_number
        self.max_number_of_attempts = max_number_of_attempts
        self.max_score = max_score
        self.max_previous_score = max_previous_score
        self.submission_dir = submission_dir
        self.submission_path = submission_path
        self.rubric_path = rubric_path
        self.results_path = results_path
        self.test_values_path = test_values_path

    @staticmethod
    def from_gradescope(gs_home_dir_override=None):
        """
        Creates an instance of Environment for Gradescope. Assumes the structure of a Gradescope server.

        :return: an instance of Environment configured to work on a Gradescope server.
        """

        gs_home_dir = GS_HOME_DIR if gs_home_dir_override is None else gs_home_dir_override
        gs_dirs = GSDirectoryStructure(home_dir=gs_home_dir)


        with open(gs_dirs.submission_metadata_json(), 'r') as metadata_file:
            submission_metadata = json.load(metadata_file)

        # Get username and email
        try:
            user = submission_metadata["users"]
            if type(user) is list:
                user = user[0]
            name = user["name"]
            email = user["email"]
        except Exception as e:
            print(f"Can't access student's name: {e}")
            name = DEFAULT_STUDENT_NAME
            email = DEFAULT_STUDENT_EMAIL

        # Find how many attempts have already been used
        previous_attempts_counter = 0
        max_previous_score = 0

        for previous_submission in submission_metadata['previous_submissions']:
            results = previous_submission["results"]
            extra_data = results.get('extra_data', None)
            if extra_data is not None and extra_data["success"] and not extra_data["pretest"]:
                previous_attempts_counter += 1
                max_previous_score = max(max_previous_score, results["score"])

        environment = Environment(
            name=name,
            email=email,
            attempt_number=previous_attempts_counter + 1,
            max_previous_score=max_previous_score,
            submission_dir=gs_dirs.submission_dir(),
            results_path=gs_dirs.results_json(),
            rubric_path = gs_dirs.source_dir() / RUBRIC_JSON,
            test_values_path=gs_dirs.source_dir() / TEST_SUITE_VALUES_FILE
        )
        return environment


    def write_down_and_exit(self, results, keep_maximal_score=True):
        """
        Writes `results` to `self.results_path`. Meant to be the end stage of both `self.write_results()`
        and `self.write_error()`.

        :param results: a dictionary formatted according to Gradescope's requirements for `results.json` file.
        :param keep_maximal_score: whether to keep the maximal previous score as current.
        :return: None
        """

        output = (f"Attempt {self.attempt_number}" +
                  (f"/{self.max_number_of_attempts}\n" if (self.max_number_of_attempts > 0
                                                           and not self.test_student
                                                           ) else "/Unlimited\n"))
        # Put the information with the attempt number to the beginning on the output message.
        results["output"] = output + results["output"]

        # Censor results and rests if the maximal score has already been previously achieved
        # or if the student used all attempts. Test Student is exempted from this.
        if self.max_previous_score >= self.max_score and not self.test_student:
            results["output"] = "You already achieved maximum score possible.\n"
            results["tests"] = []

        if self.attempt_number > self.max_number_of_attempts > 0 and not self.test_student:
            results["output"] = f"You've already used all {self.max_number_of_attempts} attempts.\n"
            results["tests"] = []

        if keep_maximal_score:
            # Let student know if the system kept his previous maximal score
            # because this submission's score is not an improvement.
            if results["score"] < self.max_previous_score:
                results["score"] = self.max_previous_score
                results["output"] += (f'The score is set to your previous ' +
                                      f'maximal score of {self.max_previous_score:.2f}/{self.max_score:.2f}\n')
        with open(self.results_path, "w") as f:
            json.dump(results, f, indent=4)
        return None

    def write_results(self, results: dict):
        """
        Forms results.json based on `results` -- partially formed results.json with
        `tests` field filled in.

        :param results: dictionary with `tests` field filled in with grading results.
        :return: None
        """

        results["output"] = (f"Executed successfully." +
                             f" Current score: {results['score']:.2f}/{self.max_score:.2f} \n")

        results["score"] = round(results["score"], 2)
        self.write_down_and_exit(results)
        return None

    def write_exception(self, exception: Exception):
        """
        Forms results.json based on `exception`. This exception can be a result of
        either student's actions, in which case the student looses an attempt, or gspack malfunctioning,
        in which case student does not loose an attempt and is asked to contact their instructor.

        :param exception: Exception that occurred during execution.
        :return: None
        """
        results = {
            "output": "ERROR: \n",
            "score": 0,
            "extra_data": {
                "success": True,
                "pretest": False
            }
        }
        if type(exception) is UserFailure:
            results["output"] += str(exception) + "\n"
        else:
            results["output"] += (f"Autograder failed to process your submission" +
                                  f" due to an internal error: \n {str(exception)} \n" +
                                  f"Please contact your instructor for assistance. " +
                                  f" This attempt does not count towards your" +
                                  f" total number of attempts, if limited.\n"
                                  )
            results["extra_data"]["success"] = False

        results["score"] = round(results["score"], 2)
        self.write_down_and_exit(results)
        return None
