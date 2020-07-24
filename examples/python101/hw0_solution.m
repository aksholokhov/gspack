x = 10;
y = -2;
z = pi;

A1 = x + y - z;
A2 = x^3;

matrix = table2array(readtable('matrix.csv'));
[U, S, V] = svd(matrix);
A3 = U(:, 1:2);