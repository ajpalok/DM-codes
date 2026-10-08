"""K-medoids clustering on a precomputed distance matrix: the centre of a cluster is one of its members.

Type: unsupervised learning.
"""
import numpy as np


def kmedoids(D, k, rng, max_iter=50):
    medoids = rng.choice(len(D), k, replace=False)
    for _ in range(max_iter):
        labels = D[:, medoids].argmin(axis=1)                                   # assignment step
        new = medoids.copy()
        for j in range(k):
            members = np.where(labels == j)[0]
            if len(members):
                new[j] = members[D[np.ix_(members, members)].sum(axis=0).argmin()]   # best medoid of the cluster
        if np.array_equal(new, medoids):
            break
        medoids = new
    labels = D[:, medoids].argmin(axis=1)
    return medoids, labels, float(D[np.arange(len(D)), medoids[labels]].sum())
