# %% [markdown]
# # 8. Task A: predicting honeypot evasion (supervised classification)
#
# **Type of learning.** Supervised. The label `honeypot_filled` was recorded by the form itself, so it is an
# observed fact about each submission, not something a rule produced.
#
# **Why it is needed here.** Section 4 showed that the honeypot misses a growing share of spam. If the features
# of a submission predict which senders evade the honeypot, the operator knows which kind of spam needs a second
# line of defence, and the comparison shows which family of model reads these features best.
#
# **Protocol (the same for every model).**
#
# - Rows: the timestamped submissions with a usable label (the window without a honeypot, Section 1.3, is excluded).
#   Features: the 45 columns built in Section 2. No time feature and nothing derived from the honeypot field.
# - **Grouped 5-fold cross-validation.** All copies of a message template stay in the same fold; otherwise a
#   model could score well by recognising a message it has already seen.
# - **Time split.** Train on 2020-2023, test on 2024-2025. This is the honest test for a deployed system: the
#   model always predicts the future from the past.
# - Scalers and PCA are fitted on the training part only. Hyper-parameters are tuned on the 2020-2023 period
#   only, so the 2024-2025 test rows are never used for any decision.
# - Metrics come from the confusion matrix: accuracy, precision, recall, specificity, F1, balanced accuracy
#   (the mean of recall and specificity) and ROC AUC. Training time, prediction time and model size are also
#   recorded, because the software must run on a small server.

# %%
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression, Perceptron
from sklearn.metrics import confusion_matrix, mutual_info_score, roc_auc_score, roc_curve
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.naive_bayes import BernoulliNB, GaussianNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier, NearestCentroid
from sklearn.neural_network import MLPClassifier
from sklearn.tree import DecisionTreeClassifier, export_text

rows_a = np.where(df["honeypot_filled"].notna())[0]
XA = X_all.iloc[rows_a].to_numpy(dtype=float)
yA = df["honeypot_filled"].iloc[rows_a].astype(int).to_numpy()
tid = df["template_id"].iloc[rows_a]
groups_a = np.where(tid != "", tid, "row" + df["id"].iloc[rows_a].astype(str)).astype(str)
year_a = df["year"].iloc[rows_a].astype(int).to_numpy()
past, future = year_a <= 2023, year_a >= 2024
print(f"Task A: {len(yA):,} rows, {XA.shape[1]} features, {len(set(groups_a)):,} template groups")
print(f"class balance: {yA.mean():.1%} filled | train period 2020-2023: {past.sum():,} rows ({yA[past].mean():.1%} filled) "
      f"| test period 2024-2025: {future.sum():,} rows ({yA[future].mean():.1%} filled)")

# %% [markdown]
# ## 8.1 Evaluation from the confusion matrix
#
# |  | predicted filled | predicted empty |
# | --- | --- | --- |
# | **actually filled** | TP | FN |
# | **actually empty** | FP | TN |
#
# accuracy = (TP + TN) / all, precision = TP / (TP + FP), recall = TP / (TP + FN),
# specificity = TN / (TN + FP), F1 = 2 x precision x recall / (precision + recall).

# %%
# %include algorithms/evaluation.py


def scores_of(model, X):
    """A continuous score for ROC analysis: class-1 probability, or the signed distance to the boundary."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    return model.decision_function(X)


def evaluate_split(model, X, y, train, test):
    m = clone(model)
    t0 = time.perf_counter()
    m.fit(X[train], y[train])
    fit_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    pred = m.predict(X[test])
    predict_ms = (time.perf_counter() - t0) / len(test) * 1000
    score = scores_of(m, X[test])
    out = metrics_from_counts(*confusion_counts(y[test], pred))
    out.update(auc=roc_auc_score(y[test], score), fit_s=fit_s, predict_ms=predict_ms, size_kb=len(pickle.dumps(m)) / 1024)
    return out, pred, score


def evaluate_cv(model, X, y, groups=None, n_splits=5):
    """Mean metrics over the folds, plus the pooled out-of-fold predictions and scores."""
    if groups is None:
        splits = StratifiedKFold(n_splits, shuffle=True, random_state=SEED).split(X, y)
    else:
        splits = StratifiedGroupKFold(n_splits, shuffle=True, random_state=SEED).split(X, y, groups)
    folds, pred_all, score_all = [], np.zeros(len(y), dtype=int), np.zeros(len(y))
    for train, test in splits:
        out, pred_all[test], score_all[test] = evaluate_split(model, X, y, train, test)
        folds.append(out)
    folds = pd.DataFrame(folds)
    summary = folds.mean().to_dict()
    summary["balanced_acc_std"] = float(folds["balanced_acc"].std())
    summary["f1_std"] = float(folds["f1"].std())
    return summary, pred_all, score_all


# The hand-written formulas agree with scikit-learn's confusion matrix.
_check = LogisticRegression(max_iter=2000).fit(StandardScaler().fit_transform(XA[past]), yA[past])
_pred = _check.predict(StandardScaler().fit(XA[past]).transform(XA[future]))
tn_, fp_, fn_, tp_ = confusion_matrix(yA[future], _pred).ravel()
assert confusion_counts(yA[future], _pred) == (tp_, fn_, fp_, tn_)
print("confusion_counts matches sklearn.metrics.confusion_matrix")

# %% [markdown]
# ## 8.2 Decision tree: entropy, information gain (ID3) and gain ratio (C4.5)
#
# **What it is.** A tree of questions about the attributes. At each node the algorithm picks the attribute that
# makes the classes purest.
#
# - **Entropy** of a node: `H = -sum p_c log2 p_c`. It is 0 for a pure node and 1 for a 50/50 node.
# - **ID3** picks the attribute with the highest **information gain**: entropy before the split minus the
#   weighted entropy after it.
# - Information gain favours attributes with many distinct values (an ID-like attribute splits the data into
#   tiny pure groups). **C4.5** corrects this with the **gain ratio**: information gain divided by the *split
#   information*, the entropy of the split itself.
#
# **Why it is needed here.** A tree produces if-then rules that can be set beside FormTrap's 14 hand-written
# rules.
#
# **Implementation.** Entropy, information gain and gain ratio are computed from scratch for the root node on
# the discretized attributes. Two attributes with many values are included on purpose to show the bias.

# %%
# %include algorithms/decision_tree.py


d_a = df.iloc[rows_a]
candidates = pd.DataFrame({
    "length bin": d_a["len_bin"].astype(str),
    "url bin": d_a["url_bin"].astype(str),
    "script": d_a["script"],
    "name is joined": d_a["name_joined"],
    "e-mail type": np.select([d_a["has_email"].eq(0), d_a["email_free"].eq(1), d_a["email_ru"].eq(1)],
                             ["none", "free mail", "russian"], default="other"),
    "phone format": np.select([d_a["has_phone"].eq(0), d_a["phone_ru_format"].eq(1)], ["none", "russian"], default="other"),
    "money keyword": d_a["kw_money"],
    "e-mail domain (many values)": d_a["email_domain"],
    "template id (almost unique)": groups_a,
}).reset_index(drop=True)

print(f"entropy of the root node: {entropy_of(yA):.4f} bits ({yA.mean():.1%} filled)")
root = pd.DataFrame({c: split_measures(candidates[c].to_numpy(), yA) for c in candidates}).T
root["distinct values"] = root["distinct values"].astype(int)
display(root.sort_values("information gain", ascending=False))
# information gain is the mutual information between attribute and label (scikit-learn reports it in nats)
assert np.isclose(root.loc["url bin", "information gain"], mutual_info_score(candidates["url bin"], yA) / math.log(2))
id3_choice, c45_choice = root["information gain"].idxmax(), root["gain ratio"].idxmax()
print(f"ID3 would split on: {id3_choice}   |   C4.5 would split on: {c45_choice}")
METRICS["tree_root"] = {"root_entropy": entropy_of(yA), "id3_choice": id3_choice, "c45_choice": c45_choice,
                        "table": root.reset_index().rename(columns={"index": "attribute"}).to_dict("records")}

# %% [markdown]
# The template id has the highest information gain of all: with thousands of values, each branch holds one or
# two rows and is trivially pure. A tree built on it would memorise the training data and predict nothing for a
# new template. Its split information is equally large, so its gain ratio drops and C4.5 picks a real attribute.
# This is the "ID3 fails" case from the lectures, on real data.
#
# The full tree below is built with scikit-learn. Its algorithm is CART (binary splits on numeric thresholds)
# with the entropy criterion, so each split is chosen by information gain as in ID3, but it is not a literal ID3
# or C4.5 tree. Depth is the main control against over-fitting, and it is tuned next.
#
# ## 8.3 Tuning on the training period: tree depth and K for KNN
#
# **KNN, what it is.** To classify a new point, find the K training points nearest to it and take a majority
# vote. There is no training step; the stored data is the model. **Why here:** "a submission behaves like the
# submissions it resembles" is exactly the campaign idea of Section 7, used for prediction. It depends directly
# on the distance measures of Section 3, which is why scaling matters so much for it.

# %%
def tune(make_model, values, X, y, groups):
    rows = []
    for v in values:
        model = make_model(v)
        cv_summary, _, _ = evaluate_cv(model, X, y, groups)
        fitted = clone(model).fit(X, y)
        train_ba = metrics_from_counts(*confusion_counts(y, fitted.predict(X)))["balanced_acc"]
        rows.append({"value": str(v), "train": train_ba, "validation": cv_summary["balanced_acc"]})
    return pd.DataFrame(rows)


depth_scan = tune(lambda d: DecisionTreeClassifier(criterion="entropy", max_depth=d, random_state=SEED),
                  [1, 2, 3, 4, 5, 6, 8, 10, None], XA[past], yA[past], groups_a[past])
k_scan_knn = tune(lambda k: make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=k)),
                  [1, 3, 5, 7, 9, 15, 25, 41], XA[past], yA[past], groups_a[past])
best_depth = depth_scan.loc[depth_scan["validation"].idxmax(), "value"]
DEPTH = None if best_depth == "None" else int(best_depth)
KNN_K = int(k_scan_knn.loc[k_scan_knn["validation"].idxmax(), "value"])
print(f"chosen tree depth: {DEPTH} | chosen K: {KNN_K}")

fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.0), sharey=True)
for ax, scan, title, xlabel in [(axes[0], depth_scan, "Decision tree: deeper trees memorise", "maximum depth"),
                                (axes[1], k_scan_knn, "KNN: K = 1 memorises", "K (number of neighbours)")]:
    xs = range(len(scan))
    ax.plot(xs, scan["train"], color=C[1], marker="o", label="training rows")
    ax.plot(xs, scan["validation"], color=C[0], marker="o", label="held-out folds")
    ax.set_xticks(xs, scan["value"])
    ax.set_xlabel(xlabel)
    ax.set_title(title)
axes[0].set_ylabel("balanced accuracy")
axes[0].legend(loc="lower right")
savefig("fig_tuning")

# %% [markdown]
# The gap between the two lines is over-fitting: training accuracy keeps rising with depth (and is perfect for
# K = 1, where every point is its own nearest neighbour) while accuracy on held-out folds levels off or falls.
# The values that are best on the held-out folds are used from here on.
#
# ## 8.4 KNN from scratch

# %%
# %include algorithms/knn.py


scaler = StandardScaler().fit(XA[past])
Ztr, Zte = scaler.transform(XA[past]), scaler.transform(XA[future][:300])
mine, tied = knn_predict(Ztr, yA[past], Zte, KNN_K)
theirs = KNeighborsClassifier(n_neighbors=KNN_K).fit(Ztr, yA[past]).predict(Zte)
print(f"from-scratch KNN agrees with scikit-learn on {np.mean(mine == theirs):.1%} of 300 test rows; "
      f"{tied.sum()} rows have a distance tie at the K-th neighbour (identical feature vectors), "
      f"where the choice of neighbour is arbitrary")
assert (mine == theirs)[~tied].all()

# Scaling matters for a distance-based method.
raw_cols = df[TEXT_F + CONTACT_F].iloc[rows_a].to_numpy(dtype=float)
unscaled, _, _ = evaluate_cv(KNeighborsClassifier(n_neighbors=KNN_K), raw_cols, yA, groups_a)
scaled, _, _ = evaluate_cv(make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=KNN_K)), XA, yA, groups_a)
knn_scaling = {"raw features": unscaled["balanced_acc"], "log + standardized": scaled["balanced_acc"]}
print("KNN balanced accuracy (5-fold):", {k: round(v, 3) for k, v in knn_scaling.items()})

# %% [markdown]
# ## 8.5 Mahalanobis distance classifier
#
# **What it is.** Assign a point to the class whose mean is nearest, measuring distance with
# `d(x, mu) = sqrt((x - mu)^T S^-1 (x - mu))`, where S is the covariance matrix of that class. Dividing by the
# covariance removes the effect of scale and of correlation between features; with S = identity it reduces to
# Euclidean distance.
#
# **Why it is needed here.** The features are strongly correlated (Section 2.2). Euclidean distance to a class
# mean counts correlated features twice; Mahalanobis distance does not.
#
# **Implementation.** From scratch, following the lecture steps: mean vector per class, covariance matrix per
# class, inverse, distance of the new point to each class, decision. It runs on PCA components because the raw
# covariance matrix is singular (Section 6).

# %%
# %include algorithms/mahalanobis.py


prep_pca = make_pipeline(StandardScaler(), PCA(0.90)).fit(XA[past])
Ptr, Pte = prep_pca.transform(XA[past]), prep_pca.transform(XA[future])
maha = MahalanobisClassifier().fit(Ptr, yA[past])
d_one = maha.distances(Pte[:1])[0]
print(f"{Ptr.shape[1]} PCA components. One test point: distance to class 'empty' = {d_one[0]:.2f}, "
      f"to class 'filled' = {d_one[1]:.2f}  ->  predicted {'filled' if d_one[1] < d_one[0] else 'empty'}, "
      f"actual {'filled' if yA[future][0] else 'empty'}")
maha_cv, _, _ = evaluate_cv(make_pipeline(StandardScaler(), PCA(0.90), MahalanobisClassifier()), XA, yA, groups_a)
eucl_cv, _, _ = evaluate_cv(make_pipeline(StandardScaler(), PCA(0.90), NearestCentroid()), XA, yA, groups_a)
maha_vs_eucl = {"Mahalanobis nearest mean": maha_cv["balanced_acc"], "Euclidean nearest mean": eucl_cv["balanced_acc"]}
print("balanced accuracy (5-fold):", {k: round(v, 3) for k, v in maha_vs_eucl.items()})

from scipy.spatial.distance import mahalanobis as scipy_mahalanobis
assert np.isclose(d_one[1], scipy_mahalanobis(Pte[0], maha.means_[1], maha.inv_covs_[1]))
print("the from-scratch distance equals scipy.spatial.distance.mahalanobis")

# %% [markdown]
# ### What PCA does to the other models
#
# The Mahalanobis classifier cannot run without PCA here, because the covariance matrix of the raw features is
# singular. KNN and logistic regression can, so the same models are scored on all 45 standardized features and
# on the principal components that keep 90% of the variance.

# %%
pca_effect = {}
for name, clf in [("KNN", KNeighborsClassifier(n_neighbors=KNN_K)), ("Logistic regression", LogisticRegression(max_iter=2000))]:
    full, _, _ = evaluate_cv(make_pipeline(StandardScaler(), clone(clf)), XA, yA, groups_a)
    reduced, _, _ = evaluate_cv(make_pipeline(StandardScaler(), PCA(0.90), clone(clf)), XA, yA, groups_a)
    pca_effect[name] = {"all 45 features": full["balanced_acc"], "PCA, 90% of variance": reduced["balanced_acc"],
                        "AUC, all features": full["auc"], "AUC, PCA": reduced["auc"]}
display(pd.DataFrame(pca_effect).T)

# %% [markdown]
# **Analysis.** KNN scores the same with and without PCA: the directions PCA removed carried nothing its
# distances used, which is what redundancy means. Logistic regression loses about two points, because it can
# still draw on small-variance directions that PCA throws away. PCA is therefore applied only where it is
# required: the Mahalanobis classifier, whose covariance matrix it makes invertible, and the Gaussian mixture.
#
# ## 8.6 Naive Bayes: which variant?
#
# **What it is.** Bayes' theorem with the "naive" assumption that features are independent given the class:
# `P(class | x) is proportional to P(class) x product of P(x_i | class)`. The class with the larger product
# wins.
#
# **Which variant.** The likelihood `P(x_i | class)` must match the type of feature: **Gaussian** for continuous
# values, **Bernoulli** for yes/no flags, **Multinomial** for word counts (used in Task B). Task A mixes
# continuous and binary features, so both candidates are tried.

# %%
bin_idx = [FEATURES.index(c) for c in BINARY_F]
nb_variants = {
    "Gaussian NB, all 45 features": make_pipeline(StandardScaler(), GaussianNB()),
    "Bernoulli NB, the 25 binary features": make_pipeline(ColumnTransformer([("binary", "passthrough", bin_idx)]), BernoulliNB(alpha=1.0)),
}
nb_cmp = {name: evaluate_cv(m, XA, yA, groups_a)[0] for name, m in nb_variants.items()}
display(pd.DataFrame(nb_cmp).T[["accuracy", "recall", "specificity", "balanced_acc", "auc"]])
best_nb = max(nb_cmp, key=lambda n: nb_cmp[n]["balanced_acc"])
print("variant used in the comparison:", best_nb)

# %% [markdown]
# ## 8.7 Logistic regression
#
# **What it is.** A linear model for classification. It computes a weighted sum `z = w . x + b` and passes it
# through the sigmoid, `p = 1 / (1 + e^-z)`, which turns any number into a probability between 0 and 1. The class
# is "filled" when `p` reaches a threshold, 0.5 by default. The weights are chosen to make the training labels as
# probable as possible.
#
# **Type of learning.** Supervised classification. Despite its name it predicts a class; the "regression" is a
# linear model of the log-odds, `ln(p / (1 - p)) = z`.
#
# **Why it is needed here.** It outputs a probability, so the operator can decide how strict the filter should
# be. It has one weight per feature, which can be read and set beside FormTrap's hand-picked weights. And it is
# the natural reference for the perceptron and the MLP that follow: the same linear form, trained on a smooth
# loss instead of a count of mistakes.
#
# **Implementation.** scikit-learn, on standardized features. The sigmoid for one row is worked by hand and
# checked, as in the lectures, together with the reverse question (which `z` gives a chosen probability).

# %%
lr_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
lr_fit = clone(lr_model).fit(XA[past], yA[past])
x_row = lr_fit[0].transform(XA[future][:1])[0]                               # one standardized test row
z_row = float(x_row @ lr_fit[-1].coef_[0] + lr_fit[-1].intercept_[0])        # weighted sum
p_row = 1 / (1 + math.exp(-z_row))                                           # sigmoid
assert np.isclose(p_row, lr_fit.predict_proba(XA[future][:1])[0, 1])
print(f"one test row: z = w.x + b = {z_row:.3f}  ->  p = 1 / (1 + e^-z) = {p_row:.3f}  ->  "
      f"predicted {'filled' if p_row >= 0.5 else 'empty'} at threshold 0.5")
print(f"the reverse question: a probability of 0.90 needs z = ln(0.9 / 0.1) = {math.log(0.9 / 0.1):.3f}")

_, _, lr_oof = evaluate_cv(lr_model, XA, yA, groups_a)                       # out-of-fold probabilities
lr_thresholds = []
for threshold in (0.3, 0.4, 0.5, 0.6, 0.7):
    out = metrics_from_counts(*confusion_counts(yA, (lr_oof >= threshold).astype(int)))
    lr_thresholds.append({"threshold": threshold, "precision": out["precision"], "recall": out["recall"],
                          "specificity": out["specificity"], "balanced_acc": out["balanced_acc"]})
lr_thresholds = pd.DataFrame(lr_thresholds)
display(lr_thresholds)

# %% [markdown]
# **Analysis.** The table is the reason a probability is worth having. Moving the threshold trades recall
# against specificity, and the operator can pick the row that matches the cost of each kind of error. A model
# that outputs only a decision offers a single row. The weights themselves are shown in Section 8.11.
#
# ## 8.8 Perceptron and multi-layer network
#
# **What it is.** A perceptron computes a weighted sum of the inputs plus a bias and outputs 1 if the sum is
# positive. Training shows it one pattern at a time and, when it is wrong, moves the weights toward the correct
# answer: `w <- w + eta (target - output) x`. It can only draw a straight boundary. A multi-layer perceptron
# (MLP) puts a layer of such units in between and can draw curved boundaries.
#
# **Why it is needed here.** To test whether a non-linear model reads these features better than the linear
# ones, and at what cost in size and time.

# %%
# %include algorithms/perceptron.py


w_p, b_p, err_hist = perceptron_train(Ztr, yA[past])
Zfu = scaler.transform(XA[future])
mine_p = (Zfu @ w_p + b_p > 0).astype(int)
sk_p = Perceptron(random_state=SEED).fit(Ztr, yA[past]).predict(Zfu)
perceptron_check = {"from scratch": metrics_from_counts(*confusion_counts(yA[future], mine_p))["balanced_acc"],
                    "scikit-learn": metrics_from_counts(*confusion_counts(yA[future], sk_p))["balanced_acc"]}
print("wrong patterns per epoch:", err_hist)
print("balanced accuracy on 2024-2025:", {k: round(v, 3) for k, v in perceptron_check.items()})
print("the error count never reaches 0: the two classes are not linearly separable in these features")

# Learning curves: the perceptron's mistakes per pass, and the MLP's training loss per iteration.
mlp_demo = make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32,), max_iter=800, random_state=SEED)).fit(XA[past], yA[past])
mlp_loss = mlp_demo[-1].loss_curve_
fig, axes = plt.subplots(1, 2, figsize=(8.8, 2.9))
axes[0].plot(range(1, len(err_hist) + 1), err_hist, color=C[0], marker="o", markersize=4)
axes[0].set_ylim(0, max(err_hist) * 1.2)
axes[0].set_xlabel("pass over the training rows")
axes[0].set_ylabel("misclassified patterns")
axes[0].set_title("Perceptron: the error count does not settle")
axes[1].plot(range(1, len(mlp_loss) + 1), mlp_loss, color=C[0])
axes[1].set_ylim(0, max(mlp_loss) * 1.1)
axes[1].set_xlabel("iteration")
axes[1].set_ylabel("training loss")
axes[1].set_title("MLP: the training loss keeps falling")
savefig("fig_learning_curves")

mlp_fit = {"training rows 2020-2023": metrics_from_counts(*confusion_counts(yA[past], mlp_demo.predict(XA[past])))["balanced_acc"],
           "later rows 2024-2025": metrics_from_counts(*confusion_counts(yA[future], mlp_demo.predict(XA[future])))["balanced_acc"]}
lr_gap = {"training rows 2020-2023": metrics_from_counts(*confusion_counts(yA[past], lr_fit.predict(XA[past])))["balanced_acc"],
          "later rows 2024-2025": metrics_from_counts(*confusion_counts(yA[future], lr_fit.predict(XA[future])))["balanced_acc"]}
display(pd.DataFrame({"MLP": mlp_fit, "Logistic regression": lr_gap}).T)

# %% [markdown]
# **Analysis.** The two curves show two different failures. The perceptron's error count stays near 300 per
# pass and never falls: a single straight boundary cannot separate these classes, and each correction undoes an
# earlier one. The MLP drives its training loss steadily down, and the table shows what that buys: it fits the
# rows it was trained on far better than logistic regression does and is at chance on the later period, where
# logistic regression keeps most of its score. The extra capacity was spent on the particular campaigns of
# 2020-2023.
#
# ## 8.9 All models under one protocol

# %%
class UrlRule(ClassifierMixin, BaseEstimator):
    """Hand-written baseline: a message with at least one URL is predicted to fill the honeypot."""

    def __init__(self, column=0):
        self.column = column

    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        return self

    def predict_proba(self, X):
        p = (X[:, self.column] > 0).astype(float)
        return np.column_stack([1 - p, p])

    def predict(self, X):
        return (X[:, self.column] > 0).astype(int)


MODELS_A = {
    "Baseline: majority class": DummyClassifier(strategy="most_frequent"),
    "Baseline: rule 'has a URL'": UrlRule(FEATURES.index("url_count")),
    "Naive Bayes": nb_variants[best_nb],
    "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "Decision tree": DecisionTreeClassifier(criterion="entropy", max_depth=DEPTH, random_state=SEED),
    "KNN": make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=KNN_K)),
    "Mahalanobis (PCA)": make_pipeline(StandardScaler(), PCA(0.90), MahalanobisClassifier()),
    "Perceptron": make_pipeline(StandardScaler(), Perceptron(random_state=SEED)),
    "MLP (one hidden layer)": make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(32,), max_iter=800, random_state=SEED)),
}
COLS = ["accuracy", "precision", "recall", "specificity", "f1", "balanced_acc", "auc"]
cv_a, ts_a, oof_a, oof_pred_a, ts_scores_a, ts_pred_a = {}, {}, {}, {}, {}, {}
train_idx, test_idx = np.where(past)[0], np.where(future)[0]
for name, model in MODELS_A.items():
    cv_a[name], oof_pred_a[name], oof_a[name] = evaluate_cv(model, XA, yA, groups_a)
    ts_a[name], ts_pred_a[name], ts_scores_a[name] = evaluate_split(model, XA, yA, train_idx, test_idx)
cv_a, ts_a = pd.DataFrame(cv_a).T, pd.DataFrame(ts_a).T
print("Grouped 5-fold cross-validation (mean over folds)")
display(cv_a[COLS + ["balanced_acc_std"]])
print("Time split: trained on 2020-2023, tested on 2024-2025")
display(ts_a[COLS])
print("Cost (time split)")
display(ts_a[["fit_s", "predict_ms", "size_kb"]].rename(columns={"fit_s": "training time (s)", "predict_ms": "prediction (ms per row)", "size_kb": "model size (KB)"}))

# %%
order = cv_a["balanced_acc"].sort_values(ascending=False).index
fig, ax = plt.subplots(figsize=(7.4, 3.9))
ypos = np.arange(len(order))
for y, name in zip(ypos, order):
    ax.plot([cv_a.loc[name, "balanced_acc"], ts_a.loc[name, "balanced_acc"]], [y, y], color=AXIS, linewidth=2, zorder=1)
ax.scatter(cv_a.loc[order, "balanced_acc"], ypos, s=64, color=C[0], edgecolors="white", linewidths=1.5, label="5-fold cross-validation", zorder=2)
ax.scatter(ts_a.loc[order, "balanced_acc"], ypos, s=64, color=C[1], edgecolors="white", linewidths=1.5, label="trained on the past, tested on 2024-2025", zorder=2)
ax.set_yticks(ypos, order)
ax.invert_yaxis()
ax.grid(axis="y", visible=False)
ax.set_xlabel("balanced accuracy")
ax.set_xlim(0.45, 1.0)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
ax.set_title("Task A: every model loses accuracy on future data", pad=30)
savefig("fig_task_a_models")

# %%
learned = [m for m in order if not m.startswith("Baseline")]
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.9), sharey=True)
for ax, src, y_true, title in [(axes[0], oof_a, yA, "ROC, cross-validation (out-of-fold)"),
                               (axes[1], ts_scores_a, yA[future], "ROC, tested on 2024-2025")]:
    for colour, name in zip(C, learned):
        fpr, tpr, _ = roc_curve(y_true, src[name])
        ax.plot(fpr, tpr, color=colour, linewidth=1.6, label=f"{name} ({roc_auc_score(y_true, src[name]):.2f})")
    ax.plot([0, 1], [0, 1], color=AXIS, linewidth=1)
    ax.set_xlabel("false positive rate (1 - specificity)")
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=7.5, title="model (AUC)", title_fontsize=8)
axes[0].set_ylabel("true positive rate (recall)")
savefig("fig_task_a_roc")

# %% [markdown]
# ## 8.10 What trusting the recorded label would have done
#
# Section 1.3 removed the twelve-month window in which the form had no honeypot. The same fitted models
# are scored here on the 2024-2025 rows *as recorded*, with every window row counted as "left empty".

# %%
rec_rows = np.where(df["honeypot_recorded"].notna() & (df["year"] >= 2024))[0]
X_rec = X_all.iloc[rec_rows].to_numpy(dtype=float)
y_rec = df["honeypot_recorded"].iloc[rec_rows].astype(int).to_numpy()
recorded = {}
for name in learned:
    m = clone(MODELS_A[name]).fit(XA[past], yA[past])
    out = metrics_from_counts(*confusion_counts(y_rec, m.predict(X_rec)))
    recorded[name] = {"balanced acc, usable labels": ts_a.loc[name, "balanced_acc"], "balanced acc, as recorded": out["balanced_acc"],
                      "specificity, usable labels": ts_a.loc[name, "specificity"], "specificity, as recorded": out["specificity"]}
recorded = pd.DataFrame(recorded).T.astype(float)
print(f"test rows with usable labels: {future.sum():,} | test rows as recorded: {len(y_rec):,} "
      f"({(y_rec == 0).sum():,} 'empty', of which {int(in_window.sum()):,} are window rows)")
display(recorded)

# %% [markdown]
# Trusting the recorded label changes the picture in three ways. The test set becomes almost three times
# larger. Its class balance flips, from about 80% "filled" to about 30%. And most models score 5 to 14 points
# *higher*, because the window adds hundreds of rows labelled "empty" that the models happen to call "empty".
# The conclusions about which model works, and about how often the honeypot is evaded, would rest on rows whose
# label says nothing about the sender. The figures with usable labels are the ones reported from here on.
#
# ## 8.11 What the models learned

# %%
best_a = ts_a.loc[learned, "balanced_acc"].idxmax()
print(f"best model on the time split: {best_a}")
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
for ax, (y_true, y_pred, title) in zip(axes, [(yA, oof_pred_a[best_a], "cross-validation"),
                                                (yA[future], ts_pred_a[best_a], "tested on 2024-2025")]):
    tp, fn, fp, tn = confusion_counts(y_true, y_pred)
    cm = np.array([[tp, fn], [fp, tn]])
    ax.imshow(cm, cmap=SEQ, vmin=0, vmax=cm.max() * 1.25)
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, f"{v:,}", ha="center", va="center", fontsize=11, color="white" if v > cm.max() * 0.55 else INK)
    ax.set_xticks([0, 1], ["pred. filled", "pred. empty"])
    ax.set_yticks([0, 1], ["actual filled", "actual empty"])
    ax.grid(False)
    ax.set_title(f"{best_a}, {title}", fontsize=9.5)
savefig("fig_task_a_confusion")

# %%
tree3 = DecisionTreeClassifier(criterion="entropy", max_depth=3, random_state=SEED).fit(XA[past], yA[past])
print("Decision tree limited to depth 3, trained on 2020-2023 (count features are on a log(1 + x) scale):\n")
print(export_text(tree3, feature_names=FEATURES, decimals=2))

full_tree = clone(MODELS_A["Decision tree"]).fit(XA[past], yA[past])
importance = pd.Series(full_tree.feature_importances_, index=FEATURES).sort_values(ascending=False).head(8)
lr = clone(MODELS_A["Logistic regression"]).fit(XA[past], yA[past])
coef = pd.Series(lr[-1].coef_[0], index=FEATURES)
top_coef = coef.reindex(coef.abs().sort_values(ascending=False).index).head(10)

fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6))
barh(axes[0], importance.index, importance.values, xlabel="share of the tree's information gain")
axes[0].set_title("Decision tree: feature importance")
colours = [C[0] if v > 0 else C[1] for v in top_coef.values]
axes[1].barh(list(top_coef.index), top_coef.values, color=colours, height=0.62)
axes[1].axvline(0, color=AXIS, linewidth=1)
axes[1].invert_yaxis()
axes[1].grid(axis="y", visible=False)
axes[1].set_xlabel("standardized coefficient")
axes[1].set_title("Logistic regression: largest weights")
axes[1].legend(handles=[plt.Rectangle((0, 0), 1, 1, color=C[0]), plt.Rectangle((0, 0), 1, 1, color=C[1])],
               labels=["pushes toward 'filled'", "pushes toward 'empty'"], loc="lower right", fontsize=8)
savefig("fig_task_a_explain")

# %%
# Error analysis for the best model on the future period.
err = df.iloc[rows_a[test_idx]].assign(pred=ts_pred_a[best_a], actual=yA[future])
err["outcome"] = np.select([(err["pred"] == 1) & (err["actual"] == 1), (err["pred"] == 0) & (err["actual"] == 0),
                            (err["pred"] == 1) & (err["actual"] == 0)], ["TP", "TN", "FP"], default="FN")
print("\noutcomes on 2024-2025 by year:")
display(pd.crosstab(err["year"].astype(int), err["outcome"]))
for kind, text in [("FP", "predicted 'filled' but the honeypot was left empty"), ("FN", "predicted 'empty' but the honeypot was filled")]:
    part = err[err["outcome"] == kind]
    print(f"\n{kind} ({len(part)} rows): {text}. Typical cases:")
    for msg, n in part["message"].str[:90].str.replace("\n", " ").value_counts().head(3).items():
        print(f"   x{n}  {msg!r}")

METRICS["task_a"] = {
    "rows": int(len(yA)), "features": int(XA.shape[1]), "train_rows": int(past.sum()), "test_rows": int(future.sum()),
    "positive_rate": float(yA.mean()), "positive_rate_train": float(yA[past].mean()), "positive_rate_test": float(yA[future].mean()),
    "tree_depth": DEPTH, "knn_k": KNN_K, "naive_bayes_variant": best_nb,
    "nb_variants": {k: v["balanced_acc"] for k, v in nb_cmp.items()},
    "knn_scaling": knn_scaling, "mahalanobis_vs_euclidean": maha_vs_eucl, "perceptron_check": perceptron_check,
    "pca_effect": pca_effect, "lr_thresholds": lr_thresholds.to_dict("records"),
    "mlp_train_vs_later": mlp_fit, "lr_train_vs_later": lr_gap,
    "depth_scan": depth_scan.to_dict("records"), "knn_scan": k_scan_knn.to_dict("records"),
    "cv": cv_a.reset_index().rename(columns={"index": "model"}).to_dict("records"),
    "time_split": ts_a.reset_index().rename(columns={"index": "model"}).to_dict("records"),
    "best_model_time_split": best_a,
    "tree_importance": importance.to_dict(), "lr_top_coefficients": top_coef.to_dict(),
    "as_recorded": recorded.reset_index().rename(columns={"index": "model"}).to_dict("records"),
    "as_recorded_test_rows": int(len(y_rec)),
}
