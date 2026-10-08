# %% [markdown]
# # 10. Comparative evaluation: which algorithm suits which task
#
# One table per classifier across both tasks, with the measures that matter for each: accuracy under drift for
# Task A, and behaviour outside the training corpus for Task B.

# %%
ALIGN = {"Naive Bayes": "Naive Bayes (multinomial)", "Logistic regression": "Logistic regression",
         "Decision tree": "Decision tree", "KNN": "KNN (cosine)", "Mahalanobis (PCA)": "Mahalanobis (LSA)",
         "Perceptron": "Perceptron", "MLP (one hidden layer)": "MLP (one hidden layer)"}
summary = pd.DataFrame({
    "A: balanced acc, cross-validation": cv_a.loc[list(ALIGN), "balanced_acc"].astype(float).values,
    "A: balanced acc, future period": ts_a.loc[list(ALIGN), "balanced_acc"].astype(float).values,
    "A: AUC, future period": ts_a.loc[list(ALIGN), "auc"].astype(float).values,
    "B: balanced acc, cross-validation": cv_b.loc[list(ALIGN.values()), "balanced_acc"].astype(float).values,
    "B: same-source AUC": cross_tbl.loc[list(ALIGN.values()), "same-source AUC"].astype(float).values,
    "B: genuine messages flagged (of 40)": cross_tbl.loc[list(ALIGN.values()), FP_COL].astype(int).values,
    "B: model size (KB)": cv_b.loc[list(ALIGN.values()), "size_kb"].astype(float).round(0).values,
}, index=[n.replace(" (PCA)", "").replace(" (one hidden layer)", "") for n in ALIGN])
display(summary)
METRICS["summary"] = summary.reset_index().rename(columns={"index": "model"}).to_dict("records")

# %% [markdown]
# **Which algorithm for which job**
#
# | Algorithm | Strength shown here | Weakness shown here | Verdict |
# | --- | --- | --- | --- |
# | Logistic regression | Best in Task A, in cross-validation and on future data; few false positives on genuine messages in Task B; probabilities; small, readable weights | Linear: cannot capture interactions between features | **Deployed** in the software |
# | Naive Bayes | One pass to train; almost no false positives on genuine messages | Independence assumption is violated; needs the right variant and smoothing value; at chance on future data in Task A | Good fallback when no tuning is possible |
# | Decision tree | Readable rules that match the Apriori findings | Lowest and least stable in Task A; poor ranking outside its corpus in Task B | Use for explanation, not for scoring |
# | KNN | Competitive in cross-validation with no training step | Stores all data, slowest prediction, needs scaling, near chance on future data | Not suitable for a small server |
# | Mahalanobis | Beats Euclidean nearest-mean by using covariance; no false positives on genuine messages in Task B | Needs PCA to be computable; at chance on future data in Task A | A teaching comparison; not deployed |
# | Perceptron | Simplest neural unit, fast | No probabilities, weakest ranking in Task A, many false positives on genuine messages | Superseded by logistic regression |
# | MLP | Near the top of the Task B cross-validation table | No better than the linear models in Task A, at chance on future data, flags the most genuine messages | Not justified at this data size |
#
# Across both tasks the same pattern appears: scoring well on data drawn like the training data says little
# about holding up when the data differs. The perceptron and the MLP lead the Task B cross-validation table and
# flag the most genuine messages; most models that look fine in Task A cross-validation are at chance a year
# later. Logistic regression is at or near the top in-distribution and clearly the most reliable outside it.
# With a few thousand rows and a moving target, a simple probabilistic model is the right one.
#
# # 11. Regression: is there a trend?
#
# **What it is.** Linear regression fits `y = w0 + w1 x` by least squares; polynomial regression adds powers of
# x. **Type of learning.** Supervised, with a numeric target.
#
# **Why it is needed here.** Two operator questions are about trend: is spam volume growing, and is the honeypot
# hit rate falling steadily? Both are checked with a fitted line and its R-squared.
#
# **Implementation.** The slope and intercept come from the lecture formulas
# `w1 = sum((x - mean_x)(y - mean_y)) / sum((x - mean_x)^2)`, `w0 = mean_y - w1 mean_x`, and the degree-2 fit
# from the normal equation `W = (X^T X)^-1 X^T Y`. Both are checked against NumPy's least-squares fit.
# Months missing from the export are left out, not counted as zero.

# %%
monthly = (fact.assign(month_start=fact["timestamp"].dt.to_period("M").dt.to_timestamp())
           .groupby("month_start").agg(submissions=("id", "size"), hit_rate=("honeypot_filled", "mean")).reset_index())
start = monthly["month_start"].min()
monthly["t"] = (monthly["month_start"].dt.year - start.year) * 12 + (monthly["month_start"].dt.month - start.month)


# %include algorithms/regression.py


trend = {}
grid_t = np.linspace(monthly["t"].min(), monthly["t"].max(), 200)
fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.3))
for ax, col, ylabel, scale in [(axes[0], "submissions", "submissions per month", 1), (axes[1], "hit_rate", "honeypot filled (%)", 100)]:
    part = monthly.dropna(subset=[col])                      # months without a honeypot have no hit rate
    t, y = part["t"].to_numpy(dtype=float), part[col].to_numpy(dtype=float) * scale
    w0, w1 = fit_line(t, y)
    w_poly = fit_polynomial(t, y, 2)
    assert np.allclose([w1, w0], np.polyfit(t, y, 1)) and np.allclose(w_poly[::-1], np.polyfit(t, y, 2))
    r2_lin, r2_poly = r_squared(y, w0 + w1 * t), r_squared(y, np.vander(t, 3, increasing=True) @ w_poly)
    trend[col] = {"months": int(len(part)), "w0": w0, "w1_per_month": w1, "r2_linear": r2_lin,
                  "poly_coefficients": w_poly.tolist(), "r2_degree2": r2_poly}
    ax.scatter(t, y, s=22, color=GRAY, linewidths=0, label="one month")
    ax.plot(grid_t, w0 + w1 * grid_t, color=C[0], label=f"linear, R2 = {r2_lin:.2f}")
    ax.plot(grid_t, np.vander(grid_t, 3, increasing=True) @ w_poly, color=C[1], label=f"degree 2, R2 = {r2_poly:.2f}")
    ax.set_xlabel(f"months since {start:%B %Y}")
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper left", fontsize=8)
axes[0].set_title("Monthly volume: no usable trend")
axes[1].set_title("Honeypot hit rate: no usable trend either")
savefig("fig_trend")
print(f"months with data: {len(monthly)} of {int(monthly['t'].max()) + 1}")
print(pd.DataFrame(trend).T[["months", "w1_per_month", "r2_linear", "r2_degree2"]])
METRICS["trend"] = {"months_with_data": int(len(monthly)), **trend}

# %% [markdown]
# **Analysis.** The hand formulas reproduce NumPy's fit exactly.
#
# - *Volume.* A straight line explains under a tenth of the variance of monthly volume and a parabola not much
#   more. Volume is driven by bursts, a campaign switching on and off, not by a smooth trend.
# - *Hit rate.* The fitted line slopes down by about half a percentage point per month and explains about a
#   tenth of the variance. The monthly hit rate jumps between near 100% and near 10% depending on which campaign
#   is active (Section 7.4); it does not decline steadily.
#
# Regression answers "is there a smooth trend?" with "no", for both quantities. Forecasting this form's spam
# from a trend line would be wrong; the campaign view is the informative one.
#
# Logistic regression, the classification member of the regression family, was applied in Sections 8 and 9,
# including the hand calculation of the sigmoid for one row.
#
# # 12. Export for the software and the paper
#
# The chosen Task B model is re-fitted on all messages and saved, together with the campaign model
# (vectorizer, LSA and K-means centroids), the campaign profiles, the association rules and every metric.

# %%
import joblib
import sklearn


def jsonable(obj):
    """Plain Python types only; NaN becomes null so that any JSON parser accepts the file."""
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return None if math.isnan(obj) or math.isinf(obj) else float(obj)
    if isinstance(obj, np.ndarray):
        return jsonable(obj.tolist())
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    return obj


def dump(name, payload):
    with open(os.path.join(ART, name), "w", encoding="utf-8") as fh:
        json.dump(jsonable(payload), fh, ensure_ascii=False, indent=1)


spam_model = clone(MODELS_B[CHOSEN]).fit(textB, yB)
joblib.dump(spam_model, os.path.join(ART, "spam_model.joblib"))
joblib.dump({"vectorizer": tfidf_c, "lsa": lsa, "kmeans": kmeans}, os.path.join(ART, "campaign_model.joblib"))

medoid_examples = {int(km_on_sample[m]): ct["message"].iloc[med_idx[m]][:200] for m in medoids}
dump("clusters.json", {"k": K, "campaigns": campaigns.to_dict("records"), "medoid_examples": medoid_examples})
dump("rules.json", {
    "min_support": MIN_SUP, "min_confidence": MIN_CONF,
    "honeypot_filled": top_filled.to_dict("records"), "honeypot_empty": top_empty.to_dict("records"),
    "decision_tree_depth3": export_text(tree3, feature_names=FEATURES, decimals=2),
})
dump("model_card.json", {
    "model": CHOSEN, "trained_on_rows": int(len(yB)), "default_threshold": 0.5,
    "cv": cv_b.loc[CHOSEN, COLS].astype(float).to_dict(),
    "same_source_auc": float(cross_tbl.loc[CHOSEN, "same-source AUC"]),
    "genuine_messages_flagged_of_40": int(cross_tbl.loc[CHOSEN, FP_COL]),
    "thresholds": thr_rows, "sklearn_version": sklearn.__version__,
    "limits": "Legitimate class is public SMS, not real contact-form traffic. Re-train on the operator's own data.",
})
dump("metrics.json", METRICS)

for probe in ["Make $5000 a day with our financial robot http://example.com/robot",
              "Hello, I would like to ask about your office hours next week. Thank you."]:
    print(f"P(spam) = {spam_model.predict_proba(np.array([probe], dtype=object))[0, 1]:.3f}  <-  {probe}")
print("\nartifacts written to", os.path.abspath(ART))
for name in sorted(os.listdir(ART)):
    path = os.path.join(ART, name)
    print(f"   {name:<24} {'(folder)' if os.path.isdir(path) else f'{os.path.getsize(path) / 1024:,.0f} KB'}")

# %% [markdown]
# # Summary of findings
#
# 1. **The honeypot is not dependable.** Its hit rate was about 98% in 2022, about 10% in October and November
#    2023, and above 90% again in spring 2025 (OLAP, Section 4).
# 2. **Checking the label mattered.** A run of 647 consecutive submissions over twelve months never fills the
#    honeypot. The form had no honeypot field in that period; those rows were treated as unlabelled
#    (Section 1.3). Trusting them would have changed the class balance and the model scores (Section 8.10).
# 3. **Honeypot behaviour belongs to the campaign.** One campaign fills every field and is always caught;
#    another sends a one-line multilingual enquiry and is almost never caught (Apriori, Section 5; clustering,
#    Section 7).
# 4. **Honeypot evasion is moderately predictable inside a period and poorly predictable forward.** Balanced
#    accuracy of about 0.79 in cross-validation; on the following period only logistic regression stays clearly
#    above chance, at about 0.69 (Section 8).
# 5. **Spam-versus-legitimate scores look excellent and are partly an artefact.** About 0.97 balanced accuracy
#    in-distribution, of which message length alone explains a large part. Out-of-corpus checks, not the
#    headline score, decided which model to deploy (Section 9).
# 6. **Simple, probabilistic and re-trainable beats flexible** at this data size and under this much change
#    (Section 10).
