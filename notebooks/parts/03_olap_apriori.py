# %% [markdown]
# # 4. OLAP: summarising five years of submissions
#
# **What it is.** Online analytical processing stores pre-computed summaries of a fact table along several
# dimensions (a *cube*) and answers questions by slicing, dicing, rolling up and drilling down.
# **Type of learning.** None; this is descriptive analysis.
# **Why it is needed here.** The operator's questions are of the form "how many, of what kind, when, and did the
# honeypot catch them?". Those are aggregate questions over time, topic and language, not row lookups.
#
# **Implementation.** The fact table has one row per timestamped submission. Dimensions: time
# (year > quarter > month), part of day, script, topic (from the keyword flags). Measures: number of
# submissions, number with a usable honeypot label, and number of honeypot hits; the hit rate is hits divided by
# labelled submissions. The cube is computed once and every operation below reads the cube, never the raw rows.

# %%
fact = df[df["timestamp"].notna()].copy()
for col in ["year", "quarter", "month", "hour"]:
    fact[col] = fact[col].astype(int)
fact["topic"] = np.select(
    [fact["has_message"].eq(0), fact["kw_crypto"].eq(1), fact["kw_gambling"].eq(1), fact["kw_adult"].eq(1),
     fact["kw_pharma"].eq(1), fact["kw_seo"].eq(1), fact["kw_money"].eq(1)],
    ["no message", "crypto", "gambling", "adult", "pharma", "seo / marketing", "money"], default="other")

DIMS = ["year", "quarter", "month", "part_of_day", "script", "topic"]
MEASURES = ["submissions", "labelled", "honeypot_hits"]
cube = (fact.groupby(DIMS, observed=True)
        .agg(submissions=("id", "size"), labelled=("honeypot_filled", "count"), honeypot_hits=("honeypot_filled", "sum"))
        .reset_index())
print(f"fact table: {len(fact):,} rows  ->  cube: {len(cube):,} pre-computed cells over {len(DIMS)} dimensions")


def summarise(cells, by):
    """Aggregate cube cells to a coarser level and derive the hit rate."""
    out = cells.groupby(by, observed=True)[MEASURES].sum()
    out["hit_rate"] = out["honeypot_hits"] / out["labelled"].where(out["labelled"] > 0)
    return out


def olap_show(table):
    show(table, pct=["hit_rate"], ints=["honeypot_hits"])


def olap_dict(table):
    return {str(k): {"submissions": int(r.submissions), "labelled": int(r.labelled), "hit_rate": r.hit_rate}
            for k, r in table.iterrows()}


# %% [markdown]
# ## 4.1 Roll-up: month -> quarter -> year
#
# Rolling up climbs the time hierarchy: detail is summed away and the long-term picture appears.

# %%
by_year = summarise(cube, ["year"])
olap_show(by_year)
METRICS["olap"] = {"by_year": olap_dict(by_year),
                   "overall_hit_rate": float(cube["honeypot_hits"].sum() / cube["labelled"].sum())}

by_quarter = summarise(cube, ["year", "quarter"])
full = pd.MultiIndex.from_product([range(by_quarter.index[0][0], by_quarter.index[-1][0] + 1), range(1, 5)],
                                  names=["year", "quarter"])
full = full[(full >= by_quarter.index[0]) & (full <= by_quarter.index[-1])]
q = by_quarter.reindex(full)                      # quarters with no export stay empty, they are not zero
q.loc[q["labelled"] < 20, "hit_rate"] = np.nan    # too few labelled rows for a rate
xlabels = [f"{y} Q{k}" for y, k in q.index]
x = np.arange(len(q))


def quarter_pos(ts):
    """Horizontal position of a date on the quarterly axis."""
    return list(q.index).index((ts.year, ts.quarter)) - 0.5 + ((ts.month - 1) % 3 + ts.day / 31) / 3


fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.2, 4.8), sharex=True, gridspec_kw={"height_ratios": [3, 2]})
for ax in (ax1, ax2):
    ax.axvspan(quarter_pos(win_start), quarter_pos(win_end), color=GRID, alpha=0.75, linewidth=0, zorder=0)
ax1.text((quarter_pos(win_start) + quarter_pos(win_end)) / 2, 55, "no honeypot field\non the form", ha="center",
         va="center", fontsize=9, color=INK2)
ax1.plot(x, q["hit_rate"] * 100, color=C[0], marker="o")
hi, lo = int(np.nanargmax(q["hit_rate"])), int(np.nanargmin(q["hit_rate"]))
for pos, dy in ((hi, 8), (lo, -15)):
    ax1.annotate(f"{q['hit_rate'].iloc[pos]:.0%}", (pos, q["hit_rate"].iloc[pos] * 100), xytext=(0, dy),
                 textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax1.set_ylim(0, 112)
ax1.set_ylabel("honeypot filled (%)")
ax1.set_title(f"Honeypot hit rate by quarter: from {q['hit_rate'].iloc[hi]:.0%} down to {q['hit_rate'].iloc[lo]:.0%} and back")
ax2.bar(x, q["submissions"].fillna(0), color=GRAY, width=0.62)
ax2.set_ylabel("submissions")
ax2.set_xticks(x, xlabels, rotation=60, ha="right")
ax2.grid(axis="x", visible=False)
ax1.grid(axis="x", visible=False)
savefig("fig_honeypot_rate")
METRICS["olap"]["by_quarter"] = olap_dict(by_quarter.rename(index=lambda v: str(v)))

# %% [markdown]
# ## 4.2 Drill-down: year 2023 -> quarter -> month
#
# Drilling down goes the other way: take the year in which the rate fell and open it up.

# %%
DRILL_YEAR = 2023
olap_show(summarise(cube[cube["year"] == DRILL_YEAR], ["year", "quarter"]))
drill_month = summarise(cube[cube["year"] == DRILL_YEAR], ["year", "quarter", "month"])
olap_show(drill_month)
METRICS["olap"]["drill_2023_by_month"] = {int(m): r.hit_rate for (_, _, m), r in drill_month.iterrows()}

# %% [markdown]
# ## 4.3 Slice: fix one value of one dimension
#
# A slice fixes a single value on one dimension and returns the remaining sub-cube. Here the time dimension is
# fixed at the fourth quarter of 2023, where the drill-down found the lowest hit rate.

# %%
sl = cube[(cube["year"] == DRILL_YEAR) & (cube["quarter"] == 4)]
slice_topic = summarise(sl, ["topic"]).sort_values("submissions", ascending=False)
olap_show(slice_topic)
olap_show(summarise(sl, ["script"]).sort_values("submissions", ascending=False))
METRICS["olap"]["slice_2023_q4_by_topic"] = olap_dict(slice_topic)

# %% [markdown]
# ## 4.4 Dice: restrict several dimensions at once
#
# A dice picks a set of values on two or more dimensions: the years 2022 and 2023, the two main scripts, and
# messages that carry a topic keyword.

# %%
dice = cube[cube["year"].isin([2022, 2023]) & cube["script"].isin(["latin", "cyrillic"])
            & ~cube["topic"].isin(["no message", "other"])]
dice_tbl = summarise(dice, ["topic", "year", "script"])
display(dice_tbl["hit_rate"].unstack(["year", "script"]).apply(lambda col: col.map(lambda v: "-" if pd.isna(v) else f"{v:.0%}")))
display(dice_tbl["submissions"].unstack(["year", "script"], fill_value=0))

# %% [markdown]
# ## 4.5 Which kind of spam does the honeypot miss?

# %%
by_topic = summarise(cube, ["topic"]).sort_values("submissions", ascending=False)
by_script = summarise(cube, ["script"]).sort_values("submissions", ascending=False)
by_part = summarise(cube, ["part_of_day"]).reindex(["night", "morning", "afternoon", "evening"])
olap_show(by_topic)
olap_show(by_script)
olap_show(by_part)
METRICS["olap"].update(by_topic=olap_dict(by_topic), by_script=olap_dict(by_script), by_part_of_day=olap_dict(by_part))

# %% [markdown]
# **Analysis.**
#
# - *Roll-up* gives the headline: the honeypot caught 79% to 98% of submissions from 2020 to 2022 and under half
#   in 2023. The rate is not a constant of the form.
# - *Drill-down* into 2023 shows when it fell: above 90% in the first months, about two thirds over the summer,
#   and about 10% in October and November.
# - *Slice.* In that quarter three quarters of the submissions carry none of the topic keywords, and only about
#   one in ten of those fills the honeypot. The fall coincides with a wave of a different kind of message.
#   The keyword topics are caught less often than before as well, on small counts.
# - *Dice.* For the same topic and script the hit rate differs between 2022 and 2023, so the topic alone does
#   not determine honeypot behaviour either.
# - Submissions are spread evenly over the day, as expected of automated senders in many time zones.
# - The shaded band is the window of Section 1.3, in which the form had no honeypot field. After it the rate is
#   back above 90%. Gaps in the lower panel are months missing from the export, not months without spam.
#
# This is the motivation for the rest of the notebook: the honeypot signal depends on who is sending and can
# vanish altogether, so the *content* of a submission has to be mined.
#
# # 5. Association rule mining with Apriori
#
# **What it is.** A search for sets of items that occur together often (*frequent itemsets*) and for rules
# `A -> B` between them. A rule is judged by **support** (how often A and B occur together), **confidence**
# (how often B holds when A holds) and **lift** (confidence divided by the base rate of B; above 1 means A
# makes B more likely).
#
# **Type of learning.** Unsupervised: no label is given. The honeypot outcome enters as an ordinary item, so
# rules that end in it can be read off afterwards.
#
# **Why it is needed here.** The software's 14 rules were written by hand. Apriori produces rules of exactly
# the same if-then shape from the data, with measured support and confidence instead of guessed weights.
#
# **Implementation.** Each submission becomes a *transaction*: the set of traits it shows. The traits come from
# the discretized (Section 2.4) and one-hot encoded (Section 2.6) attributes. Apriori is written from scratch
# with the two steps from the lectures: *join* frequent (k-1)-itemsets into candidates of size k, and *prune*
# any candidate that has an infrequent subset (the Apriori property: every subset of a frequent itemset is
# frequent).

# %%
tx = fact[fact["honeypot_filled"].notna()]              # only submissions with a usable label
items = pd.DataFrame({
    "url=none": tx["url_count"].eq(0), "url=one": tx["url_count"].eq(1), "url=2+": tx["url_count"].ge(2),
    "len=empty": tx["msg_len"].eq(0), "len=short": tx["msg_len"].between(1, 50),
    "len=medium": tx["msg_len"].between(51, 300), "len=long": tx["msg_len"].gt(300),
    "script=latin": tx["script"].eq("latin"), "script=cyrillic": tx["script"].eq("cyrillic"),
    "markup=bbcode/html": tx["has_bbcode"].eq(1) | tx["has_html"].eq(1),
    "name=joined": tx["name_joined"].eq(1),
    "email=free": tx["email_free"].eq(1), "email=ru": tx["email_ru"].eq(1), "email=none": tx["has_email"].eq(0),
    "phone=ru_format": tx["phone_ru_format"].eq(1), "phone=none": tx["has_phone"].eq(0),
    "topic=money": tx["kw_money"].eq(1), "topic=seo": tx["kw_seo"].eq(1), "topic=crypto": tx["kw_crypto"].eq(1),
    "honeypot=filled": tx["honeypot_filled"].eq(1), "honeypot=empty": tx["honeypot_filled"].eq(0),
}).reset_index(drop=True)
ITEM = list(items.columns)
M = items.to_numpy()
print(f"{len(items):,} transactions x {len(ITEM)} items; average items per transaction: {M.sum(axis=1).mean():.1f}")
display(items.mean().sort_values(ascending=False).to_frame("support of single item").T.round(2))


# %%
# %include algorithms/apriori.py


def names(itemset):
    return ", ".join(ITEM[j] for j in sorted(itemset))


MIN_SUP, MIN_CONF = 0.10, 0.80
freq = apriori(M, MIN_SUP)
rules = make_rules(freq, MIN_CONF)
by_size = pd.Series([len(s) for s in freq]).value_counts().sort_index()
print(f"min support {MIN_SUP}, min confidence {MIN_CONF}: {len(freq)} frequent itemsets, {len(rules)} rules")
display(by_size.to_frame("frequent itemsets").rename_axis("itemset size").T)

# Worked check of one rule, as in the lectures: support and confidence counted directly from the transactions.
A, Bc = ["url=one", "len=medium", "topic=money"], ["honeypot=filled"]
n_ab = int(items[A + Bc].all(axis=1).sum())
n_a = int(items[A].all(axis=1).sum())
print(f"rule {{{', '.join(A)}}} -> {{{Bc[0]}}}: support = {n_ab}/{len(items)} = {n_ab / len(items):.3f}, "
      f"confidence = {n_ab}/{n_a} = {n_ab / n_a:.3f}, lift = {(n_ab / n_a) / items[Bc[0]].mean():.2f}")

# %%
# Cross-check the frequent itemsets against mlxtend.
try:
    from mlxtend.frequent_patterns import apriori as mlx_apriori
    ref = mlx_apriori(items, min_support=MIN_SUP, use_colnames=True)
    ref_support = {frozenset(ITEM.index(i) for i in s): v for s, v in zip(ref["itemsets"], ref["support"])}
    assert set(ref_support) == set(freq) and all(np.isclose(freq[s], ref_support[s]) for s in freq)
    print(f"from-scratch Apriori and mlxtend agree on all {len(freq)} frequent itemsets and their supports")
except ImportError:
    print("mlxtend is not installed; cross-check skipped (pip install mlxtend)")

# %%
# Sensitivity: how the output grows when the thresholds are relaxed.
grid = []
for sup in (0.05, 0.10, 0.20, 0.30):
    fs = apriori(M, sup)
    row = {"min support": sup, "frequent itemsets": len(fs), "largest itemset": max(map(len, fs))}
    for conf in (0.6, 0.8, 0.9):
        row[f"rules at confidence {conf}"] = len(make_rules(fs, conf))
    grid.append(row)
sensitivity = pd.DataFrame(grid)
display(sensitivity)

# %%
HP = {ITEM.index("honeypot=filled"), ITEM.index("honeypot=empty")}


def honeypot_rules(target, keep=6):
    """Rules ending in one honeypot outcome. A longer rule is listed only if its extra items raise confidence."""
    t = frozenset([ITEM.index(target)])
    sel = rules[(rules["consequent"] == t) & rules["antecedent"].map(lambda a: not (a & HP))].copy()
    sel["size"] = sel["antecedent"].map(len)
    kept = []
    for r in sel.sort_values(["size", "confidence"], ascending=[True, False]).itertuples():
        if not any(k.antecedent < r.antecedent and k.confidence >= r.confidence - 0.02 for k in kept):
            kept.append(r)
    out = pd.DataFrame([{"antecedent": names(r.antecedent), "consequent": target, "support": r.support,
                         "confidence": r.confidence, "lift": r.lift} for r in kept])
    return out.sort_values(["lift", "support"], ascending=False).head(keep).reset_index(drop=True)


top_filled, top_empty = honeypot_rules("honeypot=filled"), honeypot_rules("honeypot=empty")
print("rules that predict the honeypot is FILLED (base rate {:.2f})".format(items["honeypot=filled"].mean()))
display(top_filled)
print("rules that predict the honeypot is left EMPTY (base rate {:.2f})".format(items["honeypot=empty"].mean()))
display(top_empty)

METRICS["apriori"] = {
    "transactions": int(len(items)), "items": len(ITEM), "min_support": MIN_SUP, "min_confidence": MIN_CONF,
    "frequent_itemsets": int(len(freq)), "rules": int(len(rules)),
    "sensitivity": sensitivity.to_dict("records"),
    "top_filled": top_filled.to_dict("records"), "top_empty": top_empty.to_dict("records"),
}

# %% [markdown]
# **Analysis.**
#
# - *Thresholds.* The sensitivity table shows the usual trade-off: lowering the support threshold multiplies the
#   number of itemsets and rules. Support 0.10 and confidence 0.80 keep the rule list short enough to read while
#   every rule still covers at least a tenth of the submissions.
# - *Rules ending in "honeypot filled".* A medium-length message about money fills the honeypot in about 96% of
#   cases, against a base rate of 71%. Reading the matching rows shows one campaign behind this rule: the
#   "financial robot" adverts. That bot completes every field it finds, hidden ones included.
# - *Rules ending in "honeypot empty".* A short message sent under a joined name such as `CarlosSob` leaves the
#   honeypot empty about 88% of the time, three times the base rate of 29%. The matching rows are a single
#   sentence, "Hi, I wanted to know your price", machine-translated into dozens of languages. This sender fills
#   name, e-mail, phone and message correctly and skips the hidden field, so the honeypot does not see it.
# - *What the rules do not show.* A rule reports co-occurrence in the data it was mined from, not cause. The two
#   campaigns were active in different periods (Section 4), so part of each rule is that time effect, and
#   Section 8 shows the one-line enquiry behaving differently in 2025.
# - *Use in the software.* Each rule has the shape of a FormTrap scoring rule and can be shown to the operator
#   with its measured confidence in place of a hand-picked weight.
