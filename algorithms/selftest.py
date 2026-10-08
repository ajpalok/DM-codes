"""Check every from-scratch algorithm against a library on small synthetic data.

    python -m algorithms.selftest        (or: npm run algorithms)
"""
import numpy as np
from scipy.spatial.distance import cdist, mahalanobis
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, confusion_matrix, mutual_info_score
from sklearn.mixture import GaussianMixture
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier

from algorithms.apriori import apriori, make_rules
from algorithms.decision_tree import entropy_of, split_measures
from algorithms.distance import minkowski, smc_jaccard
from algorithms.em import em_two_gaussians
from algorithms.evaluation import confusion_counts, metrics_from_counts
from algorithms.kmeans import kmeans_scratch
from algorithms.kmedoids import kmedoids
from algorithms.knn import knn_predict
from algorithms.mahalanobis import MahalanobisClassifier
from algorithms.naive_bayes import mnb_fit, mnb_predict
from algorithms.pca import pca_scratch
from algorithms.perceptron import perceptron_train
from algorithms.regression import fit_line, fit_polynomial, r_squared

rng = np.random.default_rng(0)
blobs = np.vstack([rng.normal(c, 0.6, (60, 4)) for c in (0, 3, 6)])
labels = np.repeat([0, 1, 2], 60)
two = labels < 2
X2, y2 = blobs[two], labels[two]


def check(name, condition):
    print(f"{'ok  ' if condition else 'FAIL'}  {name}")
    assert condition, name


a, b = blobs[0], blobs[1]
check("distance: Minkowski r = 1, 2, 3 equal SciPy", all(np.isclose(minkowski(a, b, r), cdist([a], [b], "minkowski", p=r)[0, 0]) for r in (1, 2, 3)))
smc, jaccard, _ = smc_jaccard(np.array([1, 0, 0, 1, 0]), np.array([1, 1, 0, 0, 0]))
check("distance: SMC = 3/5 and Jaccard = 1/3 on a worked example", np.isclose(smc, 0.6) and np.isclose(jaccard, 1 / 3))

M = rng.random((300, 6)) < np.array([0.7, 0.6, 0.5, 0.4, 0.3, 0.2])
M[:, 1] |= M[:, 0]                                           # item 0 implies item 1
support = apriori(M, 0.2)
rules = make_rules(support, 0.9)
brute = M[:, [0, 1]].all(axis=1).mean()
check("apriori: support of an itemset equals a direct count", np.isclose(support[frozenset([0, 1])], brute))
check("apriori: finds the planted rule {0} -> {1} with confidence 1", ((rules["antecedent"] == frozenset([0])) & (rules["consequent"] == frozenset([1])) & np.isclose(rules["confidence"], 1)).any())

values, vectors, scores = pca_scratch(blobs)
check("pca: eigenvalues equal scikit-learn's explained variance", np.allclose(values, PCA().fit(blobs).explained_variance_))

init = blobs[[0, 60, 120]]
mine, _, sse = kmeans_scratch(blobs, init)
check("kmeans: same partition as scikit-learn from the same start, SSE never rises",
      adjusted_rand_score(mine, KMeans(3, init=init, n_init=1).fit(blobs).labels_) == 1 and all(np.diff(sse) <= 1e-9))

medoids, med_labels, _ = kmedoids(cdist(blobs, blobs), 3, np.random.default_rng(1))
check("kmedoids: recovers the three groups and every medoid is a data point", adjusted_rand_score(med_labels, labels) > 0.95 and len(set(medoids)) == 3)

x = np.concatenate([rng.normal(0, 1, 400), rng.normal(6, 1, 400)])
mu, sigma, weight, loglik = em_two_gaussians(x, np.array([1.0, 4.0]), np.array([2.0, 2.0]), np.array([0.5, 0.5]))
gm = GaussianMixture(2, random_state=0).fit(x.reshape(-1, 1))
check("em: means equal scikit-learn's Gaussian mixture, likelihood never falls",
      np.allclose(np.sort(mu), np.sort(gm.means_.ravel()), atol=0.05) and all(np.diff(loglik) > -1e-6))

pred = (X2[:, 0] > 1.5).astype(int)
tn, fp, fn, tp = confusion_matrix(y2, pred).ravel()
check("evaluation: counts equal scikit-learn's confusion matrix", confusion_counts(y2, pred) == (tp, fn, fp, tn))
check("evaluation: balanced accuracy is the mean of recall and specificity", np.isclose(metrics_from_counts(8, 2, 1, 9)["balanced_acc"], (0.8 + 0.9) / 2))

attribute = np.where(X2[:, 0] > 1.5, "high", "low")
check("decision tree: information gain equals mutual information", np.isclose(split_measures(attribute, y2)["information gain"], mutual_info_score(attribute, y2) / np.log(2)))
check("decision tree: entropy of a 50/50 node is 1 bit", np.isclose(entropy_of(np.array([0, 1, 0, 1])), 1.0))

train, test = np.arange(len(y2)) % 4 != 0, np.arange(len(y2)) % 4 == 0
knn_mine, _ = knn_predict(X2[train], y2[train], X2[test], 5)
check("knn: same predictions as scikit-learn", (knn_mine == KNeighborsClassifier(5).fit(X2[train], y2[train]).predict(X2[test])).all())

maha = MahalanobisClassifier().fit(X2[train], y2[train])
check("mahalanobis: distance equals SciPy and the classifier separates the groups",
      np.isclose(maha.distances(X2[test][:1])[0, 0], mahalanobis(X2[test][0], maha.means_[0], maha.inv_covs_[0])) and (maha.predict(X2[test]) == y2[test]).mean() > 0.95)

Xc = X2 - X2.mean(axis=0)
w, bias, errors = perceptron_train(Xc, y2, epochs=20)
check("perceptron: converges to zero errors on separable data", errors[-1] == 0 and ((Xc @ w + bias > 0).astype(int) == y2).all())

from scipy.sparse import csr_matrix
counts = csr_matrix(rng.poisson(np.where(y2[:, None] == 1, [3, 1, 0.2, 1], [0.2, 1, 3, 1])))
prior, likelihood, _ = mnb_fit(counts[train], y2[train])
check("naive bayes: same predictions as scikit-learn with Laplace smoothing",
      (mnb_predict(counts[test], prior, likelihood) == MultinomialNB(alpha=1.0).fit(counts[train], y2[train]).predict(counts[test])).all())

t = np.arange(30, dtype=float)
y = 2 + 0.5 * t + 0.1 * t ** 2 + rng.normal(0, 1, 30)
w0, w1 = fit_line(t, y)
poly = fit_polynomial(t, y, 2)
check("regression: line and parabola equal NumPy's least squares", np.allclose([w1, w0], np.polyfit(t, y, 1)) and np.allclose(poly[::-1], np.polyfit(t, y, 2)))
check("regression: R squared of a perfect fit is 1", np.isclose(r_squared(y, y), 1.0))

print("\nall algorithm checks passed")
