# Algorithms

One file per algorithm, written from scratch with NumPy so that each can be read and explained on its own.
The notebook uses exactly this code: `tools/make_notebook.py` copies each file into the notebook cell that
contains `# %include algorithms/<file>.py`, so there is a single copy of every algorithm.

| File | Algorithm | Type of learning | Notebook section | Checked against |
| --- | --- | --- | --- | --- |
| `distance.py` | Minkowski / Euclidean distance, simple matching and Jaccard coefficients | Descriptive | 3 | SciPy |
| `apriori.py` | Apriori frequent itemsets; rules with support, confidence, lift | Unsupervised | 5 | mlxtend, direct counts |
| `pca.py` | PCA by eigen-decomposition of the covariance matrix | Unsupervised | 6 | scikit-learn |
| `kmeans.py` | K-means (assign, update, repeat) | Unsupervised | 7.1 | scikit-learn |
| `kmedoids.py` | K-medoids on a distance matrix | Unsupervised | 7.2 | known groups |
| `em.py` | EM for a mixture of two Gaussians | Unsupervised | 7.3 | scikit-learn |
| `evaluation.py` | Confusion matrix counts and the metrics derived from them | Evaluation | 8.1 | scikit-learn |
| `decision_tree.py` | Entropy, information gain (ID3), gain ratio (C4.5) | Supervised: classification | 8.2 | mutual information |
| `knn.py` | K-nearest neighbours with majority vote | Supervised: classification | 8.4 | scikit-learn |
| `mahalanobis.py` | Mahalanobis distance classifier | Supervised: classification | 8.5 | SciPy |
| `perceptron.py` | Perceptron learning rule | Supervised: classification | 8.8 | separable data |
| `naive_bayes.py` | Multinomial Naive Bayes with Laplace smoothing | Supervised: classification | 9.1 | scikit-learn |
| `regression.py` | Linear and polynomial least squares | Supervised: regression | 11 | NumPy |

Logistic regression, the multi-layer perceptron and the full decision tree are used from scikit-learn; the
notebook works the logistic sigmoid by hand for one row (section 8.7).

## Check them

```bash
python -m algorithms.selftest      # or: npm run algorithms
```

Each algorithm is run on small synthetic data and compared with a library result.

## Use one

```python
import numpy as np
from algorithms.kmeans import kmeans_scratch

X = np.random.default_rng(0).normal(size=(100, 2))
labels, centroids, sse_per_iteration = kmeans_scratch(X, X[:3])
```

## Where the rest lives

| Location | Content |
| --- | --- |
| `src/features.py` | Text masking and feature extraction, shared with the scoring service |
| `src/prepare_dataset.py` | Cleaning, anonymization and the label audit |
| `notebooks/parts/` | The analysis itself, in order; it applies these algorithms to the data |
| `software/ml_service/app.py` | The deployed model, campaign assignment and mined rules, served to the web application |
