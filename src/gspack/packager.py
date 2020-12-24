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
import os
import shutil
from zipfile import ZipFile

import click

from gspack.__about__ import __author__, __email__
from gspack.__about__ import __version__
from gspack.directories import *
from gspack.directories import AUTOGRADER_ZIP
from gspack.executor import Executor
from gspack.helpers import UserFailure, GspackFailure, determine_platform
from gspack.helpers import generate_requirements
from gspack.rubric import Rubric


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
def create_autograder_from_terminal(solution, rubric, verbose=True):
    """
    Wrapper function for creating autograder archives from a terminal.

    :param solution: path to solution file
    :param rubric: path to a rubric file (.json). If not provided then the rubric is assumed to be in the solution file.
    :param verbose: whether to print detailed outputs.
    :return: None
    """
    return create_autograder(solution, rubric, verbose)


def create_autograder(solution, rubric=None, verbose=True):
    """
    Creates autograder archive based on the solution. The archive is named "autograder.zip", and
    is placed alongside the solution file.

    :param solution: path to solution file
    :param rubric: path to a rubric file (.json). If not provided then the rubric is assumed to be in the solution file.
    :param verbose: whether to print detailed outputs.
    :return: None
    """
    solution_path = Path(solution).resolve()
    try:
        platform = determine_platform(solution_path)

        if rubric is not None:
            # If path to a rubric file is provided then it's loaded first,
            # and the rubric inside the solution file, if any, is ignored.
            rubric_path = Path(rubric).resolve()
            rubric = Rubric.from_json(rubric_path, verbose=verbose, solution_platform=platform)
            # The solution file is executed, the variables from its namespace are stored in solution_variables
            # See the docstring for Executor.execute() for more details.
            _, solution_variables = Executor(verbose=True,
                                             matlab_config=rubric.matlab_config).execute(solution_path)
        else:
            if platform == "matlab":
                # For MATLAB solutions a separate rubric file has to be provided
                # since there is no way to put it inside the solution file itself.
                raise UserFailure("You need to provide a rubric file with your MATLAB solution.\n" +
                                  "Use argument '--rubric path/to/rubric.json'")
            _, solution_variables = Executor(verbose=True).execute(solution_path)
            # When rubric is not provided as a separate file, gspack looks for it in the solution file's namespace.
            rubric = Rubric.from_dict(solution_variables, verbose=verbose, solution_platform=platform)

        # Scan the rubric and pull the values of variables from test suite from solution_variables.
        # These values are going to be saved to autograder.zip alongside with the rubric.
        rubric.fetch_values_for_tests(solution_variables)
        create_archive(solution_path.parent / AUTOGRADER_ZIP, rubric=rubric, platform=platform, verbose=verbose)

    except UserFailure as e:
        # This error indicates that something went wrong because the user did something wrong,
        # and gspack was able to identify what exactly and provided a suggestion
        # in the error's message.
        print("ERROR: The process is aborted, see the error below:")
        print(e)
        return None
    except (GspackFailure, Exception) as e:
        # This error indicates that something went out of gspack's control. It likely indicates a bug in gspack.
        print("ERROR: The process is aborted due to an unusual reason. Contact the developers.")
        # raise e
        print(e)
        return None
    print(f"Archive created successfully: \n-> {solution_path.parent / AUTOGRADER_ZIP}")


def create_archive(archive_path: Path, rubric: Rubric, platform: str, verbose=False):
    """
    Creates a Gradescope autograder archive (autograder.zip).

    :param archive_path: path where archive should be saved.
    :param rubric: rubric with attached true values.
    :param platform: which language was used for writing the solution file
    :param verbose: whether to print detailed outputs.
    :return: None. Saves the archive to archive_path or aborts.
    """
    if verbose:
        print("Generating the archive:")
    program_dir = Path(os.path.dirname(__file__))
    archive_dir = archive_path.parent.absolute()
    try:
        # This function puts all the files for the archive to a newly created DIST_DIR and
        # deletes it once it's packed into autograder.zip
        os.mkdir(archive_dir / DIST_DIR)

        # Copy necessary files (setup.sh, run_autograder). See AUTOGRADER_ARCHIVE_FILES.
        for file in AUTOGRADER_ARCHIVE_FILES:
            full_path = program_dir / TEMPLATES_DIR / file
            if not os.path.exists(full_path):
                raise GspackFailure(f"-> {file}: the file {full_path} does not exist." +
                                    f" It's likely a gspack installation bug." +
                                    f" You should contact authors" +
                                    f" or post the issue on the project's Github page.")
            shutil.copyfile(full_path, archive_dir / DIST_DIR / file)
            if verbose:
                print(f"-> {file}: OK")

        # Generate requirements file. It's either in 'requirements' variable or it can be generated via pipreqs.
        if verbose:
            print("Looking for package requirements for your solution:")
        if rubric.requirements is not None:
            with open(archive_dir / DIST_DIR / REQUIREMENTS_FILE, "w") as f:
                f.write("\n".join(rubric.requirements))
                print("-> saved from 'requirements' variable, OK.")
        else:
            # pipreqs package scans the solution and generates the list of (non-standard) Python packages used.
            if platform == "python":
                generate_reqs_output = generate_requirements(archive_dir,
                                                             output_path=archive_dir / DIST_DIR / REQUIREMENTS_FILE)
                if not generate_reqs_output[0].startswith(b"INFO: Successfully saved"):
                    raise GspackFailure("Extra package requirements identification FAILED. " +
                                        "Make sure all solution files in the solution's " +
                                        "directory (including subdirectories), " +
                                        "can be executed without errors, and there are no other," +
                                        " irrelevant python files in the solution directory.")
                if verbose:
                    print(f"-> Generated via pipreqs: OK")
            elif platform == "jupyter":
                if verbose:
                    print("-> Not provided, assumed no extra packages are needed")
            elif platform == "matlab":
                print("-> If you need extra MATLAB toolboxes for your solution contact your department " +
                      "to make sure they're added to the department's MATLAB distribution for Gradescope.")
            else:
                pass

        # This file will contain all the information that setup.sh needs during
        # the Docker initialization process.
        config = {}

        if "matlab" in rubric.supported_platforms:
            # Add MATLAB support
            if rubric.matlab_credentials is None:
                raise UserFailure("MATLAB support is requested but no matlab_credentials path is provided")
            if verbose:
                print("Adding MATLAB support...")

            # Check that all the necessary files are in the credentials folder
            matlab_folder_path = Path(rubric.matlab_credentials).expanduser().absolute()
            if not matlab_folder_path.exists() or not matlab_folder_path.is_dir():
                raise UserFailure(
                    f"matlab_credentials: the directory {matlab_folder_path} does not exist" +
                    f" or it's not a directory.")

            # Move all necessary files to the archive's directory
            for file in MATLAB_FILES:
                if not (matlab_folder_path / file).exists():
                    raise UserFailure(f"-> {file}: File {(matlab_folder_path / file).absolute()} does not exist.")
                shutil.copyfile(matlab_folder_path / file,
                                archive_dir / DIST_DIR / file)
                if verbose:
                    print(f"-> {file}: OK")

            # Getting prefix and suffix commands for the run_autograder script, if any.
            # These _prefix and _suffix normally contain all the commands
            # which need to be executed before and after the main
            # grading script kicks in. For instance, opening and closing a SSH tunnels to
            # MATLAB license servers, if used.
            run_autograder_prefix = ""
            run_autograder_suffix = ""
            if (matlab_folder_path / PROXY_SETTINGS).exists():
                with open(matlab_folder_path / PROXY_SETTINGS, "r") as proxy_settings_file:
                    proxy_settings = json.load(proxy_settings_file)
                    if proxy_settings['open_tunnel'] is not None:
                        run_autograder_prefix += proxy_settings['open_tunnel']
                    if proxy_settings['close_tunnel'] is not None:
                        run_autograder_suffix += proxy_settings['close_tunnel']

            # Create run_autograder file given the prefix and suffix
            with open(archive_dir / DIST_DIR / RUN_AUTOGRADER_FILE, 'w') as run_autograder_dest:
                run_autograder_dest.write("#!/usr/bin/env bash \n")
                if run_autograder_prefix is not None:
                    run_autograder_dest.write(run_autograder_prefix + "\n")
                with open(program_dir / TEMPLATES_DIR / RUN_AUTOGRADER_FILE, 'r') as run_autograder_src:
                    run_autograder_dest.write(run_autograder_src.read() + "\n")
                if run_autograder_suffix is not None:
                    run_autograder_dest.write(run_autograder_suffix)
            config["matlab_support"] = 1
            if verbose:
                print("MATLAB support added successfully.", end='\n')
        else:
            config["matlab_support"] = 0
            # Create run_autograder file only adding bash prefix to the template
            with open(archive_dir / DIST_DIR / RUN_AUTOGRADER_FILE, 'w') as run_autograder_dest:
                run_autograder_dest.write("#!/usr/bin/env bash \n")
                with open(program_dir / TEMPLATES_DIR / RUN_AUTOGRADER_FILE, 'r') as run_autograder_src:
                    run_autograder_dest.write(run_autograder_src.read() + "\n")

        # Add Jupyter Notebooks support.
        if "jupyter" in rubric.supported_platforms:
            config["jupyter_support"] = 1
        else:
            config["jupyter_support"] = 0

        # save the config.json file
        with open(archive_dir / DIST_DIR / CONFIG_JSON, 'w') as f:
            json.dump(config, f)

        # Check and add extra files from extra_files list,
        if verbose and rubric.extra_files is not None:
            print("Find extra files list:")

        for extra_file in rubric.extra_files:
            if not (archive_dir / extra_file).exists():
                raise UserFailure(f"{extra_file}: can't find {archive_dir / extra_file}")
            shutil.copyfile(archive_dir / extra_file, archive_dir / DIST_DIR / extra_file)
            if verbose:
                print(f"-> {extra_file}: OK")

        # save the rubric and true values from the rubric to the archive's folder.
        rubric.save_to(archive_dir / DIST_DIR)

        # Zip all files in DIST directory
        zip_archive = ZipFile(archive_dir / AUTOGRADER_ZIP, 'w')
        for extra_file in os.listdir(archive_dir / DIST_DIR):
            zip_archive.write(archive_dir / DIST_DIR / extra_file, arcname=extra_file)
        zip_archive.close()
        return True
    finally:
        # Delete the temporary dist directory
        if os.path.exists(archive_dir / DIST_DIR):
            shutil.rmtree(archive_dir / DIST_DIR)
