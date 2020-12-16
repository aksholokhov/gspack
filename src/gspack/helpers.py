import subprocess

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


all_supported_platforms = {
    "python": [".py", ],
    "matlab": [".m"],
    "jupyter": [".ipynb"]
}


def determine_platform(file_path):
    for platform, extensions in all_supported_platforms.items():
        for extension in extensions:
            if str(file_path).endswith(extension):
                return platform
    return None
