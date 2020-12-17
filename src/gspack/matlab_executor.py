import matlab.engine  # This import can only be the first line in the file (*fpm*)
from matlab.engine import MatlabExecutionError  # it's NOT an error: it will be imported once matlab.engine is.
import numpy as np

import matlab
from gspack.helpers import UserFailure, GspackFailure


def matlab2python(a):
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
    if type(a) in matlab_array_types:
        return np.array(a, dtype=float)
    elif type(a) == int or type(a) == float or type(a) == str or type(a) == bool:
        return a
    else:
        raise ValueError(f"Unknown MATLAB type: {type(a)}")

def get_from_workspace(workspace, key, default=None):
    try:
        item = workspace[key]
    except MatlabExecutionError:
        item = default
    return item

def execute_matlab(file_path, matlab_settings):
    # Execute MATLAB solution file
    try:
        # it's actually used below: see exec command
        eng = matlab.engine.start_matlab()
    except Exception as e:
        raise GspackFailure(f"MATLAB Engine failed to start with the following error: \n {e}.")
    try:
        eval(f"eng.{file_path.stem}(nargout=0)")
    except Exception as e:
        err_msg = f"Exception occurred while executing your code: \n {str(e)}"
        if str(e) == "MATLAB function cannot be evaluated":
            err_msg += "\n Check that you suppress all console outputs " \
                       "(semicolumn at the end of line), especially in loops."
        raise UserFailure(err_msg)
    try:
        workspace = {}
        for name in matlab_settings["variables_to_take"]:
            item = get_from_workspace(eng.workspace, name)
            if item is not None:
                workspace[name] = matlab2python(item)
        eng.quit()
        return workspace
    except Exception as e:
        raise GspackFailure(f"Failure while exporting data from MATLAB environment: \n {str(e)}")
