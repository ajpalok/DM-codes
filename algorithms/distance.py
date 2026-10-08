"""Distance and similarity measures.

Type: descriptive (no learning). Used by KNN, K-means, K-medoids and near-duplicate detection.
minkowski(a, b, r): r = 1 is Manhattan distance, r = 2 is Euclidean distance.
smc_jaccard(a, b): simple matching and Jaccard coefficients of two binary vectors.
"""
import numpy as np


def minkowski(a, b, r):
    return float((np.abs(a - b) ** r).sum() ** (1 / r))


def smc_jaccard(a, b):
    f11 = int(((a == 1) & (b == 1)).sum())
    f00 = int(((a == 0) & (b == 0)).sum())
    f10 = int(((a == 1) & (b == 0)).sum())
    f01 = int(((a == 0) & (b == 1)).sum())
    return (f11 + f00) / (f11 + f00 + f10 + f01), (f11 / (f11 + f10 + f01) if f11 + f10 + f01 else 0.0), (f11, f00, f10, f01)
