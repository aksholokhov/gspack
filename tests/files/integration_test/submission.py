import numpy as np

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**3

with open("matrix.csv", "r") as f:
    matrix = np.loadtxt(f, delimiter=",")

U, S, V = np.linalg.svd(matrix, full_matrices=True)
A3 = U[:, :2].T
