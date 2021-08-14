import gspack.grader as grader
import numpy as np

def test_reduce_type():
    assert grader.reduce_type(3.4) == 3.4
    assert grader.reduce_type(3) == 3.0
    assert grader.reduce_type(np.array([4])) == 4.0
    assert grader.reduce_type(np.array([4.5])) == 4.5
    assert np.all(grader.reduce_type([1, 2]) == np.array([1.0, 2.0]))
