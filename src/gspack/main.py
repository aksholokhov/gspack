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


from pathlib import Path
import click

from gspack.__about__ import __version__
from gspack.executor import Executor
from gspack.rubric import Rubric
from gspack.metadata import Metadata
from gspack.directories import AUTOGRADER_ZIP

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


@click.command(
    help="Genreates archive for gradescope autograder"
)
@click.version_option(
    version=__version__
)
@click.argument(
    'solution',
    type=str,
    help="path to the solution file"
)
@click.option(
    '--rubric',
    default=None,
    type=str,
    help="path to the rubric file"
)
def create_autograder(solution, rubric):
    solution_path = Path(solution).absolute()
    try:
        platform, solution_variables = Executor(verbose=True).execute(solution_path)
        if rubric is not None:
            rubric_path = Path(rubric).absolute()
            rubric = Rubric.from_json(rubric_path, verbose=True)
        else:
            rubric = Rubric.from_dict(solution_variables)
        if rubric.supported_platforms is None:
            rubric.supported_platforms = (platform, )
        rubric.fetch_values_for_tests(solution_variables)
        rubric.create_archive(solution_path.parent / AUTOGRADER_ZIP)
    except UserFailure as e:
        print("ERROR: The process is aborted, see the error below:")
        print(e)
        return None
    except (GspackFailure, Exception) as e:
        print("ERROR: The process is aborted due to unusual reason. Contact the developers.")
        print(e)
        return None
    print(f"Archive created successfully: \n-> {solution_path.parent / AUTOGRADER_ZIP}")


@click.command(
    help="Grades solution given the rubric"
)
@click.version_option(
    version=__version__
)
@click.argument(
    '-s',
    type=str,
    help="path to the submission file"
)
@click.option(
    '--rubric',
    default=None,
    type=str,
    help="path to the rubric file"
)
@click.option(
    '--gradescope',
    default=False,
    type=bool,
    help="whether is executed on Gradescope server"
)
def grade(submission, rubric, gradescope):
    submission_path = Path(submission).absolute()
    metadata = Metadata.from_gradescope() if gradescope else Metadata()
    try:
        if rubric is None:
            raise ValueError("Path to the rubric is not provided")
        rubric = Rubric.from_archive_dump(rubric)
        executor = Executor(supported_platforms=rubric.supported_platforms)
        student_module = executor.execute(submission_path)
        grades = rubric.grade(student_module)
        metadata.write_results(grades=grades)
    except Exception as e:
        metadata.write_results(exception=e)
