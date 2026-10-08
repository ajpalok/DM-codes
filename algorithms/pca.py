"""Principal component analysis by eigen-decomposition of the covariance matrix.

Type: unsupervised learning (dimensionality reduction).
"""
import numpy as np


def pca_scratch(Z):
    """Eigen-decomposition of the covariance matrix. Returns eigenvalues, eigenvectors (columns) and scores."""
    Zc = Z - Z.mean(axis=0)
    cov = Zc.T @ Zc / (len(Z) - 1)
    values, vectors = np.linalg.eigh(cov)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    return values, vectors, Zc @ vectors
