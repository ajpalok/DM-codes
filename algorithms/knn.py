"""K-nearest-neighbours classification with Euclidean distance and majority vote.

Type: supervised learning (classification), instance-based.
"""
import numpy as np


def knn_predict(X_train, y_train, X_test, k):
    preds, ties = [], []
    for x in X_test:
        dist = np.sqrt(((X_train - x) ** 2).sum(axis=1))          # Euclidean distance to every training row
        nearest = np.argsort(dist, kind="stable")[:k + 1]         # the K nearest (and the next one, to detect ties)
        preds.append(int(y_train[nearest[:k]].sum() * 2 > k))     # majority vote
        ties.append(bool(np.isclose(dist[nearest[k - 1]], dist[nearest[k]], atol=1e-6)))
    return np.array(preds), np.array(ties)
