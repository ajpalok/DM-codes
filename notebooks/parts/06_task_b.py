# %% [markdown]
# **Analysis of Task A.**
#
# - **The features carry signal, and nothing leaked.** In cross-validation the learned models reach a balanced
#   accuracy of 0.73 to 0.79 against 0.50 for the majority baseline, and an AUC of up to 0.88. No score is near
#   1.00, which is what a real, noisy label looks like.
# - **A one-line rule is hard to beat at a single threshold.** "The message has a URL" reaches a balanced
#   accuracy of about 0.76; the best learned model about 0.79. The learned models are better at *ranking*
#   submissions (AUC 0.80 to 0.88 against 0.76), which matters when a threshold has to be chosen.
# - **Forward in time, most models fall to chance.** Trained on 2020-2023 and tested on 2024-2025, logistic
#   regression keeps a balanced accuracy of about 0.69 (AUC about 0.77). Every other learned model lands between
#   0.49 and 0.57, below the URL rule. The test period is small (372 rows, 71 of them "empty"), so differences of
#   a few points mean nothing, but the gap between logistic regression and the rest, and between
#   cross-validation and the time split, is far larger than that.
# - **Why the future is different.** In 2025 almost every submission fills the honeypot, including the one-line
#   price enquiry that almost never did in 2023 (the false negatives listed above). The form itself changed at
#   that point (Section 1.3). Honeypot behaviour depends on how the form presents the hidden field and on the
#   bot software, not only on what the message says, and content features cannot see either.
# - **Naive Bayes.** The Bernoulli variant on the binary flags beats the Gaussian variant on all features by a
#   wide margin: the count features are far from Gaussian even after the log transform.
# - **KNN.** Scaling the features raises its balanced accuracy by about three points. Its model is the entire
#   training set (hundreds of KB against 2-3 KB for the linear models) and it is the slowest to predict.
# - **Mahalanobis.** It beats the Euclidean nearest-mean classifier on the same PCA components by about two
#   points, the benefit of correcting for covariance. It models the shape of each class closely, so when the
#   classes move it is at chance.
# - **Perceptron.** Its balanced accuracy in cross-validation is close to that of logistic regression, but its
#   AUC is the lowest of the learned models: it outputs a decision, not a graded score. The classes are not
#   linearly separable, so its update rule never settles.
# - **Decision tree.** The lowest and least stable in cross-validation. Its value is the readable rule set: the
#   first question of the depth-3 tree, whether the name is a joined token, is the attribute the from-scratch
#   gain ratio chose and the one Apriori put in its rules.
#
# **Conclusion for the project.** Whether a sender fills the honeypot is moderately predictable inside one
# period and poorly predictable forward in time. It is a property of the bot and the form, and both change. The
# honeypot cannot be the only defence, and no model of honeypot behaviour can stand in for it; the content
# itself has to be classified, which is Task B.
#
# # 9. Task B: spam versus legitimate messages (supervised classification)
#
# **Type of learning.** Supervised. Label 1 = a message received by this form (all spam), label 0 = a
# legitimate message from the public SMS Spam Collection.
#
# **Why it is needed here.** This is the model the software uses to score an incoming submission when the
# honeypot is silent.
#
# **Known weakness, stated up front.** The two classes come from different sources. A model can score well by
# learning "which source" (message length, SMS slang, Cyrillic script) instead of "spam". Section 9.4 measures
# how much of the score that explains.
#
# **Features.** Words only. Each message becomes a vector of word counts (for Naive Bayes) or TF-IDF weights
# (for the other models), built inside the cross-validation pipeline so the vocabulary never sees test folds.
# Spam rows are distinct templates, so no copy of a training message appears in a test fold.

# %%
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import FunctionTransformer

merged["text"] = merged["text"].fillna("").astype(str)
textB = merged["text"].to_numpy(dtype=object)
yB = merged["label"].to_numpy()
print(f"Task B: {len(yB):,} messages, {yB.mean():.1%} spam")
display(merged.groupby(["source", "label"])["text"].agg(rows="size", median_length=lambda s: s.str.len().median()))

# %% [markdown]
# ## 9.1 Multinomial Naive Bayes from scratch
#
# For text, the likelihood of a class is the product of the probabilities of the words in the message:
#
# `P(word | class) = (count of the word in that class + alpha) / (all words in that class + alpha x vocabulary size)`
#
# With `alpha = 0` a word that never occurred in one class gets probability 0 and wipes out the whole product
# (the zero-frequency problem). **Laplace smoothing** (`alpha = 1`) adds one imaginary occurrence of every word
# to every class.

# %%
def mnb_fit(counts, y, alpha=1.0):
    log_prior = np.log(np.array([np.mean(y == c) for c in (0, 1)]))
    word_counts = np.vstack([np.asarray(counts[y == c].sum(axis=0)).ravel() for c in (0, 1)])
    log_likelihood = np.log((word_counts + alpha) / (word_counts.sum(axis=1, keepdims=True) + alpha * counts.shape[1]))
    return log_prior, log_likelihood, word_counts


def mnb_predict(counts, log_prior, log_likelihood):
    return np.asarray(counts @ log_likelihood.T + log_prior).argmax(axis=1)   # sums of logs instead of products


tr_b, te_b = train_test_split(np.arange(len(yB)), test_size=0.2, stratify=yB, random_state=SEED)
cvec = CountVectorizer(lowercase=True, min_df=2, max_features=20000)
Ctr, Cte = cvec.fit_transform(textB[tr_b]), cvec.transform(textB[te_b])
vocab = np.array(cvec.get_feature_names_out())
log_prior, log_lik, word_counts = mnb_fit(Ctr, yB[tr_b])
mine_nb = mnb_predict(Cte, log_prior, log_lik)
sk_nb = MultinomialNB(alpha=1.0).fit(Ctr, yB[tr_b]).predict(Cte)
print(f"from-scratch Multinomial NB agrees with scikit-learn on {np.mean(mine_nb == sk_nb):.2%} of {len(te_b):,} test messages")
assert np.mean(mine_nb == sk_nb) > 0.999

totals = word_counts.sum(axis=1)
worked = []
for w in ["free", "website", "money", "love", "ok"]:
    j = int(np.where(vocab == w)[0][0])
    worked.append({"word": w, "count in legitimate": int(word_counts[0, j]), "count in spam": int(word_counts[1, j]),
                   "P(word | legitimate)": math.exp(log_lik[0, j]), "P(word | spam)": math.exp(log_lik[1, j]),
                   "spam / legitimate ratio": math.exp(log_lik[1, j] - log_lik[0, j])})
print(f"words in legitimate class: {int(totals[0]):,} | words in spam class: {int(totals[1]):,} | vocabulary: {len(vocab):,}")
worked = pd.DataFrame(worked)
for col in ["P(word | legitimate)", "P(word | spam)"]:
    worked[col] = worked[col].map("{:.6f}".format)
display(worked)
zero_in_ham, zero_in_spam = int((word_counts[0] == 0).sum()), int((word_counts[1] == 0).sum())
print(f"zero-frequency problem: {zero_in_ham:,} vocabulary words never occur in the legitimate class and "
      f"{zero_in_spam:,} never occur in spam; without smoothing each would force a probability of exactly 0")

# %%
ALPHAS = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
alpha_folds = {alpha: [] for alpha in ALPHAS}
for train, test in StratifiedKFold(5, shuffle=True, random_state=SEED).split(textB, yB):
    vec = CountVectorizer(lowercase=True, min_df=2, max_features=20000)
    Xtr, Xte = vec.fit_transform(textB[train]), vec.transform(textB[test])      # counts built once per fold
    for alpha in ALPHAS:
        nb = MultinomialNB(alpha=alpha).fit(Xtr, yB[train])
        out = metrics_from_counts(*confusion_counts(yB[test], nb.predict(Xte)))
        out["auc"] = roc_auc_score(yB[test], nb.predict_proba(Xte)[:, 1])
        alpha_folds[alpha].append(out)
alpha_scan = pd.DataFrame([{"alpha": alpha, **pd.DataFrame(v)[["balanced_acc", "recall", "specificity", "auc"]].mean().to_dict()}
                           for alpha, v in alpha_folds.items()])
display(alpha_scan.set_index("alpha").T)

llr = pd.Series(log_lik[1] - log_lik[0], index=vocab)
frequent = word_counts.sum(axis=0) >= 30
print("words that most indicate spam:      ", ", ".join(llr[frequent].sort_values(ascending=False).head(18).index))
print("words that most indicate legitimate:", ", ".join(llr[frequent].sort_values().head(18).index))

# %% [markdown]
# ## 9.2 All models under one protocol

# %%
def text_length(texts):
    return np.log1p(np.array([[len(t)] for t in texts], dtype=float))


def tfidf_words():
    return TfidfVectorizer(lowercase=True, min_df=2, max_features=20000, sublinear_tf=True)


MODELS_B = {
    "Baseline: majority class": DummyClassifier(strategy="most_frequent"),
    "Baseline: message length only": make_pipeline(FunctionTransformer(text_length), LogisticRegression()),
    "Naive Bayes (multinomial)": make_pipeline(CountVectorizer(lowercase=True, min_df=2, max_features=20000), MultinomialNB(alpha=1.0)),
    "Logistic regression": make_pipeline(tfidf_words(), LogisticRegression(max_iter=2000)),
    "Decision tree": make_pipeline(tfidf_words(), DecisionTreeClassifier(criterion="entropy", max_depth=20, random_state=SEED)),
    "KNN (cosine)": make_pipeline(tfidf_words(), KNeighborsClassifier(n_neighbors=5, metric="cosine", algorithm="brute")),
    "Mahalanobis (LSA)": make_pipeline(tfidf_words(), TruncatedSVD(20, random_state=SEED), MahalanobisClassifier()),
    "Perceptron": make_pipeline(tfidf_words(), Perceptron(random_state=SEED)),
    "MLP (one hidden layer)": make_pipeline(TfidfVectorizer(lowercase=True, min_df=2, max_features=5000, sublinear_tf=True),
                                            MLPClassifier(hidden_layer_sizes=(32,), max_iter=40, early_stopping=True, random_state=SEED)),
}
cv_b, oof_b, oof_pred_b = {}, {}, {}
for name, model in MODELS_B.items():
    cv_b[name], oof_pred_b[name], oof_b[name] = evaluate_cv(model, textB, yB)
cv_b = pd.DataFrame(cv_b).T
print("5-fold cross-validation (mean over folds)")
display(cv_b[COLS + ["balanced_acc_std"]])
display(cv_b[["fit_s", "predict_ms", "size_kb"]].rename(columns={"fit_s": "training time (s)", "predict_ms": "prediction (ms per message)", "size_kb": "model size (KB)"}))

# %% [markdown]
# ## 9.3 A first warning: how far does message length alone go?
#
# The "message length only" baseline in the table above uses one number per message and no words at all. Its
# score is the share of the task that the *source difference* solves for free, because form spam is long and
# SMS messages are short. The checks below measure the remainder.
#
# ## 9.4 Did the models learn "spam", or only "which source"?
#
# Four checks, each attacking the source shortcut from a different side:
#
# 1. **Latin script only.** Remove every non-Latin message, so "Cyrillic means spam" is unavailable.
# 2. **Length-matched.** Keep only messages of 20 to 200 characters in both classes, so length is unavailable.
# 3. **Same-source test.** Hold out 20% of the legitimate SMS from training, then test on those plus the *SMS
#    spam* from the same public collection (never used in training). Both test classes are SMS, so a model that
#    learned only "form versus SMS" would call all of them legitimate.
# 4. **Out-of-domain legitimate messages.** Forty hand-written messages of the kind a real visitor sends through
#    a contact form (synthetic, written for this project). Every one flagged as spam is a false positive.

# %%
LEARNED_B = [m for m in MODELS_B if not m.startswith("Baseline")]
CONTROL = {
    "Baseline: message length only": ("length", LogisticRegression()),
    "Naive Bayes (multinomial)": ("counts", MultinomialNB(alpha=1.0)),
    "Logistic regression": ("tfidf", LogisticRegression(max_iter=2000)),
    "Perceptron": ("tfidf", Perceptron(random_state=SEED)),
}


def cv_on_words(texts, y, classifiers):
    """5-fold CV that builds the word matrices once per fold and shares them between the classifiers."""
    folds = {name: [] for name in classifiers}
    for train, test in StratifiedKFold(5, shuffle=True, random_state=SEED).split(texts, y):
        mats = {"length": (text_length(texts[train]), text_length(texts[test]))}
        for kind, vec in [("counts", CountVectorizer(lowercase=True, min_df=2, max_features=20000)), ("tfidf", tfidf_words())]:
            mats[kind] = (vec.fit_transform(texts[train]), vec.transform(texts[test]))
        for name, (kind, clf) in classifiers.items():
            Xtr, Xte = mats[kind]
            m = clone(clf).fit(Xtr, y[train])
            out = metrics_from_counts(*confusion_counts(y[test], m.predict(Xte)))
            out["auc"] = roc_auc_score(y[test], scores_of(m, Xte))
            folds[name].append(out)
    return {name: pd.DataFrame(v).mean().to_dict() for name, v in folds.items()}


lengths = merged["text"].str.len().to_numpy()
subsets = {
    "all messages": np.ones(len(yB), dtype=bool),
    "latin script only": (merged["script"] == "latin").to_numpy(),
    "length 20-200 only": (lengths >= 20) & (lengths <= 200),
}
subset_rows = []
for sname, mask in subsets.items():
    for mname, s_ in cv_on_words(textB[mask], yB[mask], CONTROL).items():
        subset_rows.append({"subset": sname, "rows": int(mask.sum()), "spam share": float(yB[mask].mean()), "model": mname,
                            "balanced_acc": s_["balanced_acc"], "auc": s_["auc"]})
subset_tbl = pd.DataFrame(subset_rows)
display(subset_tbl.drop_duplicates("subset").set_index("subset")[["rows", "spam share"]])
display(subset_tbl.pivot(index="model", columns="subset", values="balanced_acc")[list(subsets)])

# %%
is_ham = np.where(yB == 0)[0]
ham_train, ham_test = train_test_split(is_ham, test_size=0.2, random_state=SEED)
train_cs = np.concatenate([np.where(yB == 1)[0], ham_train])
sms_spam["text"] = sms_spam["text"].fillna("").astype(str)
holdout["text"] = holdout["text"].astype(str)
cs_text = np.concatenate([textB[ham_test], sms_spam["text"].to_numpy(dtype=object)])
cs_y = np.concatenate([np.zeros(len(ham_test), dtype=int), np.ones(len(sms_spam), dtype=int)])

cross_rows, fitted_cs = [], {}
for mname in LEARNED_B:
    m = clone(MODELS_B[mname]).fit(textB[train_cs], yB[train_cs])
    fitted_cs[mname] = m
    pred = m.predict(cs_text)
    out = metrics_from_counts(*confusion_counts(cs_y, pred))
    cross_rows.append({"model": mname,
                       "SMS spam caught (recall)": out["recall"],
                       "held-out SMS legitimate passed (specificity)": out["specificity"],
                       "same-source AUC": roc_auc_score(cs_y, scores_of(m, cs_text)),
                       "contact-form legitimate flagged (false positives of 40)": int(m.predict(holdout["text"].to_numpy(dtype=object)).sum())})
cross_tbl = pd.DataFrame(cross_rows).set_index("model")
display(cross_tbl)

# %% [markdown]
# ## 9.5 Choosing the model for the software
#
# The software needs (a) a probability, so that the operator can set a blocking threshold, (b) a model under
# 5 MB and (c) a prediction in under 10 ms per message. These limits were fixed before looking at results,
# together with the rule "take the candidate with the best cross-validated F1". Models defined inside this
# notebook (the from-scratch Mahalanobis classifier) are not candidates, because the service loads plain
# scikit-learn objects.
#
# That rule turned out not to discriminate: the F1 values of the candidates lie within about one point of each
# other, which is no more than the variation between folds. The checks of Section 9.4 do separate them. The
# choice is therefore made in two steps: keep every candidate within 0.01 F1 of the best, then take the one
# that flags the fewest genuine contact-form messages, with the same-source AUC as tie-break. For a contact
# form, blocking a real enquiry is the costly error.
#
# One consequence has to be stated: the 40-message set is now used for selection, so its false-positive count
# for the chosen model is no longer an untouched estimate.

# %%
FP_COL = "contact-form legitimate flagged (false positives of 40)"
candidates_b = [m for m in LEARNED_B if m != "Mahalanobis (LSA)" and hasattr(MODELS_B[m], "predict_proba")
                and cv_b.loc[m, "size_kb"] < 5 * 1024 and cv_b.loc[m, "predict_ms"] < 10]
f1_b = cv_b.loc[candidates_b, "f1"].astype(float)
tied = [m for m in candidates_b if f1_b.max() - f1_b[m] <= 0.01]
selection = cross_tbl.loc[tied, [FP_COL, "same-source AUC"]].assign(cv_f1=f1_b[tied], cv_f1_std=cv_b.loc[tied, "f1_std"].astype(float))
selection = selection.sort_values([FP_COL, "same-source AUC"], ascending=[True, False])
CHOSEN = selection.index[0]
print("candidates with a probability output, within the size and speed limits:", candidates_b)
print(f"best F1 {f1_b.max():.4f} ({f1_b.idxmax()}); within 0.01 of it:")
display(selection)
print(f"chosen for the software: {CHOSEN}  ({cv_b.loc[CHOSEN, 'size_kb']:.0f} KB, {cv_b.loc[CHOSEN, 'predict_ms']:.3f} ms per message)")

holdout_text = holdout["text"].to_numpy(dtype=object)
thr_rows = []
for thr in [0.3, 0.5, 0.7, 0.9]:
    out = metrics_from_counts(*confusion_counts(yB, (oof_b[CHOSEN] >= thr).astype(int)))
    cs_pred = (fitted_cs[CHOSEN].predict_proba(cs_text)[:, 1] >= thr).astype(int)
    thr_rows.append({"threshold": thr, "precision": out["precision"], "recall": out["recall"], "specificity": out["specificity"],
                     "SMS spam caught": metrics_from_counts(*confusion_counts(cs_y, cs_pred))["recall"],
                     "contact-form legitimate flagged (of 40)": int((fitted_cs[CHOSEN].predict_proba(holdout_text)[:, 1] >= thr).sum())})
thr_tbl = pd.DataFrame(thr_rows)
print(f"{CHOSEN}: effect of the decision threshold (cross-validated scores for the first three columns)")
display(thr_tbl)

fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5))
order_b = cv_b.loc[LEARNED_B + ["Baseline: message length only"], "balanced_acc"].astype(float).sort_values(ascending=False)
barh(axes[0], order_b.index, order_b.values, fmt="{:.3f}", xlabel="balanced accuracy, 5-fold")
axes[0].set_title("In-distribution scores are close together")
fp40 = cross_tbl[FP_COL].reindex([m for m in order_b.index if m in cross_tbl.index])
barh(axes[1], fp40.index, fp40.values, color=C[1], fmt="{:.0f}", xlabel="flagged as spam, of 40 genuine contact-form messages")
axes[1].set_title("False positives on real enquiries differ")
savefig("fig_task_b_models")

fig, ax = plt.subplots(figsize=(6.6, 3.2))
sub_plot = subset_tbl.pivot(index="model", columns="subset", values="balanced_acc")[list(subsets)]
width = 0.26
for i, (sname, colour) in enumerate(zip(subsets, C)):
    ax.bar(np.arange(len(sub_plot)) + (i - 1) * width, sub_plot[sname], width=width * 0.9, color=colour, label=sname)
ax.set_xticks(np.arange(len(sub_plot)), [m.replace("Baseline: ", "").replace(" (multinomial)", "") for m in sub_plot.index], fontsize=8.5)
ax.set_ylim(0.45, 1.0)
ax.set_ylabel("balanced accuracy, 5-fold")
ax.grid(axis="x", visible=False)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
ax.set_title("Once lengths are matched, length alone fails and words still work", pad=30)
savefig("fig_task_b_controls")

METRICS["task_b"] = {
    "rows": int(len(yB)), "spam_share": float(yB.mean()),
    "cv": cv_b.reset_index().rename(columns={"index": "model"}).to_dict("records"),
    "alpha_scan": alpha_scan.to_dict("records"),
    "zero_frequency": {"never_in_legitimate": zero_in_ham, "never_in_spam": zero_in_spam, "vocabulary": int(len(vocab)),
                       "words_legitimate": int(totals[0]), "words_spam": int(totals[1])},
    "subset_checks": subset_tbl.to_dict("records"),
    "cross_source": cross_tbl.reset_index().to_dict("records"),
    "candidates": candidates_b, "tied_within_0.01_f1": tied, "chosen_model": CHOSEN,
    "thresholds": thr_rows,
    "spam_words": llr[frequent].sort_values(ascending=False).head(18).index.tolist(),
    "legitimate_words": llr[frequent].sort_values().head(18).index.tolist(),
}

# %% [markdown]
# ## 9.6 Where the chosen model fails

# %%
chosen_fit = fitted_cs[CHOSEN]                       # the fit that never saw the held-out legitimate SMS
genuine = holdout.assign(spam_probability=chosen_fit.predict_proba(holdout_text)[:, 1])
print("genuine contact-form messages with the highest spam probability:")
display(genuine.sort_values("spam_probability", ascending=False).head(5)[["spam_probability", "text"]])

vectorizer_b, classifier_b = chosen_fit[0], chosen_fit[-1]
if hasattr(classifier_b, "coef_"):
    top_text = genuine.sort_values("spam_probability", ascending=False)["text"].iloc[0]
    contrib = pd.Series(vectorizer_b.transform([top_text]).multiply(classifier_b.coef_[0]).toarray().ravel(),
                        index=vectorizer_b.get_feature_names_out())
    print("words pushing the top message toward spam:      ", ", ".join(f"{w} ({v:+.2f})" for w, v in contrib.sort_values(ascending=False).head(6).items()))
    print("words pushing the top message toward legitimate:", ", ".join(f"{w} ({v:+.2f})" for w, v in contrib.sort_values().head(4).items()))

missed = (yB == 1) & (oof_pred_b[CHOSEN] == 0)
caught = (yB == 1) & (oof_pred_b[CHOSEN] == 1)
wrongly_flagged = (yB == 0) & (oof_pred_b[CHOSEN] == 1)
task_b_errors = {
    "spam passed as legitimate": int(missed.sum()), "legitimate flagged": int(wrongly_flagged.sum()),
    "median length, missed spam": float(np.median(lengths[missed])), "median length, caught spam": float(np.median(lengths[caught])),
    "missed spam with a URL": float(merged.loc[missed, "text"].str.contains("http", case=False).mean()),
    "caught spam with a URL": float(merged.loc[caught, "text"].str.contains("http", case=False).mean()),
    "script of missed spam": merged.loc[missed, "script"].value_counts().to_dict(),
}
print("\ncross-validation errors of the chosen model:")
for key, value in task_b_errors.items():
    print(f"   {key}: {value if not isinstance(value, float) else round(value, 2)}")
print("examples of missed spam:")
for text in merged.loc[missed, "text"].sample(6, random_state=SEED):
    print("   ", repr(text[:90]))
METRICS["task_b"]["errors"] = task_b_errors

# %% [markdown]
# **Analysis.**
#
# - *The genuine message it flags* is a request for a quotation. Its words ("company", "page", "profile") are
#   commerce words the model has only ever seen in spam, and even "hello" counts toward spam because SMS
#   messages rarely start that way. This is the source difference again, visible in a single prediction.
# - *The spam it misses is short.* Missed templates have a median length of about 23 characters against about
#   350 for the caught ones, and only about one in ten contains a link. They are bare names, random strings and
#   the one-line price enquiry in its many languages. A bag-of-words model has almost nothing to read in them.
# - *The two defences share a blind spot.* These are the same senders that evade the honeypot (Sections 5 and
#   7). What does identify them is their shape: short, no link, joined name. The association rules capture
#   exactly that, which is why the scoring service reports the matched rules with every prediction. Adding
#   shape features to the classifier is the obvious next step.
#
# ## 9.7 Summary of Task B
#
# **Analysis of Task B.**
#
# - **In-distribution scores are high and close.** Every word-based model reaches a balanced accuracy of about
#   0.95 to 0.97, and the best AUC is above 0.99. On these numbers alone the task looks solved.
# - **Much of that is the source difference.** Message length alone, with no words, already reaches a balanced
#   accuracy near 0.79. The word lists say the same thing: the tokens that most indicate "spam" are URL
#   fragments and Cyrillic words, and the tokens that most indicate "legitimate" are SMS slang. The models
#   learned the difference between two collections at least as much as the difference between spam and
#   non-spam.
# - **Words still carry real signal.** Restricting both classes to 20-200 characters pushes the length baseline
#   down to chance, while the word models keep a balanced accuracy of 0.94 or more. Removing non-Latin
#   messages changes little.
# - **The same-source test is the decisive one.** With SMS on both sides, the models still rank SMS spam above
#   legitimate SMS (AUC well above 0.5 for most of them), so something about spam itself was learned. At the
#   default threshold, though, most of them catch well under half of the SMS spam. The models know *form* spam;
#   that knowledge transfers only partly to another kind of spam.
# - **Higher in-distribution accuracy did not mean a better filter.** The perceptron and the MLP top the
#   cross-validation table and also flag the most genuine contact-form messages. Naive Bayes, logistic
#   regression and the decision tree flag almost none. The extra accuracy of the flexible models came from
#   fitting the two collections more tightly.
# - **Naive Bayes smoothing.** Most of the vocabulary never occurs in the legitimate class, so without smoothing
#   almost every spam word would force a zero probability. Laplace smoothing (alpha = 1) fixes that but is not
#   the best value here: the legitimate class is small, and adding one count for each of 17,000 vocabulary
#   words flattens its word distribution. Smaller alpha values score higher.
# - **Decision threshold.** The threshold table shows the trade-off for the chosen model; the software exposes
#   the threshold as a setting.
# - **Limits of this result.** The legitimate class is SMS, not real contact-form traffic, and the 40 genuine
#   messages are synthetic. The scores describe this corpus. The model must be re-trained on the operator's own
#   legitimate submissions once the form collects them.
