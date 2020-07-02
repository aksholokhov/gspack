import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3
A3 = np.arange(12).reshape((3, 4))

test_suite = {
    "Addition": {
        "variable_name": "A1",
        "description": "Evaluating x + y - z",
        "hint": "check your signs",
        "score": 1
    },
    "Power": {
        "variable_name": "A2",
        "description": "Evaluating x^3",
        "hint": "Check the difference between * and **",
        "score": 1
    },
    "Arange": {
        "variable_name": "A3",
        "rtol": 1e-5,
        "atol": 1e-2,
        "hint": "check transposition",
        "score": 3
    }
}