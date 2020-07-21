import matlab.engine
import numpy as np


def matlab2python(a):
    if type(a) == matlab.double:
        return np.array(a)
    elif type(a) == int or type(a) == float:
        return a
    else:
        raise ValueError(f"Unknown MATLAB type: {type(a)}")
