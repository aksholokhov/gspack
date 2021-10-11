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


import matlab.engine  # This import can only be the first in the file (*fpm*)
from matlab.engine import MatlabExecutionError  # it's NOT an error: it will be imported once matlab.engine is.
import numpy as np
import io

import matlab
from gspack.helpers import UserFailure, GspackFailure, redirected_output

from pathlib import Path


def matlab2python(a):
    """
    Converts a MATLAB type to a Python type
    :param a: MATLAB variable to convert
    :return: Python representation of a: bool, float, string, or a Numpy array, depending on a.
    """
    matlab_array_types = (matlab.double,
                          matlab.single,
                          matlab.int8,
                          matlab.int16,
                          matlab.int32,
                          matlab.int64,
                          matlab.uint8,
                          matlab.uint16,
                          matlab.uint32,
                          matlab.uint64
                          )
    if type(a) == complex:
        return np.array(a, dtype=complex)
    if type(a) in matlab_array_types:
        if a._is_complex:
            return np.array(a, dtype=complex)
        else:
            return np.array(a, dtype=float)
    elif type(a) == int or type(a) == float or type(a) == str or type(a) == bool:
        return a
    else:
        raise ValueError(f"Unknown MATLAB type: {type(a)}")


def get_from_workspace(workspace, key: str, default=None):
    """
    Pulls a variable from workspace by it's name (`key`), and returns default if failed.
    Designed to simulate Python dictionary's .get() behaviour.

    :param workspace: MATLAB workspace.
    :param key: variable's name
    :param default: value which will be returned if `key` is not defined
    :return: MATLAB variable with the name "key", if defined, otherwise returns `default`.
    """
    try:
        item = workspace[key]
    except MatlabExecutionError:
        item = default
    return item


def execute_matlab(file_path: Path, matlab_config: dict):
    """
    Executes MATLAB solution script and returns variables from it's namespace.

    :param file_path: Path to the script
    :param matlab_config: Dictionary with additional parameters:

        - `variables_to_take`: list of variables' names which should be pulled from MATLAB's namespace

    :return: Dictionary "name" - "value" for variables listed in matlab_config["variables_to_take"]
    """
    try:
        # Launch MATLAB engione
        eng = matlab.engine.start_matlab()
    except Exception as e:
        raise GspackFailure(f"MATLAB Engine failed to start with the following error: \n {e}.")
    try:
        # Execute MATLAB script
        eval(f"eng.{file_path.stem}(nargout=0)")
    except Exception as e:
        err_msg = f"Exception occurred while executing your code: \n {str(e)}"
        raise UserFailure(err_msg)
    try:
        # pull variables from MATLAB workspace `eng.workspace` into `workspace` dict.
        # The reason to explicitly require the list of variables' names is because
        # MATLAB engine and all its components die once the execution leaves this scope,
        # so `return eng.workspace` would not work.
        workspace = {}
        variables_to_take = matlab_config.get("variables_to_take", ())
        for name in variables_to_take:
            item = get_from_workspace(eng.workspace, name)
            if item is not None:
                workspace[name] = matlab2python(item)
        eng.quit()
        return workspace
    except Exception as e:
        raise GspackFailure(f"Failure while exporting data from MATLAB environment: \n {str(e)}")
