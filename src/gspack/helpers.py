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


import subprocess
import sys
from contextlib import contextmanager

# These two errors indicate which side is responsible for the failure.
# UserFailure invokes when the execution is failed because of the student's or instructor's
# code or its formatting and ultimately leads to a loss of an attempt by a student.
# GspackFailure indicates that something went wrong in gspack, like MATLAB Engine failed to start.
# Normally it indicates a bug in my code.
# The student is not responsible for this error so it won't lead to a loss of an attempt.


class UserFailure(Exception):
    """
    This error indicates the situations when something was wrong because
    of the user's actions.
    """
    pass


class GspackFailure(Exception):
    """
    This errors indicates bugs in gspack. If this error is invoked then the
    student does not loose an attempt and is being asked to contact the instructor for assistance.
    """
    pass


def generate_requirements(filepath, output_path):
    process = subprocess.Popen(["pipreqs", "--savepath", f"{output_path}", f"{filepath}"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    return process.communicate()

@contextmanager
def redirected_output(new_stdout=None, new_stderr=None):
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    if new_stdout is not None:
        sys.stdout = new_stdout
    if new_stderr is not None:
        sys.stderr = new_stderr
    try:
        yield None
    finally:
        sys.stdout = save_stdout
        sys.stderr = save_stderr

all_supported_platforms = {
    "python": [".py", ],
    "matlab": [".m"],
    "jupyter": [".ipynb"]
}

all_rubric_variables = [
    "test_suite",
    "total_score",
    "number_of_attempts",
    "supported_platforms",
    "extra_files",
    "main_file_name",
]


def determine_platform(file_path):
    for platform, extensions in all_supported_platforms.items():
        for extension in extensions:
            if str(file_path).endswith(extension):
                return platform
    return None
