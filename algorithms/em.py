"""Expectation-Maximisation for a mixture of two one-dimensional Gaussians.

Type: unsupervised learning.
E-step: probability of each group for each point. M-step: weighted re-estimate of mean, spread and weight.
"""
import numpy as np


def em_two_gaussians(x, mu, sigma, weight, max_iter=2000, tol=1e-6):
    log_lik = []
    for _ in range(max_iter):
        dens = weight * np.exp(-0.5 * ((x[:, None] - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
        log_lik.append(float(np.log(dens.sum(axis=1)).sum()))
        resp = dens / dens.sum(axis=1, keepdims=True)                 # E-step: P(group | x)
        nk = resp.sum(axis=0)                                         # M-step: weighted re-estimates
        mu = (resp * x[:, None]).sum(axis=0) / nk
        sigma = np.sqrt((resp * (x[:, None] - mu) ** 2).sum(axis=0) / nk)
        weight = nk / len(x)
        if len(log_lik) > 1 and abs(log_lik[-1] - log_lik[-2]) < tol:
            break
    return mu, sigma, weight, log_lik
