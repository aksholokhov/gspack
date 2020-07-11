import numpy as np
import pickle

x = 10
y = -2
z = np.pi

A1 = x + y - z
A2 = x**4

with open("matrix.dat", "rb") as f:
    matrix = pickle.load(f)

A3 = np.linalg.svd(matrix)[0][:2]