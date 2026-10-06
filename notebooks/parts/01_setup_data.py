# %% [markdown]
# # FormTrap-DM: Mining Five Years of Contact-Form Spam
#
# One public website contact form received 5,766 submissions between August 2020 and May 2025.
# None of them was a genuine enquiry. The form carried a hidden "honeypot" field that humans cannot see
# and that naive bots fill in. This notebook mines that data.
#
# ## Why data mining is needed here
#
# 1. **The honeypot is not dependable.** Section 4 shows its hit rate swinging between 98% of submissions in
#    2022 and about 10% in late 2023, depending on which campaign is active, and Section 1.3 shows twelve months
#    in which the signal is missing altogether. Detection therefore has to come from the *content* of a
#    submission, which means learning patterns from past data.
# 2. **The existing filter is guesswork.** The FormTrap software scores submissions with 14 hand-written rules
#    and hand-picked weights. Mining replaces those guesses with rules and weights learned from the data.
# 3. **Spam arrives in campaigns.** Many messages are copies or near-copies of each other. Nobody labelled the
#    campaigns, so they have to be discovered.
# 4. **Nobody can read thousands of rows.** Summaries over time, topic, language and honeypot status are needed
#    to see what is going on.
#
# ## Types of learning used
#
# | Type | Labels | Used for | Algorithms | Section |
# | --- | --- | --- | --- | --- |
# | Descriptive analysis (no learning) | none | Summarising and comparing records | Distance and similarity measures, OLAP | 3, 4 |
# | **Unsupervised learning** | none | Finding structure nobody labelled | Apriori, PCA, K-means, K-medoids, EM | 5, 6, 7 |
# | **Supervised learning: classification** | observed | Task A (honeypot evasion), Task B (spam vs legitimate) | Naive Bayes, logistic regression, decision tree, KNN, Mahalanobis classifier, perceptron / MLP | 8, 9, 10 |
# | **Supervised learning: regression** | observed counts | Trend of spam volume and honeypot hit rate | Linear and polynomial regression | 11 |
#
# Deliberately **not** used:
#
# - *Semi-supervised learning on rule-made labels.* If labels are produced by rules and a model is then scored
#   against those same rules, the evaluation is circular. Every label in this notebook is observed.
# - *Deep CNN / RNN models.* A few thousand short messages and a small target server do not justify them.
# - *Reinforcement learning.* There is no agent, action or reward in this problem.
#
# ## The two supervised tasks
#
# - **Task A, honeypot evasion.** Label: did the sender fill the hidden honeypot field (observed by the form).
#   Features: the message and the contact fields. Nothing derived from the honeypot field itself is a feature.
# - **Task B, spam vs legitimate.** Label: 1 for a message from this form, 0 for a legitimate message from a
#   public corpus. The two classes come from different sources, so Section 9 includes checks for whether the
#   models learned "spam" or only "which source".
#
# Every algorithm section uses the same five headings: **What it is / Type of learning / Why it is needed here /
# Implementation / Analysis of results.** "From scratch" means a short NumPy version that follows the hand
# calculation from the lectures and is checked against the library result.

# %%
import glob
import itertools
import json
import math
import os
import pickle
import re
import time
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from IPython.display import display
from matplotlib.colors import LinearSegmentedColormap

warnings.filterwarnings("ignore")
SEED = 42
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_colwidth", 90)
pd.set_option("display.float_format", lambda v: f"{v:.3f}")

# Chart conventions: fixed colour order (validated for colour-blind separation), one axis per chart,
# thin marks, solid hairline grid, text always in ink colours.
INK, INK2, MUTED, GRID, AXIS, GRAY = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#c3c2b7"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
DIV = LinearSegmentedColormap.from_list("div_blue_red", ["#184f95", "#6da7ec", "#f0efec", "#ee8f8e", "#b52b2b"])
plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.grid": True, "axes.axisbelow": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.labelsize": 9.5, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "lines.linewidth": 2, "lines.markersize": 6, "lines.markeredgecolor": "white", "lines.markeredgewidth": 1.2,
    "legend.frameon": False, "legend.fontsize": 9, "axes.prop_cycle": plt.cycler(color=C),
})


# Where the dataset is downloaded from when it is not on this machine (for example on Colab): the "raw"
# address of the folder that holds the CSV files, in a GitHub repository or a gist. Examples:
#   https://raw.githubusercontent.com/<user>/<repository>/main/data/prepared
#   https://gist.githubusercontent.com/<user>/<gist id>/raw
DATA_URL = os.environ.get("FORMTRAP_DATA_URL", "https://raw.githubusercontent.com/ajpalok/FormTrap-DM/main/data/prepared")
DATA_FILES = ["formtrap_spam_clean.csv", "formtrap_features.csv", "formtrap_spam_ham_merged.csv",
              "external_sms_spam_check.csv", "legit_contact_form_holdout.csv", "prep_log.json"]


def search_data():
    for d in ["/kaggle/input/*", "/kaggle/input/*/*", "/content", "/content/*", "/content/drive/MyDrive/*",
              "../data/prepared", "data/prepared", "formtrap_data", "."]:
        for hit in glob.glob(os.path.join(d, "formtrap_features.csv")):
            return os.path.dirname(hit)
    return None


def download_data(base_url, target="formtrap_data"):
    """Fetch the dataset files from raw GitHub (or gist) links. Returns the folder, or None if unreachable."""
    import urllib.request
    os.makedirs(target, exist_ok=True)
    try:
        for name in DATA_FILES:
            urllib.request.urlretrieve(base_url.rstrip("/") + "/" + name, os.path.join(target, name))
    except Exception as error:
        print(f"could not download the dataset from {base_url}: {error}")
        return None
    print(f"dataset downloaded from {base_url}")
    return target


def find_data():
    """Locate the dataset: a local copy, Kaggle input, a download from DATA_URL, or (on Colab) an uploaded zip."""
    found = search_data()
    if found is None and DATA_URL:
        found = download_data(DATA_URL)
    if found is None:
        try:
            from google.colab import files
        except ImportError:
            files = None
        if files is not None:
            import zipfile
            print("Choose formtrap_dataset.zip (from the release folder)")
            for name in files.upload():
                if name.endswith(".zip"):
                    zipfile.ZipFile(name).extractall("/content/formtrap")
            found = search_data()
    if found is None:
        raise FileNotFoundError("Dataset not found. Set DATA_URL to the raw GitHub address of the CSV files, "
                                "or upload formtrap_dataset.zip when asked (Colab), or add the dataset (Kaggle).")
    return found


DATA = find_data()
ART = os.environ.get("FORMTRAP_ARTIFACTS", "artifacts")
FIG = os.path.join(ART, "figures")
os.makedirs(FIG, exist_ok=True)
METRICS = {}          # every number used by the paper and the software is collected here


def savefig(name):
    plt.tight_layout()
    plt.savefig(os.path.join(FIG, name + ".png"), bbox_inches="tight")
    plt.show()
    plt.close()


def barh(ax, labels, values, color=None, fmt="{:.2f}", xlabel=""):
    """Horizontal bars, one hue, value written at the tip."""
    labels, values = list(labels), list(values)
    ax.barh(labels, values, color=color or C[0], height=0.62)
    span = max(values) if values and max(values) > 0 else 1
    for y, v in enumerate(values):
        ax.text(v + span * 0.012, y, fmt.format(v), va="center", fontsize=8.5, color=INK2)
    ax.set_xlim(0, span * 1.14)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(xlabel)


def show(table, pct=(), ints=()):
    """Display a table with some columns written as percentages or whole numbers."""
    out = table.copy()
    for col in pct:
        out[col] = out[col].map(lambda v: "-" if pd.isna(v) else f"{v:.1%}")
    for col in ints:
        out[col] = out[col].astype(int)
    display(out)


print("data folder:", DATA, "| artifacts folder:", ART)

# %%
clean = pd.read_csv(os.path.join(DATA, "formtrap_spam_clean.csv"), parse_dates=["timestamp"])
feat = pd.read_csv(os.path.join(DATA, "formtrap_features.csv"))
merged = pd.read_csv(os.path.join(DATA, "formtrap_spam_ham_merged.csv"))
holdout = pd.read_csv(os.path.join(DATA, "legit_contact_form_holdout.csv"))
sms_spam = pd.read_csv(os.path.join(DATA, "external_sms_spam_check.csv"))
with open(os.path.join(DATA, "prep_log.json"), encoding="utf-8") as fh:
    prep = json.load(fh)

clean["message"] = clean["message"].fillna("").astype(str)
clean["template_id"] = clean["template_id"].fillna("").astype(str)
shared = ["source_block", "has_message", "script", "template_id", "template_count", "email_domain", "honeypot_filled",
          "honeypot_reliable"]
df = clean.merge(feat.drop(columns=shared), on="id")

TEXT_F = ["msg_len", "word_count", "avg_word_len", "line_count", "url_count", "email_mentions", "phone_mentions",
          "digit_ratio", "upper_ratio", "special_ratio", "non_ascii_ratio", "cyrillic_ratio", "char_entropy",
          "exclam_count", "has_bbcode", "has_html", "has_repeat", "kw_money", "kw_crypto", "kw_seo", "kw_pharma",
          "kw_adult", "kw_gambling", "kw_unsub"]
CONTACT_F = ["has_name", "name_len", "name_words", "name_has_digit", "name_joined", "name_equals_msg", "has_email",
             "email_valid", "email_local_len", "email_local_digits", "email_free", "email_ru", "has_phone",
             "phone_digits", "phone_ru_format", "phone_has_letters", "field_completion_ratio"]

print(f"submissions: {len(df):,} | columns: {df.shape[1]} | spam-vs-legitimate corpus: {len(merged):,} rows")
display(df[["id", "timestamp", "source_block", "script", "message", "template_count", "email_domain",
            "honeypot_filled"]].assign(message=lambda d: d["message"].str[:70]).head(5))

# %% [markdown]
# # 1. Data understanding
#
# The published dataset is the cleaned and anonymized version of the raw export. Names, e-mail addresses and
# phone numbers were removed before publication; only features derived from them remain. The raw-data
# statistics below come from `prep_log.json`, written by the preparation script.
#
# ## 1.1 Types of attributes

# %%
attr_types = pd.DataFrame([
    ("message", "unstructured text", "what the sender wrote (e-mails, phones, site name masked)"),
    ("script, email_domain, source_block", "nominal", "categories with no order"),
    ("part_of_day, len_bin (created in 2.4)", "ordinal", "ordered categories"),
    ("timestamp", "interval", "differences are meaningful, there is no true zero"),
    ("year, quarter, month, hour", "ordinal / interval", "levels of the time hierarchy used by OLAP"),
    ("msg_len, word_count, url_count, name_len ...", "ratio, discrete", "counts with a true zero"),
    ("digit_ratio, upper_ratio, char_entropy ...", "ratio, continuous", "measured quantities"),
    ("has_bbcode, kw_*, has_email, name_joined ...", "binary, asymmetric", "presence of a trait is the informative value"),
    ("honeypot_filled", "binary class label", "1 = hidden field was filled, 0 = left empty, blank = unknown"),
], columns=["attribute", "type", "note"])
display(attr_types)

# %% [markdown]
# ## 1.2 Data quality: missing values, duplicates, noise

# %%
raw_total = prep["steps"][0]["rows"]
missing = (pd.Series(prep["raw_missing"]) / raw_total * 100).sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(6.4, 3.2))
barh(ax, missing.index, missing.values, fmt="{:.0f}%", xlabel="missing values in the raw export (%)")
ax.set_title("Most raw columns are more than 40% empty")
savefig("fig_missing_raw")

steps = pd.DataFrame(prep["steps"])
steps["removed"] = -steps["rows"].diff().fillna(0).astype(int)
display(steps)

known = df["honeypot_filled"].notna()
quality = pd.Series({
    "raw rows": raw_total,
    "rows after cleaning": len(df),
    "rows where First = Middle = Last name (redundant columns)": prep["redundant_name_rows"],
    "rows with an empty message": int((df["has_message"] == 0).sum()),
    "rows whose message repeats another row's template": int((df["template_count"] > 1).sum()),
    "distinct message templates": int(df.loc[df["template_id"] != "", "template_id"].nunique()),
    "rows with a recorded honeypot label": int(known.sum()),
    "  of which honeypot filled": int((df["honeypot_filled"] == 1).sum()),
    "  of which honeypot left empty": int((df["honeypot_filled"] == 0).sum()),
    "rows with unknown label (older export, no timestamp)": int((~known).sum()),
})
display(quality.to_frame("count"))
display(df["script"].value_counts().to_frame("rows by writing system"))
METRICS["data"] = {k.strip(): int(v) for k, v in quality.items()}
METRICS["data"]["script"] = df["script"].value_counts().to_dict()

# %%
# Noise: a few extreme values dominate the raw scale of the count features.
display(df[["msg_len", "word_count", "url_count", "name_len", "email_local_len"]]
        .describe(percentiles=[0.5, 0.95, 0.99]).T[["50%", "95%", "99%", "max"]])

# %% [markdown]
# **What the quality report shows**
#
# - **Missing values.** Two exports were merged into the sheet. The older one has no timestamp and no honeypot
#   column, which is why those two columns are about half empty. For those rows the honeypot label is *unknown*,
#   not "not filled", so they are kept for unsupervised mining and left out of Task A.
# - **Redundant attributes.** `First name`, `Middle name` and `Last name` hold the same string in most rows that
#   have them. They were merged into one name before features were computed.
# - **Duplicates.** Exact duplicate rows were removed. Repeated *templates* were kept and counted
#   (`template_count`), because repetition is the signature of a campaign.
# - **Noise.** The maximum message length sits at the 32,767-character limit of a spreadsheet cell, and some
#   "names" are several hundred characters long because a bot pasted its message into the name field. The 99th
#   percentile is far below the maximum for every count feature, so these features are log-transformed before
#   any distance-based method (Section 2.5).

# %% [markdown]
# ## 1.3 A data-quality finding: twelve months without a single honeypot hit
#
# Checking the label before using it turned up one pattern that changes how it must be read. The timestamped
# submissions are sorted by time and split into *runs* of consecutive submissions that left the honeypot empty.

# %%
stamped = df[df["timestamp"].notna()].sort_values(["timestamp", "id"])
empty = stamped["honeypot_filled"].eq(0).to_numpy()
run_id = np.cumsum(~empty)                                   # a new run starts after every filled submission
runs = (stamped[empty].groupby(run_id[empty])
        .agg(first=("timestamp", "min"), last=("timestamp", "max"), submissions=("id", "size"))
        .sort_values("submissions", ascending=False))
runs["days"] = (runs["last"] - runs["first"]).dt.days
display(runs.head(5).reset_index(drop=True))

in_window = df["id"].isin(set(stamped["id"][empty & (run_id == runs.index[0])])).to_numpy()
assert (in_window == df["honeypot_reliable"].eq(0).to_numpy()).all()    # the same rows are flagged in the dataset
win_start, win_end = runs["first"].iloc[0], runs["last"].iloc[0]

before = stamped[(stamped["timestamp"] < win_start) & (stamped["timestamp"] >= win_start - pd.Timedelta(days=90))]
after = stamped[(stamped["timestamp"] > win_end) & (stamped["timestamp"] <= win_end + pd.Timedelta(days=90))]
print(f"90 days before the run: {before['honeypot_filled'].mean():.0%} of {len(before)} submissions filled the honeypot")
print(f"inside the run:         0% of {int(in_window.sum())} submissions, {win_start:%d %b %Y} to {win_end:%d %b %Y}")
print(f"90 days after the run:  {after['honeypot_filled'].mean():.0%} of {len(after)} submissions filled the honeypot")

outside = df[~in_window & df["honeypot_filled"].notna() & (df["template_id"] != "")]
both = set(outside["template_id"]) & set(df.loc[in_window, "template_id"])
same_out = outside[outside["template_id"].isin(both)]
n_in = int((in_window & df["template_id"].isin(both).to_numpy()).sum())
p_out = float(same_out["honeypot_filled"].mean())
print(f"\n{len(both)} message templates occur both inside and outside the run. Outside it they fill the honeypot in "
      f"{p_out:.1%} of {len(same_out)} submissions; inside it in 0 of {n_in}.")
print(f"If their behaviour were unchanged, the chance of 0 hits in {n_in} submissions would be (1 - {p_out:.3f})^{n_in} = {(1 - p_out) ** n_in:.1e}")
print(f"share of submissions with an e-mail address: {before['has_email'].mean():.0%} before the run, "
      f"{df.loc[in_window, 'has_email'].mean():.0%} inside it, {after['has_email'].mean():.0%} after it")

df["honeypot_recorded"] = df["honeypot_filled"]              # the label exactly as exported
df.loc[in_window, "honeypot_filled"] = np.nan                # from here on: unknown inside the run
known = df["honeypot_filled"].notna()
label_counts = pd.Series({
    "label recorded": int(df["honeypot_recorded"].notna().sum()),
    "  inside the run, treated as unknown": int(in_window.sum()),
    "label used in this notebook": int(known.sum()),
    "  of which honeypot filled": int((df["honeypot_filled"] == 1).sum()),
    "  of which honeypot left empty": int((df["honeypot_filled"] == 0).sum()),
})
display(label_counts.to_frame("rows"))
METRICS["data"].update({k.strip(): int(v) for k, v in label_counts.items()})
METRICS["window"] = {"start": str(win_start), "end": str(win_end), "rows": int(in_window.sum()),
                     "days": int(runs["days"].iloc[0]), "second_longest_rows": int(runs["submissions"].iloc[1]),
                     "second_longest_days": int(runs["days"].iloc[1]),
                     "hit_rate_90d_before": float(before["honeypot_filled"].mean()),
                     "hit_rate_90d_after": float(after["honeypot_filled"].mean()),
                     "shared_templates": len(both), "shared_hit_rate_outside": p_out, "shared_rows_inside": n_in,
                     "chance_of_zero": float((1 - p_out) ** n_in)}

# %% [markdown]
# **Reading the evidence.**
#
# - The longest run is about 650 submissions over a full year. The second longest is under 100 submissions in a
#   few days, which is a burst of one campaign.
# - In the three months before the run about a third of submissions filled the honeypot; in the three months
#   after it almost all did. Inside it: none.
# - Templates that appear on both sides of the boundary do fill the honeypot outside the run and never inside
#   it. Under unchanged behaviour that outcome has a probability that is effectively zero.
# - The contact fields change at the end of the run too (the share of submissions carrying an e-mail address
#   drops), which points to a change of the form itself.
#
# Every bot changing its behaviour on the same day, for exactly one year, is not a credible explanation. The
# simplest one is that the honeypot field was not on the form during this period. The site's operator has
# since confirmed it: **the form did not implement the honeypot at that time.**
#
# **Decision.** Inside the run, "not filled" is read as "unknown". Those rows are real spam and stay in the
# unsupervised analyses (similarity, clustering). They are left out of everything that uses the label: hit
# rates, the association rules about the honeypot, and Task A. Section 8 also shows what Task A would have
# reported had the recorded label been trusted. The dataset ships the recorded label together with a
# `honeypot_reliable` flag, so that others can make their own choice.
