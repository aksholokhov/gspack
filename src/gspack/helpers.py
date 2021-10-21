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
from pathlib import Path

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


def generate_requirements(path, output_path):
    """
    Generates a requirements.txt file using pipreqs package.

    WARNING: pipreqs executes and scans ALL files in the `path` directory, related to the solution or not.
    It's because it treats the `path` directory as a Python project's root and all .py files inside it,
    including the ones in subdirectories, as the project's code. In past it led to many confusing situations
    when pipreqs was failing to produce the file because the instructor had other python files in the same directory,
    and those failed to execute.
    Putting the solution file into a temporary folder is also not a solution because then we won't be able
    to accommodate solutions with multiple files: how would you decide what is relevant and what is not?
    The best advice to manage failures of this function is start with checking
    whether there are irrelevant Python files in the directory.
    Another solution would be to list all the packages explicitly in
    "requirements" variable, in which case this function won't be called.

    :param path: Path to the directory which contains the solution file.
    :param output_path: Path where to save the requirements file
    :return:
    """
    process = subprocess.Popen(["pipreqs", "--no-pin", "--savepath", f"{output_path}", f"{path}"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    return process.communicate()


@contextmanager
def redirected_output(new_stdout=None, new_stderr=None):
    """
    Suppresses the output of the function which it is called with.

    :param new_stdout: sys.stdout stream, optional
    :param new_stderr: sys.stderr stream, optional
    :return:
    """
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


# List of all supported platforms with their extensions
all_supported_platforms = {
    "python": [".py", ],
    "matlab": [".m"],
    "jupyter": [".ipynb"]
}

# List af all fields which can be a part of a rubric
all_rubric_variables = [
    "test_suite",
    "total_score",
    "number_of_attempts",
    "supported_platforms",
    "extra_files",
    "main_file_name",
]


def determine_platform(file_path: Path):
    """
    Takes a code file's path and determines the file's language
    by its extension

    :param file_path: Path to the file
    :return: name of the platform or None if the platform has not been identified.
    """
    for platform, extensions in all_supported_platforms.items():
        for extension in extensions:
            if str(file_path).endswith(extension):
                return platform
    return None
