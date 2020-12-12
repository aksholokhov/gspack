from gspack.directories import *
import json

from gspack.helpers import UserFailure, GspackFailure
from gspack.directories import TEST_STUDENT_NAME, TEST_STUDENT_EMAIL


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
            if submission_metadata["extra_data"]["success"] and not submission_metadata["extra_data"]["pretest"]:
                previous_attempts_counter += 1
                max_previous_score = max(max_previous_score, submission_metadata["score"])

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


    def write_results(self, results=None, exception=None):

        attempt_counts = False
        keep_previous_score = False

        if self.attempt_number > self.max_number_of_attempts:
            output = f"You've already used all {self.max_number_of_attempts} attempts."
            keep_previous_score  = True
            attempt_counts = False

        if self.max_previous_score >= self.max_score:
            output = "You already achieved maximum score possible."


        output = (f"Attempt {self.attempt_number}" +
                 (f"/{self.max_number_of_attempts}" if (self.max_number_of_attempts > 0
                                                        and not self.test_student
                                                        ) else ""))
        if exception is not None:
            output += "ERROR: \n"
            if type(exception) is UserFailure:
                output += str(exception) + "\n"
            else:
                output += ("Autograder failed to process your submission due to an internal error." +
                           "Please contact your instructor for assistance."
                           "This attempt does not count towards your total number of attempts, if limited."
                           )
                attempt_counts = False
            results = {
                "output": output,
                "score": self.max_previous_score
            }
        elif results is not None:
            pass


        with open(self.results_path, "w") as f:
            json.dump(results, f, indent=4)
        #############################

        output = ""
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
                results[
                    "output"] += f"This is your attempt {number_of_used_attempts + 1} out of {number_of_attempts}. \n"

        pass
