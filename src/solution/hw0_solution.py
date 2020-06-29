import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3
A3 = np.arange(12).reshape((3, 4))

test_suite = {
    "addition": {
        "variable_name": "A1",
        "description": "Evaluating x + y - z",
        "hint": "check your signs",
        "weight": 1
    },
    "power": {
        "variable_name": "A2",
        "description": "Evaluating x^3",
        "hint": "Check the difference between * and **",
        "weight": 1
    },
    "arange": {
        "variable_name": "A3",
        "similarity": np.linalg.norm,
        "rel_tol": 1e-5,
        "abs_tol": 1e-2,
        "hint": "check transposition",
        "weight": 3
    }
}