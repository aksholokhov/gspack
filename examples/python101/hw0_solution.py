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
        "score": 1,
        "hint": "Check your signs"
    },
    "Power": {
        "variable_name": "A2",
        "description": "Evaluating x^3",
        "score": 1
    },
    "Arrange": {
        "variable_name": "A3",
        "rtol": 1e-5,
        "atol": 1e-2,
        "score": 3
    }
}
