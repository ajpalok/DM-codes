"""K-means clustering (Lloyd's algorithm): assign to the nearest centroid, move centroids to the mean, repeat.

Type: unsupervised learning.
"""
import numpy as np


def kmeans_scratch(X, centroids, max_iter=100):
    history = []
    for _ in range(max_iter):
        d = ((X[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)        # squared distance to every centroid
        labels = d.argmin(axis=1)                                             # assignment step
        history.append(float(d[np.arange(len(X)), labels].sum()))             # SSE
        new = np.array([X[labels == j].mean(axis=0) if (labels == j).any() else centroids[j]
                        for j in range(len(centroids))])                      # update step
        if np.allclose(new, centroids):
            break
        centroids = new
    return labels, centroids, history
