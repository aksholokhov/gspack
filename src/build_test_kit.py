import subprocess
import os.path
from pathlib import Path
import types
import shutil
from zipfile import ZipFile

DIST_DIR = Path("dist")
TEMPLATES_DIR = Path("templates")
REQUIREMENTS_FILE = "requirements.txt"
RUN_AUTOGRADER_FILE = "run_autograder"
SETUP_FILE = "setup.sh"
RUN_TESTS_FILE = "run_tests.py"
AUTOGRADER_ZIP = "autograder.zip"

def generate_requirements(filepath, output_path):
    process = subprocess.Popen(f"pipreqs --savepath {output_path} {filepath}".split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return process.communicate()


def validate_solution(solution_path):
    if not os.path.exists(solution_path):
        raise FileNotFoundError(f"The file {os.path.abspath(solution_path)} does not exists")
    solution_code = open(solution_path, 'r').read()
    solution_module_name = os.path.basename(solution_path)
    solution_module = types.ModuleType(solution_module_name)
    solution_module.__file__ = os.path.abspath(solution_path)
    try:
        exec(solution_code, solution_module.__dict__)
    except Exception as e:
        print("Error happened while executing the solution file. Logged into")
        return False, None
    if not hasattr(solution_module, 'test_suite'):
        print("No test_suite variable defined in the solution file.")
        return False, None
    test_suite = solution_module.test_suite
    if type(test_suite) is not dict:
        print(f"test_suite is defined as {type(test_suite)} but it should be dict.")
    for k, v in test_suite.items():
        if not hasattr(solution_module, v["variable_name"]):
            print(f"{k}: variable {v['variable_name']} is set to be checked but it's not defined in the solution file")
        else:
            print(f"{k}: ok")

    if hasattr(solution_module, 'extra_files'):
        extra_files = solution_module.extra_files
    else:
        extra_files = []

    return True, extra_files


def create_solution_archive(solution_path, extra_files):
    solution_dir = Path(solution_path).parent.absolute()
    try:
        os.mkdir(solution_dir / DIST_DIR)
        shutil.copyfile(TEMPLATES_DIR / RUN_TESTS_FILE, solution_dir / DIST_DIR / RUN_TESTS_FILE)
        generate_requirements(solution_dir, output_path=solution_dir / DIST_DIR / REQUIREMENTS_FILE)
        shutil.copyfile(TEMPLATES_DIR / SETUP_FILE, solution_dir / DIST_DIR / SETUP_FILE)
        shutil.copyfile(TEMPLATES_DIR / RUN_AUTOGRADER_FILE, solution_dir / DIST_DIR / RUN_AUTOGRADER_FILE)
        all_files_to_zip = [SETUP_FILE, RUN_TESTS_FILE, RUN_AUTOGRADER_FILE, REQUIREMENTS_FILE]
        for extra_file in extra_files:
            try:
                shutil.copyfile(solution_dir / extra_file, solution_dir / DIST_DIR / extra_file)
                all_files_to_zip.append(extra_file)
            except FileNotFoundError:
                print(f"File {os.path.abspath(solution_dir / extra_file)} does not exist.")
                return False
        zip_archive = ZipFile(solution_dir / AUTOGRADER_ZIP, 'w')
        for f in os.listdir(solution_dir / DIST_DIR):
            zip_archive.write(solution_dir / DIST_DIR / f, arcname=f)
        zip_archive.close()
        pass
    finally:
        if os.path.exists(solution_dir / DIST_DIR):
            shutil.rmtree(solution_dir / DIST_DIR)
    return None


# @click.command(
#     help="Genreates archive for gradescope autograder"
# )
# @click.option(
#     '--solution_path',
#     default="solution.py",
#     type=str,
#     help="specify path to the solution"
# )
def create_autograder(solution_path):
    solution_path = Path(solution_path).absolute()
    is_valid, extra_files = validate_solution(solution_path)
    create_solution_archive(solution_path, extra_files)


if __name__ == "__main__":
    create_autograder(solution_path="solution/hw0_solution.py")
