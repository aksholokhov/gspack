import subprocess


def generate_requirements(filepath, output_path):
    process = subprocess.Popen(["pipreqs", "--savepath", f"{output_path}", f"{filepath}"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    return process.communicate()


def determine_platform(file_path):
    if str(file_path).endswith(".py"):
        platform = "python"
    elif str(file_path).endswith(".m"):
        platform = "matlab"
    elif str(file_path).endswith(".ipynb"):
        platform = "jupyter"
    else:
        platform = None
    return platform
