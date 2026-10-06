# %% [markdown]
# # 6. Dimensionality reduction with PCA
#
# **What it is.** Principal component analysis finds new axes (principal components) that are uncorrelated and
# ordered by how much of the data's variance they carry. Keeping the first few components keeps most of the
# information in fewer dimensions.
#
# **Type of learning.** Unsupervised: the labels are not used.
#
# **Why it is needed here.** Section 2.2 showed groups of features that say the same thing. Redundant features
# (1) are counted several times in every distance, which hurts KNN and K-means, (2) make the covariance matrix
# singular, so it cannot be inverted for the Mahalanobis classifier, and (3) cannot be plotted in two
# dimensions.
#
# **Implementation.** The five steps from the lectures: centre the data, compute the covariance matrix, find its
# eigenvalues, find the eigenvectors, project. First on two features by hand, then on the full matrix, checked
# against scikit-learn.

# %%
# Worked example with two correlated features and six messages.
small = X_all.loc[df["has_message"] == 1, ["msg_len", "word_count"]].iloc[[0, 5, 9, 14, 20, 40]].to_numpy()
mean = small.mean(axis=0)                                     # step 1: feature means, then centre
centred = small - mean
cov = centred.T @ centred / (len(small) - 1)                  # step 2: covariance matrix
a_, b_, d_ = cov[0, 0], cov[0, 1], cov[1, 1]
lam1 = ((a_ + d_) + math.sqrt((a_ - d_) ** 2 + 4 * b_ ** 2)) / 2    # step 3: roots of det(cov - lambda I) = 0
lam2 = ((a_ + d_) - math.sqrt((a_ - d_) ** 2 + 4 * b_ ** 2)) / 2
v1 = np.array([b_, lam1 - a_])                                # step 4: solve (cov - lambda1 I) v = 0, then normalize
v1 = v1 / np.linalg.norm(v1)
pc1 = centred @ v1                                            # step 5: project every row on PC 1
print("covariance matrix:\n", cov.round(4))
print(f"eigenvalues: {lam1:.4f}, {lam2:.4f}  ->  PC 1 keeps {lam1 / (lam1 + lam2):.1%} of the variance")
print("first eigenvector:", v1.round(4))
print("2-D data becomes 1-D:", pc1.round(3))
assert np.allclose(sorted([lam1, lam2]), np.linalg.eigvalsh(cov))

# %%
from sklearn.decomposition import PCA


def pca_scratch(Z):
    """Eigen-decomposition of the covariance matrix. Returns eigenvalues, eigenvectors (columns) and scores."""
    Zc = Z - Z.mean(axis=0)
    cov = Zc.T @ Zc / (len(Z) - 1)
    values, vectors = np.linalg.eigh(cov)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    return values, vectors, Zc @ vectors


eigvals, eigvecs, scores = pca_scratch(Z_all)
ratio = eigvals / eigvals.sum()
cum = np.cumsum(ratio)
pca_ref = PCA().fit(Z_all)
assert np.allclose(eigvals, pca_ref.explained_variance_, atol=1e-8)
assert np.allclose(np.abs(eigvecs[:, :5].T), np.abs(pca_ref.components_[:5]), atol=1e-6)
N90, N95 = int(np.searchsorted(cum, 0.90) + 1), int(np.searchsorted(cum, 0.95) + 1)
print(f"from-scratch PCA matches scikit-learn. {Z_all.shape[1]} features -> {N90} components keep 90% of the "
      f"variance, {N95} keep 95%; the last {int((eigvals < 1e-8).sum())} eigenvalue(s) are zero (exact redundancy)")
METRICS["pca"] = {"features": int(Z_all.shape[1]), "components_90": N90, "components_95": N95,
                  "pc1_ratio": float(ratio[0]), "pc2_ratio": float(ratio[1])}

fig, ax = plt.subplots(figsize=(6.4, 3.0))
ax.plot(range(1, len(cum) + 1), cum * 100, color=C[0], marker="o", markersize=4)
ax.axhline(90, color=AXIS, linewidth=1)
ax.annotate(f"{N90} components reach 90%", (N90, 90), xytext=(N90 + 2, 78), fontsize=9, color=INK2,
            arrowprops={"arrowstyle": "-", "color": MUTED})
ax.set_xlabel("number of principal components")
ax.set_ylabel("cumulative variance explained (%)")
ax.set_ylim(0, 104)
ax.set_title(f"{N90} of {Z_all.shape[1]} dimensions carry 90% of the variance")
savefig("fig_pca_variance")

# %%
loadings = pd.DataFrame(eigvecs[:, :2], index=FEATURES, columns=["PC1", "PC2"])
for pc in ["PC1", "PC2"]:
    top = loadings[pc].reindex(loadings[pc].abs().sort_values(ascending=False).index).head(7)
    print(f"{pc} ({ratio[int(pc[2]) - 1]:.1%} of variance), strongest loadings:")
    print("   " + ", ".join(f"{f} ({v:+.2f})" for f, v in top.items()))

status = df["honeypot_filled"].map({1.0: "honeypot filled", 0.0: "honeypot empty"}).fillna("label unknown")
fig, ax = plt.subplots(figsize=(6.4, 4.4))
for name, colour, z in [("label unknown", GRAY, 1), ("honeypot filled", C[0], 2), ("honeypot empty", C[1], 3)]:
    m = (status == name).to_numpy()
    ax.scatter(scores[m, 0], scores[m, 1], s=12, color=colour, alpha=0.55, linewidths=0, label=f"{name} ({m.sum():,})", zorder=z)
ax.set_xlabel(f"PC 1 ({ratio[0]:.0%} of variance)")
ax.set_ylabel(f"PC 2 ({ratio[1]:.0%} of variance)")
ax.legend(loc="best", markerscale=2)
ax.set_title("Submissions projected on the first two principal components")
savefig("fig_pca_scatter")

# %% [markdown]
# **Analysis.**
#
# - The eigenvalue curve confirms the redundancy seen in the correlation matrix: far fewer components than
#   features are needed for 90% of the variance, and the smallest eigenvalue is zero because the one-hot script
#   columns always sum to 1.
# - The loadings give the components a meaning. PC 1 is dominated by the contact-field features (whether an
#   e-mail and phone were given), with message length pulling the other way: it separates "contact fields
#   filled, short message" from "contact fields empty, long message". PC 2 contrasts submissions that carry an
#   ordinary Latin-script message and a name with submissions that have no readable text.
# - In the projection the two honeypot outcomes occupy different regions but overlap, so the label is
#   learnable from these features and not trivially so. Section 8 measures how well.
# - PCA is used below wherever a method needs uncorrelated, non-redundant inputs: the Mahalanobis classifier
#   and the Gaussian mixture. Section 8.5 also measures what PCA does to KNN and logistic regression.
#
# # 7. Clustering: discovering spam campaigns
#
# **Type of learning.** Unsupervised. No campaign labels exist; the algorithms group messages by similarity
# alone.
#
# **Why it is needed here.** Section 3.3 showed that many templates are rewrites of one another. Grouping them
# lets an operator review a handful of campaigns instead of thousands of messages, and lets the software tell a
# new submission "you belong to campaign X".
#
# **Representation.** Each distinct template is a TF-IDF vector. Common English words and URL fragments
# (`https`, `com`, ...) are removed so that clusters form around content words. The vectors are reduced to 50
# dimensions by truncated SVD (the sparse-matrix relative of PCA, known as latent semantic analysis) and scaled
# to unit length, so that Euclidean distance between them orders pairs the same way cosine similarity does.

# %%
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer

STOP = sorted(ENGLISH_STOP_WORDS | {"https", "http", "www", "com", "href", "url", "html", "htm", "php", "ru",
                                    "net", "org", "email", "phone", "site", "name"})
tfidf_c = TfidfVectorizer(lowercase=True, min_df=3, max_df=0.4, max_features=20000, sublinear_tf=True,
                          stop_words=STOP, token_pattern=r"(?u)\b[^\W\d_]{2,}\b")
Tc_all = tfidf_c.fit_transform(tpl["message"])
has_vocab = np.asarray(Tc_all.getnnz(axis=1) > 0).ravel()
ct = tpl[has_vocab].reset_index(drop=True)            # templates that share vocabulary with others
Tc = Tc_all[has_vocab]
lsa = make_pipeline(TruncatedSVD(50, random_state=SEED), Normalizer())
L = lsa.fit_transform(Tc)
terms_c = np.array(tfidf_c.get_feature_names_out())
no_vocab = tpl[~has_vocab]
print(f"{len(ct):,} templates x {Tc.shape[1]:,} terms -> {L.shape[1]} LSA dimensions")
print(f"{len(no_vocab)} templates share no vocabulary with any other template and are kept as their own group; examples:")
for msg in no_vocab["message"].head(4):
    print("   ", msg[:70].replace("\n", " "))

# %% [markdown]
# ## 7.1 K-means
#
# **What it is.** Choose k centroids; assign every point to its nearest centroid; move each centroid to the mean
# of its points; repeat until nothing changes. It minimises the sum of squared distances (SSE) from points to
# their centroid.
#
# **Implementation.** From scratch on a sample of 500 templates with k = 4, then checked against scikit-learn
# started from the same initial centroids.

# %%
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


rng = np.random.default_rng(SEED)
sample_idx = rng.choice(len(L), 500, replace=False)
Xs = L[sample_idx]
init = Xs[rng.choice(len(Xs), 4, replace=False)]
labels_s, cent_s, sse_hist = kmeans_scratch(Xs, init)
ref = KMeans(4, init=init, n_init=1, algorithm="lloyd", tol=0, max_iter=100).fit(Xs)
print("SSE per iteration:", [round(v, 2) for v in sse_hist])
print(f"converged after {len(sse_hist)} iterations; agreement with scikit-learn (adjusted Rand index): "
      f"{adjusted_rand_score(labels_s, ref.labels_):.3f}")
assert adjusted_rand_score(labels_s, ref.labels_) > 0.99

# %% [markdown]
# ### Choosing k
#
# Two diagnostics are computed for each k: the **SSE** (the "elbow" plot) and the **silhouette coefficient**,
# which compares each point's distance to its own cluster with its distance to the nearest other cluster
# (1 = compact and separate, 0 = overlapping).

# %%
K_RANGE = list(range(4, 17, 2))
k_scan = []
for k in K_RANGE:
    km = KMeans(k, n_init=10, random_state=SEED).fit(L)
    k_scan.append({"k": k, "SSE": km.inertia_, "silhouette": silhouette_score(L, km.labels_, metric="cosine")})
k_scan = pd.DataFrame(k_scan)
display(k_scan)
K = int(k_scan.loc[k_scan["silhouette"].idxmax(), "k"])

fig, axes = plt.subplots(1, 2, figsize=(8.6, 2.9))
axes[0].plot(k_scan["k"], k_scan["SSE"], color=C[0], marker="o")
axes[0].set_title("Elbow: SSE falls steadily")
axes[0].set_xlabel("k")
axes[0].set_ylabel("SSE")
axes[1].plot(k_scan["k"], k_scan["silhouette"], color=C[0], marker="o")
axes[1].scatter([K], [k_scan["silhouette"].max()], s=110, facecolors="none", edgecolors=INK, linewidths=1.2, zorder=5)
axes[1].set_title(f"Silhouette: best of the range at k = {K}")
axes[1].set_xlabel("k")
axes[1].set_ylabel("silhouette (cosine)")
savefig("fig_kmeans_k")

# %%
kmeans = KMeans(K, n_init=10, random_state=SEED).fit(L)
ct["cluster"] = kmeans.labels_
tpl_cluster = dict(zip(ct["template_id"], ct["cluster"]))
tpl_cluster.update({t: -1 for t in no_vocab["template_id"]})
df["campaign"] = df["template_id"].map(tpl_cluster)            # NaN = no message


def profile(cluster_id):
    if cluster_id == -1:
        members, label, top_terms = no_vocab, "short / no shared vocabulary", []
        example = members["message"].iloc[0]
    else:
        idx = np.where(kmeans.labels_ == cluster_id)[0]
        members = ct.iloc[idx]
        top_terms = terms_c[np.asarray(Tc[idx].mean(axis=0)).ravel().argsort()[::-1][:6]].tolist()
        label = ", ".join(top_terms[:3])
        example = members["message"].iloc[int((L[idx] @ kmeans.cluster_centers_[cluster_id]).argmax())]
    rows = df[df["campaign"] == cluster_id]
    years = rows["year"].dropna()
    return {"campaign": int(cluster_id), "label": label, "templates": int(len(members)), "submissions": int(len(rows)),
            "honeypot_rate": float(rows["honeypot_filled"].mean()), "main_script": rows["script"].mode().iat[0],
            "first_year": int(years.min()) if len(years) else None, "last_year": int(years.max()) if len(years) else None,
            "top_terms": top_terms, "example": example[:160].replace("\n", " ")}


campaigns = pd.DataFrame([profile(j) for j in [-1] + list(range(K))]).sort_values("submissions", ascending=False)
campaigns = campaigns.reset_index(drop=True)
show(campaigns.drop(columns=["top_terms"]), pct=["honeypot_rate"])
km_sil = float(silhouette_score(L, kmeans.labels_, metric="cosine"))

names_c = [f"C{r.campaign}: {r.label}" if r.campaign >= 0 else r.label for r in campaigns.itertuples()]
fig, axes = plt.subplots(1, 2, figsize=(9.2, 0.33 * len(campaigns) + 1.2), sharey=True)
barh(axes[0], names_c, campaigns["submissions"], fmt="{:,.0f}", xlabel="submissions")
axes[0].set_title("Campaigns found by K-means")
barh(axes[1], names_c, campaigns["honeypot_rate"].fillna(0) * 100, fmt="{:.0f}%", xlabel="honeypot filled (%)")
axes[1].set_title("Honeypot hit rate per campaign")
savefig("fig_campaigns")

# %% [markdown]
# ## 7.2 K-medoids
#
# **What it is.** Like K-means, but the centre of each cluster must be one of the data points (the *medoid*: the
# member with the smallest total distance to the other members). It works with any distance, not only Euclidean.
#
# **Why it is needed here.** A K-means centroid is an average of many messages and cannot be read. A medoid is a
# real message, so the operator sees the campaign's actual template. A medoid is also not dragged around by
# extreme members the way a mean is.
#
# **Implementation.** From scratch, on a sample of 800 templates with cosine distance: initialise medoids,
# assign each point to the nearest medoid, then for each cluster pick the member with the lowest total distance
# to the rest. Five random starts; the lowest-cost run is kept.

# %%
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


rng = np.random.default_rng(SEED)
med_idx = rng.choice(len(L), 800, replace=False)
Lm = L[med_idx]
D = np.clip(1 - Lm @ Lm.T, 0, None)                         # cosine distance
np.fill_diagonal(D, 0)
runs = [kmedoids(D, K, rng) for _ in range(5)]
medoids, med_labels, med_cost = min(runs, key=lambda r: r[2])
print("total cost of the five starts:", [round(r[2], 1) for r in runs], "-> kept", round(med_cost, 1))

km_on_sample = kmeans.labels_[med_idx]
kmedoids_metrics = {
    "sample": int(len(Lm)),
    "silhouette_kmedoids": float(silhouette_score(D, med_labels, metric="precomputed")),
    "silhouette_kmeans_same_sample": float(silhouette_score(D, km_on_sample, metric="precomputed")),
    "ari_vs_kmeans": float(adjusted_rand_score(km_on_sample, med_labels)),
}
print(kmedoids_metrics)
medoid_tbl = pd.DataFrame({"cluster size": np.bincount(med_labels, minlength=K),
                           "medoid (a real message)": [ct["message"].iloc[med_idx[m]][:110].replace("\n", " ") for m in medoids]})
display(medoid_tbl.sort_values("cluster size", ascending=False).reset_index(drop=True))

# %% [markdown]
# ## 7.3 Expectation-Maximisation (Gaussian mixture)
#
# **What it is.** EM fits a model with a hidden variable. Here the hidden variable is "which group produced
# this point", and each group is a Gaussian. The **E-step** computes, for every point, the probability that it
# belongs to each group given the current parameters. The **M-step** re-estimates each group's parameters from
# those probabilities. The two steps repeat until the likelihood stops improving. It is the same logic as the
# two-coins example from the lectures, with Gaussians in place of coins.
#
# **Why it is needed here.** K-means and K-medoids give *hard* assignments. A spam message can borrow from two
# campaigns; EM gives every message a membership probability for every group.
#
# **Implementation.** First from scratch in one dimension (message length), then scikit-learn's
# `GaussianMixture` on the text representation.

# %%
x_len = np.log1p(df.loc[df["has_message"] == 1, "msg_len"].to_numpy(dtype=float))


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


mu0 = np.percentile(x_len, [25, 75])
sigma0 = np.array([x_len.std(), x_len.std()])
mu_em, sigma_em, w_em, ll_hist = em_two_gaussians(x_len, mu0, sigma0, np.array([0.5, 0.5]))
gm1 = GaussianMixture(2, means_init=mu0.reshape(-1, 1), weights_init=[0.5, 0.5],
                      precisions_init=(1 / sigma0 ** 2).reshape(-1, 1, 1), tol=1e-10, max_iter=1000,
                      reg_covar=1e-12).fit(x_len.reshape(-1, 1))
print(f"start: means {mu0.round(2)}  ->  after {len(ll_hist)} iterations: means {mu_em.round(3)}, "
      f"std {sigma_em.round(3)}, weights {w_em.round(3)}")
print("log-likelihood, first five iterations:", [round(v, 1) for v in ll_hist[:5]], "(it never decreases)")
print("scikit-learn means:", gm1.means_.ravel().round(3))
assert np.all(np.diff(ll_hist) > -1e-6)
assert np.allclose(np.sort(mu_em), np.sort(gm1.means_.ravel()), atol=0.05)

grid_x = np.linspace(x_len.min(), x_len.max(), 300)
fig, ax = plt.subplots(figsize=(6.4, 3.0))
ax.hist(x_len, bins=45, density=True, color=GRAY, rwidth=0.9)
for j, lab in enumerate(["group 1", "group 2"]):
    pdf = w_em[j] * np.exp(-0.5 * ((grid_x - mu_em[j]) / sigma_em[j]) ** 2) / (sigma_em[j] * np.sqrt(2 * np.pi))
    ax.plot(grid_x, pdf, color=C[j], label=f"{lab}: typical length {np.expm1(mu_em[j]):,.0f} characters, weight {w_em[j]:.2f}")
ax.set_xlabel("log(1 + message length)")
ax.set_ylabel("density")
ax.legend(loc="upper right")
ax.set_title("EM separates one-line messages from full adverts")
savefig("fig_em_length")

# %%
L10 = L[:, :10]
bic = []
for k in [4, 8, 12, 16, 20, 24]:
    g = GaussianMixture(k, covariance_type="diag", random_state=SEED, n_init=2).fit(L10)
    bic.append({"components": k, "BIC": g.bic(L10)})
bic = pd.DataFrame(bic)
display(bic.T)

gmm = GaussianMixture(K, covariance_type="diag", random_state=SEED, n_init=3).fit(L10)
resp = gmm.predict_proba(L10)
gmm_labels = resp.argmax(axis=1)
gmm_metrics = {
    "components": K,
    "ari_vs_kmeans": float(adjusted_rand_score(kmeans.labels_, gmm_labels)),
    "silhouette": float(silhouette_score(L, gmm_labels, metric="cosine")),
    "share_soft_below_0.9": float((resp.max(axis=1) < 0.9).mean()),
}
print(gmm_metrics)
between = np.argsort(resp.max(axis=1))[:3]
for i in between:
    top2 = resp[i].argsort()[::-1][:2]
    print(f"  shared between group {top2[0]} ({resp[i, top2[0]]:.2f}) and group {top2[1]} ({resp[i, top2[1]]:.2f}): "
          + ct["message"].iloc[i][:90].replace("\n", " "))

# %% [markdown]
# ## 7.4 Campaigns over time (the campaign dimension of the cube)

# %%
camp_year = (df[df["timestamp"].notna() & df["campaign"].notna()]
             .assign(year=lambda d: d["year"].astype(int), campaign=lambda d: d["campaign"].astype(int))
             .pivot_table(index="campaign", columns="year", values="id", aggfunc="count", fill_value=0))
camp_year = camp_year.reindex(campaigns["campaign"]).dropna(how="all").fillna(0).astype(int)
camp_year.index = [names_c[list(campaigns["campaign"]).index(c)] for c in camp_year.index]
display(camp_year)

fig, ax = plt.subplots(figsize=(7.2, 0.33 * len(camp_year) + 1.3))
im = ax.imshow(camp_year.to_numpy(), cmap=SEQ, aspect="auto")
ax.set_xticks(range(camp_year.shape[1]), camp_year.columns)
ax.set_yticks(range(len(camp_year)), camp_year.index)
ax.grid(False)
fig.colorbar(im, ax=ax, label="submissions")
ax.set_title("Each campaign has its own active period")
savefig("fig_campaign_year")

METRICS["clustering"] = {
    "templates_clustered": int(len(ct)), "templates_no_vocabulary": int(len(no_vocab)), "k": K,
    "k_scan": k_scan.to_dict("records"), "kmeans_silhouette": km_sil,
    "kmedoids": kmedoids_metrics, "gmm": gmm_metrics, "gmm_bic": bic.to_dict("records"),
    "em_1d": {"means_log": mu_em.tolist(), "typical_length": np.expm1(mu_em).tolist(), "weights": w_em.tolist(),
              "iterations": len(ll_hist)},
    "campaigns": campaigns.to_dict("records"),
}

# %% [markdown]
# **Analysis.**
#
# - **No natural k.** SSE falls smoothly with no sharp elbow, and the silhouette is still rising slowly at the
#   largest k tried. Spam campaigns share vocabulary (links, greetings, sales words), so the groups overlap. The
#   k with the best silhouette inside the range an operator can review was used. A silhouette around 0.25
#   means the clusters are coarse topics, not crisp groups, and they should be read that way.
# - **The campaigns are readable.** The top terms name them: the "financial robot" money adverts, SEO and
#   backlink offers, pharmacy, casino, crypto wallets, Russian-language adverts, and so on.
# - **Honeypot behaviour is a property of the campaign.** Hit rates range from almost 0% to almost 100% between
#   campaigns. The swings found by OLAP follow from this: 2022 was dominated by the financial-robot campaign,
#   whose bot fills every field, and late 2023 by the short-message group, which mostly does not.
# - **What text clustering cannot do.** The templates with no shared vocabulary are mostly one-line messages,
#   including the one-sentence price enquiry translated into dozens of languages. No two versions share a word,
#   so no text clustering can group them. Apriori (Section 5) did catch that campaign through its shape: short,
#   no link, joined name. The two unsupervised methods complement each other.
# - **K-medoids** gives each cluster a real message as its centre, which is what an operator wants to read. On
#   the same sample its silhouette is a little lower than that of K-means and the two partitions agree only
#   partly (adjusted Rand index well below 1), as expected when the cluster structure is weak.
# - **EM** in one dimension splits the messages into one-liners and full adverts. On the text representation it
#   gives soft memberships: a visible share of templates is not clearly in one group, and the examples are
#   messages that mix two themes. BIC keeps falling as components are added, which again says there is no sharp
#   number of groups. Its hard labels agree with K-means less than K-medoids does.
# - **Choice for the software.** K-means, because assigning a new submission needs only the distance to k
#   centroids, and because its partition scored best here. The medoid messages are shown beside each campaign as
#   its readable example.
