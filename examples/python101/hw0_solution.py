import numpy as np
import pickle

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3

with open("matrix.dat", "rb") as f:
    matrix = pickle.load(f)

A3 = np.linalg.svd(matrix)[0][:2].T

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
        "hint": "Don't forget to transpose eigen vectors",
        "rtol": 1e-5,
        "atol": 1e-2,
        "score": 3
    }
}

extra_files = ["matrix.dat"]
