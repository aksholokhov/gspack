import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3

with open("matrix.csv", "r") as f:
    matrix = np.loadtxt(f, delimiter=",")

U, S, V = np.linalg.svd(matrix, full_matrices=True)
A3 = U[:, :2]

test_suite = [
    {
        "test_name": "Addition",
        "variable_name": "A1",
        "description": "Evaluating x + y - z",
        "score": 1,
    },
    {
        "test_name": "Power",
        "variable_name": "A2",
        "description": "Evaluating x^3",
        "hint_tolerance": "Check power.",
        "score": 1
    },
    {
        "test_name": "Arrange",
        "variable_name": "A3",
        "hint_wrong_size": "Check transposition",
        "rtol": 1e-5,
        "atol": 1e-2,
        "score": 3
    }
]

extra_files = ["matrix.csv"]

# matlab_credentials = "~/Storage/repos/gspack_uw_amath_matlab_credentials"