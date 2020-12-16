import matlab.engine  # This import can only be the first line in the file (*fpm*)
from matlab.engine import MatlabExecutionError  # it's NOT an error: it will be imported once matlab.engine is.
from gspack.helpers import UserFailure, GspackFailure


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
        err_msg = f"Execution failed: \n {str(e)}"
        if str(e) == "MATLAB function cannot be evaluated":
            err_msg += "\n Check that you suppress all console outputs " \
                       "(semicolumn at the end of line), especially in loops."
        elif str(e).endswith(
                ' (and maybe others) not assigned during call to "solution>student_solution".\n'):
            err_msg += "\n Check that you defined the aforementioned variables in your solution file."
        raise UserFailure(err_msg)
    try:
        workspace = {}
        for name in matlab_settings["variables_to_take"]:
            item = get_from_workspace(eng.workspace, name)
            if item is not None:
                workspace[name] = item
        eng.quit()
        return workspace
    except Exception as e:
        raise GspackFailure("MATLAB's workspace is inaccessible")
