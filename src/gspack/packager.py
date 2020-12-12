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
from gspack.directories import AUTOGRADER_ZIP
from gspack.helpers import UserFailure, GspackFailure


@click.command(
    help="Generates archive for gradescope autograder"
)
@click.version_option(
    version=__version__
)
@click.option(
    '--rubric',
    default=None,
    type=str,
    help="path to the rubric file"
)
@click.argument(
    'solution'
)
def create_autograder(solution, rubric, verbose=True):
    solution_path = Path(solution).absolute()
    try:
        platform, solution_variables = Executor(verbose=True).execute(solution_path)
        if rubric is not None:
            rubric_path = Path(rubric).absolute()
            rubric = Rubric.from_json(rubric_path, verbose=verbose)
        else:
            rubric = Rubric.from_dict(solution_variables, verbose=verbose)
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
        raise e
        # print(e)
        # return None
    print(f"Archive created successfully: \n-> {solution_path.parent / AUTOGRADER_ZIP}")
