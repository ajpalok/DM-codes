"""Mahalanobis distance classifier: nearest class mean, with distance corrected by each class's covariance.

Type: supervised learning (classification).
"""
import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin


class MahalanobisClassifier(ClassifierMixin, BaseEstimator):
    """Nearest class mean under the Mahalanobis distance, with one covariance matrix per class."""

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.means_ = [X[y == c].mean(axis=0) for c in self.classes_]                                # step 1
        self.inv_covs_ = [np.linalg.pinv(np.cov(X[y == c], rowvar=False)) for c in self.classes_]    # steps 2-3
        return self

    def distances(self, X):
        return np.column_stack([np.sqrt(np.clip(np.einsum("ij,jk,ik->i", X - m, s, X - m), 0, None))
                                for m, s in zip(self.means_, self.inv_covs_)])                       # step 4

    def decision_function(self, X):
        d = self.distances(X)
        return d[:, 0] - d[:, 1]            # positive when the point is closer to class 1

    def predict(self, X):
        return self.classes_[self.distances(X).argmin(axis=1)]                                       # step 5
