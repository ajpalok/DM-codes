# %% [markdown]
# # 2. Preprocessing
#
# ## 2.1 Handling missing values
#
# | Situation | Decision | Reason |
# | --- | --- | --- |
# | Honeypot label unknown (older export) | Keep the row, treat it as unlabelled | Deleting it would throw away half of the campaign evidence; guessing a label would invent data |
# | Empty message | Keep, with `has_message = 0` and text features set to 0 | An empty message is itself bot behaviour |
# | Empty name / e-mail / phone | Keep, with a `has_*` indicator and length 0 | Which fields a bot skips is informative |
# | Row with no content at all | Removed during preparation | Carries no information |
#
# No value is imputed with a mean or a mode: for this data "missing" is a behaviour, not a measurement error.
#
# ## 2.2 Reducing redundant features
#
# Features that carry the same information distort distance-based methods, because the shared information is
# counted more than once. The correlation matrix shows which ones overlap.

# %%
num = df[TEXT_F + CONTACT_F]
corr = num.corr()
pairs = (corr.where(np.triu(np.ones(corr.shape, dtype=bool), k=1)).stack()
         .rename("r").reset_index().rename(columns={"level_0": "feature_a", "level_1": "feature_b"}))
redundant = pairs[pairs["r"].abs() >= 0.9].sort_values("r", key=abs, ascending=False)
display(redundant)

heat_cols = ["msg_len", "word_count", "line_count", "url_count", "char_entropy", "cyrillic_ratio", "non_ascii_ratio",
        "has_email", "has_phone", "phone_digits", "phone_ru_format", "email_valid", "field_completion_ratio",
        "name_joined", "has_bbcode"]
fig, ax = plt.subplots(figsize=(6.6, 5.6))
im = ax.imshow(corr.loc[heat_cols, heat_cols], cmap=DIV, vmin=-1, vmax=1)
ax.set_xticks(range(len(heat_cols)), heat_cols, rotation=90)
ax.set_yticks(range(len(heat_cols)), heat_cols)
ax.grid(False)
fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson correlation")
ax.set_title("Several features measure the same thing")
savefig("fig_correlation")

# %% [markdown]
# Pairs such as `has_email` / `email_valid` and `cyrillic_ratio` / `non_ascii_ratio` are near copies of each
# other. They are not deleted by hand. Decision trees and Naive Bayes are run on the full set, and Section 6
# (PCA) removes the redundancy for the methods that need it: KNN, the Mahalanobis classifier and clustering.
#
# ## 2.3 Feature creation
#
# A raw message is text; the mining algorithms need numbers. Each feature below is created from the message.
# Three of them are recomputed here from the published text and compared with the published columns, to show
# exactly how they are defined.

# %%
URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'\[\]]+", re.I)
MASK_RE = re.compile(r"<(?:EMAIL|PHONE|SITE|NAME)>")


def shannon_entropy(text):
    """H = -sum p(c) log2 p(c) over the characters of the text."""
    if not text:
        return 0.0
    _, counts = np.unique(list(text), return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log2(p)).sum())


recomputed = pd.DataFrame({
    "msg_len": df["message"].str.len(),
    "url_count": df["message"].map(lambda m: len(URL_RE.findall(m))),
    "char_entropy": df["message"].map(lambda m: shannon_entropy(MASK_RE.sub(" ", m).strip())),
})
agreement = {c: float(np.isclose(recomputed[c], df[c], atol=1e-6).mean()) for c in recomputed}
print("share of rows where the recomputed feature equals the published one:", agreement)
assert min(agreement.values()) > 0.99

example = df.loc[df["url_count"] > 0, ["message", "msg_len", "url_count", "char_entropy", "has_bbcode", "kw_money"]].head(3)
display(example.assign(message=example["message"].str[:80]))

# %% [markdown]
# ## 2.4 Discretization
#
# Apriori (Section 5) and the information-gain calculation (Section 8) need categories, not continuous numbers.
# Message length and URL count are cut into ordered bins with boundaries that have a plain meaning.

# %%
df["len_bin"] = pd.cut(df["msg_len"], [-1, 0, 50, 300, 1000, np.inf],
                       labels=["empty", "short (1-50)", "medium (51-300)", "long (301-1000)", "very long (>1000)"])
df["url_bin"] = pd.cut(df["url_count"], [-1, 0, 1, np.inf], labels=["no url", "one url", "2+ urls"])

by_len = df[known].groupby("len_bin", observed=True)["honeypot_filled"].agg(rows="size", honeypot_rate="mean")
by_url = df[known].groupby("url_bin", observed=True)["honeypot_filled"].agg(rows="size", honeypot_rate="mean")
display(by_len, by_url)

fig, axes = plt.subplots(1, 2, figsize=(8.6, 2.9), gridspec_kw={"width_ratios": [5, 3]})
barh(axes[0], by_len.index, by_len["honeypot_rate"] * 100, fmt="{:.0f}%", xlabel="honeypot filled (%)")
axes[0].set_title("Honeypot hit rate by message length")
barh(axes[1], by_url.index, by_url["honeypot_rate"] * 100, fmt="{:.0f}%", xlabel="honeypot filled (%)")
axes[1].set_title("... and by number of URLs")
savefig("fig_discretization")

# %% [markdown]
# ## 2.5 Normalization and standardization
#
# Features live on very different scales: message length reaches tens of thousands while ratios stay between
# 0 and 1. Any method built on distance (KNN, K-means, PCA) would be ruled by the largest scale.
#
# - **Min-max normalization** maps a feature to [0, 1]: `x' = (x - min) / (max - min)`.
# - **Standardization** gives mean 0 and standard deviation 1: `z = (x - mean) / std`.
#
# The worked example uses five rows; the result is checked against scikit-learn.

# %%
from sklearn.preprocessing import MinMaxScaler, StandardScaler

sample = df.loc[df["has_message"] == 1, ["msg_len", "char_entropy"]].head(5).reset_index(drop=True)
by_hand = sample.copy()
for col in sample:
    x = sample[col]
    by_hand[col + "_minmax"] = (x - x.min()) / (x.max() - x.min())
    by_hand[col + "_z"] = (x - x.mean()) / x.std(ddof=0)
display(by_hand)
assert np.allclose(by_hand[["msg_len_minmax", "char_entropy_minmax"]], MinMaxScaler().fit_transform(sample))
assert np.allclose(by_hand[["msg_len_z", "char_entropy_z"]], StandardScaler().fit_transform(sample))
print("hand calculation matches MinMaxScaler and StandardScaler")

# %% [markdown]
# Min-max normalization is sensitive to the extreme values found in Section 1.2: one 32,767-character message
# would squeeze every other message into a sliver near 0. The count features are therefore first passed through
# `log(1 + x)`, and the model matrix is then **standardized**. Scalers are always fitted on the training fold
# only, inside a pipeline, so no information from the test fold leaks into training.
#
# ## 2.6 One-hot encoding
#
# `script` is nominal. Coding it as 0, 1, 2, 3 would invent an order and a distance between writing systems,
# so it becomes one binary column per value.

# %%
LOG_COLS = ["msg_len", "word_count", "avg_word_len", "line_count", "url_count", "email_mentions", "phone_mentions",
            "exclam_count", "name_len", "name_words", "email_local_len", "email_local_digits", "phone_digits"]
script_onehot = pd.get_dummies(df["script"], prefix="script").astype(int)
display(pd.concat([df["script"], script_onehot], axis=1).drop_duplicates("script"))

X_all = df[TEXT_F + CONTACT_F].astype(float).copy()
X_all[LOG_COLS] = np.log1p(X_all[LOG_COLS])
X_all = pd.concat([X_all, script_onehot], axis=1)
FEATURES = list(X_all.columns)
BINARY_F = [c for c in FEATURES if set(np.unique(X_all[c])) <= {0.0, 1.0}]
print(f"model matrix: {X_all.shape[0]:,} rows x {X_all.shape[1]} features ({len(BINARY_F)} binary)")
print("no time feature and nothing derived from the honeypot field is included")

# %% [markdown]
# # 3. Distance and similarity
#
# **What it is.** A number that says how alike two records are. **Type of learning.** None; these measures are
# the building blocks of KNN, K-means, K-medoids and the Mahalanobis classifier. **Why it is needed here.**
# Campaign discovery rests on one question, "is this message a variant of that one?", and that is a similarity
# question.
#
# ## 3.1 Euclidean and Minkowski distance on numeric features
#
# `d(x, y) = (sum |x_i - y_i|^r)^(1/r)`: r = 1 is Manhattan distance, r = 2 is Euclidean distance.

# %%
from scipy.spatial.distance import cdist


def minkowski(a, b, r):
    return float((np.abs(a - b) ** r).sum() ** (1 / r))


Z_all = StandardScaler().fit_transform(X_all)
picks = df.index[df["has_message"] == 1][:5]
P = Z_all[picks]
labels5 = [f"id {i}" for i in df.loc[picks, "id"]]
for r, name in [(1, "Manhattan (r = 1)"), (2, "Euclidean (r = 2)"), (3, "Minkowski (r = 3)")]:
    D = np.array([[minkowski(a, b, r) for b in P] for a in P])
    assert np.allclose(D, cdist(P, P, "minkowski", p=r))
    print(name)
    display(pd.DataFrame(D, index=labels5, columns=labels5).round(2))

# %% [markdown]
# ## 3.2 Simple matching and Jaccard coefficients on binary features
#
# For binary vectors, count the four kinds of match: f11 (both 1), f00 (both 0), f10 and f01.
#
# - `SMC = (f11 + f00) / (f11 + f00 + f10 + f01)` counts shared absences as agreement.
# - `Jaccard = f11 / (f11 + f10 + f01)` ignores shared absences.
#
# The trait flags here are asymmetric (most are 0 for most rows), so two messages that both lack BBCode, crypto
# words and pharmacy words are not thereby similar. Jaccard is the right measure; SMC is shown for contrast.

# %%
def smc_jaccard(a, b):
    f11 = int(((a == 1) & (b == 1)).sum())
    f00 = int(((a == 0) & (b == 0)).sum())
    f10 = int(((a == 1) & (b == 0)).sum())
    f01 = int(((a == 0) & (b == 1)).sum())
    return (f11 + f00) / (f11 + f00 + f10 + f01), (f11 / (f11 + f10 + f01) if f11 + f10 + f01 else 0.0), (f11, f00, f10, f01)


B = X_all.loc[picks, BINARY_F].to_numpy()
rows = []
for i, j in itertools.combinations(range(len(picks)), 2):
    smc, jac, (f11, f00, f10, f01) = smc_jaccard(B[i], B[j])
    rows.append({"pair": f"{labels5[i]} / {labels5[j]}", "f11": f11, "f00": f00, "f10": f10, "f01": f01,
                 "SMC": smc, "Jaccard": jac})
display(pd.DataFrame(rows))

# %% [markdown]
# SMC is high for every pair because most flags are 0 in both vectors. Jaccard separates the pairs.
#
# ## 3.3 Cosine similarity on text
#
# Each message becomes a TF-IDF vector (one dimension per word, weighted up for words that are rare across
# messages). `cos(x, y) = x . y / (|x| |y|)` measures the angle between two vectors and ignores their length,
# so a short and a long version of the same advert still match.

# %%
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

tpl = (df[df["has_message"] == 1].drop_duplicates("template_id")
       [["id", "template_id", "message", "script", "template_count"]].reset_index(drop=True))
tfidf = TfidfVectorizer(lowercase=True, min_df=2, max_features=20000, sublinear_tf=True)
T = tfidf.fit_transform(tpl["message"])
print(f"{len(tpl):,} distinct templates x {T.shape[1]:,} terms")

a, b = T[0].toarray().ravel(), T[1].toarray().ravel()
by_hand_cos = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
assert np.isclose(by_hand_cos, cosine_similarity(T[0], T[1])[0, 0])
print(f"cosine similarity of the first two templates, by hand and by scikit-learn: {by_hand_cos:.4f}")

# Nearest other template for every template (TF-IDF rows are already unit length, so T @ T.T is the cosine matrix).
S = (T @ T.T).toarray()
np.fill_diagonal(S, 0)
nearest = S.max(axis=1)
near_dup = {f">= {t}": float((nearest >= t).mean()) for t in (0.5, 0.7, 0.9)}
print("share of templates whose nearest other template is at least this similar:", {k: round(v, 3) for k, v in near_dup.items()})
METRICS["similarity"] = {"templates": int(len(tpl)), "near_duplicate_share": near_dup}

fig, ax = plt.subplots(figsize=(6.2, 2.9))
ax.hist(nearest, bins=40, color=C[0], rwidth=0.88)
ax.set_xlabel("cosine similarity to the nearest other template")
ax.set_ylabel("templates")
ax.set_title("Many templates have a near-identical twin")
savefig("fig_nearest_similarity")

i = int(np.argmax((nearest > 0.85) & (nearest < 0.97)))
j = int(S[i].argmax())
print(f"example near-duplicate pair, cosine = {S[i, j]:.2f}")
print(" A:", tpl.loc[i, "message"][:160].replace("\n", " "))
print(" B:", tpl.loc[j, "message"][:160].replace("\n", " "))

# %% [markdown]
# **Analysis.** Exact-template matching (Section 1.2) already found repeated messages. Cosine similarity shows
# that many of the remaining "distinct" templates are small rewrites of one another: the histogram has a heavy
# right side, and the example pair differs in only a few words. This is the evidence that campaigns exist beyond
# exact copies, and it is why Section 7 clusters the templates.
