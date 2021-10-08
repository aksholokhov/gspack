from pathlib import Path

import os
import shutil
import json
from tempfile import mkdtemp
from zipfile import ZipFile

from gspack.environment import Environment
from gspack.packager import create_autograder
from gspack.grader import grade_on_fake_gradescope

def do_test_gspack(submission_file):
    '''
    Tests packaging an autograder and using it to grade a python submission, end to end.
    '''
    rootdir = Path(os.getcwd())
    test_file_dir = rootdir / "tests/files/integration_test"

    # Move to a working directory
    packaging_dir = Path(mkdtemp())
    test_files = os.listdir(test_file_dir)
    for file_name in test_files:
        full_file_name = test_file_dir / file_name
        if os.path.isfile(full_file_name):
            shutil.copy(full_file_name, packaging_dir)

    print(os.listdir(packaging_dir))

    create_autograder(packaging_dir / "solutions.py", rubric=(packaging_dir / "rubric.json"), verbose=True)
    autograder_zip_path = packaging_dir / "autograder.zip"

    assert os.path.exists(autograder_zip_path)

    # Copy archive to a grading directory and move there to work
    # The directory structure should match the Gradescope specification
    # found here: https://gradescope-autograders.readthedocs.io/en/latest/specs/#file-hierarchy
    grading_dir = Path(mkdtemp())
    shutil.copy(autograder_zip_path, grading_dir / "autograder.zip")
    os.chdir(grading_dir)

    autograder_zip = ZipFile("autograder.zip", 'r')
    autograder_zip.extractall("source")
    shutil.copy(packaging_dir / "submission_metadata.json", grading_dir / "submission_metadata.json")

    os.mkdir(grading_dir / "results")
    os.mkdir(grading_dir / "submission")

    shutil.copy(test_file_dir / submission_file, grading_dir / "submission")

    grade_on_fake_gradescope(gs_home_dir_override=grading_dir)

    with open(grading_dir / "results/results.json") as results_json:
        results = json.load(results_json)
        print(results)
        assert results['score'] == 2

    os.chdir(rootdir)


def test_gspack_python():
    do_test_gspack("submission.py")


def test_gspack_matlab():
    do_test_gspack("submission.m")
