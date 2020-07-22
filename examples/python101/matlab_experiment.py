import matlab.engine
from pathlib import Path

path_to_file = Path("hw0_solution.m")

try:
    eng = matlab.engine.start_matlab()
    A = eng.hw0_solution(nargout=4)

except matlab.engine.MatlabExecutionError as e:
    print(e)
finally:
    eng.quit()