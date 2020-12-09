import os, sys, io, types, signal

from pathlib import Path
from matplotlib import pyplot as plt

from IPython import get_ipython
from nbformat import read
from IPython.core.interactiveshell import InteractiveShell
from contextlib import contextmanager

from helpers import determine_platform

# These two errors indicate which side is responsible for the failure.
# ExecutionIncomplete invokes when the execution is failed because of the student's or instructor's
# code or its formatting and ultimately leads to a loss of an attempt by a student.
# ExecutorFailure indicates that something went wrong in gspack, like MATLAB Engine failed to start.
# The student is not responsible for this failure so it won't lead to a loss of an attempt.


class ExecutionIncomplete(Exception):
    """
    This error indicates the situation when the execution failed
    because something was wrong with the file, but not with the
    Executor class itself. This is designed to indicate the failures
    on the students'/instructor's side, i.e. code errors occurring in
    their files or failure to comply with the required format.
    """
    pass


class ExecutorFailure(Exception):
    """
    This errors indicates bugs in gspack. If this error is invoked then the
    student does not loose an attempt and is being asked to contact the instructor for assistance.
    """
    pass

@contextmanager
def redirected_output(new_stdout=None, new_stderr=None):
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    if new_stdout is not None:
        sys.stdout = new_stdout
    if new_stderr is not None:
        sys.stderr = new_stderr
    try:
        yield None
    finally:
        sys.stdout = save_stdout
        sys.stderr = save_stderr


@contextmanager
def timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        raise Exception("Timeout")
    except Exception as e:
        raise e
    finally:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)


def raise_timeout(signum, frame):
    raise TimeoutError


class Executor:
    def __init__(self, supported_platforms, timeout=1000, matlab_settings=None):
        self.supported_platforms = supported_platforms
        self.matlab_config = matlab_settings
        self.log_path = "execution_log_%s.txt"
        self.timeout = timeout

    def execute(self, file_path: Path, platform=None):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File does not exist: {file_path}")
        if platform is None:
            platform = determine_platform(file_path)
        if platform is None:
            raise ExecutionIncomplete(f"Can't recognize the language platform for the file {file_path}")
        my_dir = os.getcwd()
        os.chdir(file_path.parent)
        try:
            if platform == "matlab":
                output = self.execute_matlab(file_path)
            elif platform == "jupyter":
                output = self.execute_jupyter(file_path)
            elif platform == "python":
                output = self.execute_python(file_path)
            else:
                raise ExecutorFailure(f"Unrecognized platform: {platform}")
        finally:
            os.chdir(my_dir)
        return platform, output

    def execute_matlab(self, file_path: Path):
        if "matlab" not in self.supported_platforms:
            raise ExecutionIncomplete(
                "MATLAB support is disabled for this assignment, but a MATLAB file is submitted.")
        # MATLAB executor has been moved into a separate file because MATLAB Engine
        # requires being imported in the very first line of the file.
        try:
            from matlab_executor import execute_matlab as execute_matlab_ext
            with timeout(self.timeout):
                output = execute_matlab_ext(file_path, matlab_settings=self.matlab_config)
        except TimeoutError:
            return ExecutionIncomplete("Code did not finish before timeout.")
        return output

    def execute_python(self, file_path: Path):
        code = open(file_path, 'r').read()
        module_name = file_path.stem
        module = types.ModuleType(module_name)
        module.__file__ = os.path.abspath(file_path)

        with open(self.log_path, 'w') as f:
            with redirected_output(new_stdout=f, new_stderr=f):
                try:
                    with timeout(self.timeout):
                        exec(code, module.__dict__)
                except Exception as e:
                    raise ExecutionIncomplete(f"Error occurred while executing your code: {str(e)}")
            # in case the code opened plots -- close them
            # to avoid buffer overflow
            plt.close()
            return module.__dict__

    def execute_jupyter(self, file_path: Path):
        """import a notebook as a module"""
        # load the notebook object
        with io.open(file_path, 'r', encoding='utf-8') as f:
            nb = read(f, 4)

        # create the module and add it to sys.modules
        # if name in sys.modules:
        #    return sys.modules[name]
        shell = InteractiveShell.instance()
        fullname = file_path.stem
        module = types.ModuleType(fullname)
        module.__file__ = file_path
        module.__loader__ = self
        module.__dict__['get_ipython'] = get_ipython
        sys.modules[fullname] = module

        # extra work to ensure that magics that would affect the user_ns
        # actually affect the notebook module's ns
        save_user_ns = shell.user_ns
        shell.user_ns = module.__dict__
        with open(self.log_path, 'w') as f:
            try:
                code_cells_counter = 0
                for cell in nb.cells:
                    if cell.cell_type == 'code':
                        code_cells_counter += 1
                        # transform the input to executable Python
                        code = shell.input_transformer_manager.transform_cell(cell.source)
                        # run the code in module
                        try:
                            with timeout(self.timeout):
                                with redirected_output(new_stdout=f):
                                    exec(code, module.__dict__)
                        except TimeoutError:
                            raise ExecutionIncomplete("Code did not finish before timeout")
                        except Exception as e:
                            raise ExecutionIncomplete("Exception in code cell %d: %s" % (code_cells_counter, e))
                        plt.close()
            finally:
                shell.user_ns = save_user_ns
        return module.__dict__

