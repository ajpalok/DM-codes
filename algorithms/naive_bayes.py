"""Multinomial Naive Bayes for word counts, with Laplace smoothing.

Type: supervised learning (classification).
"""
import numpy as np


def mnb_fit(counts, y, alpha=1.0):
    log_prior = np.log(np.array([np.mean(y == c) for c in (0, 1)]))
    word_counts = np.vstack([np.asarray(counts[y == c].sum(axis=0)).ravel() for c in (0, 1)])
    log_likelihood = np.log((word_counts + alpha) / (word_counts.sum(axis=1, keepdims=True) + alpha * counts.shape[1]))
    return log_prior, log_likelihood, word_counts


def mnb_predict(counts, log_prior, log_likelihood):
    return np.asarray(counts @ log_likelihood.T + log_prior).argmax(axis=1)   # sums of logs instead of products
