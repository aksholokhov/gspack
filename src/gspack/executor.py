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


import io
import os
import signal
import sys
import types
from contextlib import contextmanager
from pathlib import Path

from IPython import get_ipython
from IPython.core.interactiveshell import InteractiveShell
from matplotlib import pyplot as plt
from nbformat import read

from gspack.helpers import UserFailure, GspackFailure, redirected_output
from gspack.helpers import determine_platform, all_supported_platforms, all_rubric_variables


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


def raise_timeout(_):
    raise TimeoutError


class Executor:
    def __init__(self,
                 supported_platforms=all_supported_platforms.keys(),
                 timeout_for_execution=1000,
                 matlab_config=None,
                 verbose=False):
        self.supported_platforms = supported_platforms
        if matlab_config is None:
            self.matlab_config = {
                "variables_to_take": all_rubric_variables
            }
        else:
            self.matlab_config = matlab_config
        self.log_path = "execution_log_%s.txt"
        self.timeout = timeout_for_execution
        self.verbose = verbose

    def execute(self, file_path: Path, platform=None):
        if not os.path.exists(file_path):
            raise UserFailure(f"File does not exist: {file_path}")
        if platform is None:
            platform = determine_platform(file_path)
        if platform is None:
            raise UserFailure(f"Can't recognize the language platform for the file {file_path}")
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
                raise GspackFailure(f"Unrecognized platform: {platform}")
        finally:
            os.chdir(my_dir)
        if self.verbose:
            print(f"Found and executed successfully: \n {file_path}")
        return platform, output

    def execute_matlab(self, file_path: Path):
        if "matlab" not in self.supported_platforms:
            raise UserFailure(
                "MATLAB support is disabled for this assignment, but a MATLAB file is submitted.")
        # MATLAB executor has been moved into a separate file because MATLAB Engine
        # requires being imported in the very first line of the file.
        try:
            from .matlab_executor import execute_matlab as execute_matlab_ext
            with timeout(self.timeout):
                output = execute_matlab_ext(file_path,
                                            matlab_config=self.matlab_config)
        except TimeoutError:
            return UserFailure("Code did not finish before timeout.")
        return output

    def execute_python(self, file_path: Path):
        with open(file_path, 'r') as f:
            code = f.read()
        module_name = file_path.stem
        module = types.ModuleType(module_name)
        module.__file__ = os.path.abspath(file_path)

        with open(self.log_path, 'w') as f:
            with redirected_output(new_stdout=f, new_stderr=f):
                try:
                    with timeout(self.timeout):
                        exec(code, module.__dict__)
                except Exception as e:
                    raise UserFailure(f"Exception occurred while executing your code: {str(e)}")
            # in case the code opened plots -- close them
            # to avoid buffer overflow
            plt.close()
        if os.path.exists(self.log_path):
            os.remove(self.log_path)
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
                            raise UserFailure("Code did not finish before timeout")
                        except Exception as e:
                            raise UserFailure("Exception occurred while executing your"
                                              " code in code cell %d: %s" % (code_cells_counter, e))
                        plt.close()
            finally:
                shell.user_ns = save_user_ns
        return module.__dict__
