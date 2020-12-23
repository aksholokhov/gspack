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
        Creates an instance of Environment class
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
    def from_gradescope():
        with open(GS_SUBMISSION_METADATA_JSON, 'r') as metadata_file:
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
        for submission_metadata in submission_metadata['previous_submissions']:
            results = submission_metadata["results"]
            if results["extra_data"]["success"] and not results["extra_data"]["pretest"]:
                previous_attempts_counter += 1
                max_previous_score = max(max_previous_score, results["score"])

        environment = Environment(
            name=name,
            email=email,
            attempt_number=previous_attempts_counter + 1,
            max_previous_score=max_previous_score,
            submission_dir=GS_SUBMISSION_DIR,
            results_path=GS_RESULTS_JSON,
            rubric_path=GS_SOURCE_DIR / RUBRIC_JSON,
            test_values_path=GS_SOURCE_DIR / TEST_SUITE_VALUES_FILE
        )
        return environment

    def write_down_and_exit(self, results, keep_maximal_score=True):
        if keep_maximal_score:
            if results["score"] < self.max_previous_score:
                results["score"] = self.max_previous_score
                results["output"] += (f'The score is set to your previous ' +
                                      f'maximal score of {self.max_previous_score:.2f}/{self.max_score:.2f}\n')
        with open(self.results_path, "w") as f:
            json.dump(results, f, indent=4)
        return None

    def write_results(self, results=None, exception=None):

        output = (f"Attempt {self.attempt_number}" +
                  (f"/{self.max_number_of_attempts}\n" if (self.max_number_of_attempts > 0
                                                           and not self.test_student
                                                           ) else "/Unlimited\n"))
        if exception is not None:
            results = {
                "output": output,
                "score": self.max_previous_score,
                "extra_data": {
                    "success": True,
                    "pretest": False
                }
            }
            results["output"] += " ERROR: \n"
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

        elif results is not None:
            results["output"] = output + (f"Executed successfully." +
                                          f" Current score: {results['score']:.2f}/{self.max_score:.2f} \n")

            if self.max_previous_score >= self.max_score and not self.test_student:
                results["output"] = "You already achieved maximum score possible.\n"
                results["tests"] = []

            if self.attempt_number > self.max_number_of_attempts > 0 and not self.test_student:
                results["output"] = f"You've already used all {self.max_number_of_attempts} attempts.\n"
                results["tests"] = []

        results["score"] = round(results["score"], 2)
        self.write_down_and_exit(results)
        return None
