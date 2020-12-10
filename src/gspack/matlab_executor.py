import matlab.engine
from gspack.main import UserFailure, GspackFailure


def execute_matlab(file_path, matlab_settings):
    # Execute MATLAB solution file
    try:
        # it's actually used below: see exec command
        eng = matlab.engine.start_matlab()
    except Exception as e:
        raise GspackFailure(f"MATLAB Engine failed to start with the following error: \n {e}.")
    try:
        eval(f"eng.{file_path.stem}(nargout={matlab_settings['nargout']})")
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
        return eng.workspace
    except Exception:
        raise GspackFailure("MATLAB's workspace is inaccessible")
