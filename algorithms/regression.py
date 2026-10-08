"""Least-squares regression: a line by the closed-form slope and intercept, a polynomial by the normal equation.

Type: supervised learning (regression).
"""
import numpy as np


def fit_line(x, y):
    w1 = float(((x - x.mean()) * (y - y.mean())).sum() / ((x - x.mean()) ** 2).sum())
    return float(y.mean() - w1 * x.mean()), w1


def fit_polynomial(x, y, degree):
    X = np.vander(x, degree + 1, increasing=True)            # columns 1, x, x^2, ...
    return np.linalg.inv(X.T @ X) @ X.T @ y                  # normal equation


def r_squared(y, y_hat):
    return float(1 - ((y - y_hat) ** 2).sum() / ((y - y.mean()) ** 2).sum())
