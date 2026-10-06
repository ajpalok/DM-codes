"""Build the prepared, anonymized FormTrap dataset from the raw contact-form export.

Usage: python src/prepare_dataset.py
Reads  data/raw/Contact Form (Responses).xlsx  and  data/external/SMSSpamCollection
Writes data/prepared/*.csv, prep_log.json, README.md, dataset-metadata.json
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import features as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Contact Form (Responses).xlsx"
HAM = ROOT / "data" / "external" / "SMSSpamCollection"
OUT = ROOT / "data" / "prepared"
SEED = 42
MIN_DOMAIN_COUNT = 5      # rarer e-mail domains are published as "other"

log = {"steps": []}


def step(name, df):
    log["steps"].append({"step": name, "rows": int(len(df))})
    print(f"{name:<45} {len(df):>6}")


def clean_cell(v):
    if isinstance(v, float) and not np.isnan(v) and v.is_integer():
        v = int(v)                                   # phone numbers stored as numbers
    return F._s(v) or np.nan


def join_unique(values):
    seen = []
    for v in values:
        if isinstance(v, str) and v not in seen:
            seen.append(v)
    return " ".join(seen) if seen else np.nan


def part_of_day(hour):
    if pd.isna(hour):
        return np.nan
    return ["night", "morning", "afternoon", "evening"][int(hour) // 6]


def load_raw():
    df = pd.read_excel(RAW, sheet_name="SpamCleaned")
    step("1 raw rows", df)
    log["raw_missing"] = {c: int(df[c].isna().sum()) for c in df.columns}
    for c in df.columns.drop("Timestamp"):
        df[c] = df[c].map(clean_cell)
    return df


def clean(df):
    split = ["First name", "Middle name", "Last name"]
    log["redundant_name_rows"] = int((df[split].nunique(axis=1) == 1).sum())
    out = pd.DataFrame({
        "timestamp": df["Timestamp"],
        "name": df["Full name"].where(df["Full name"].notna(), df[split].apply(join_unique, axis=1)),
        "email": df["Email"],
        "phone": df["Phone Number"],
        "text": df[["Subject", "Message"]].apply(lambda r: "\n".join(v for v in r if isinstance(v, str)) or np.nan, axis=1),
        "honeypot_url": df["URL-honeypot"],
    })
    out["source_block"] = np.where(out["timestamp"].notna(), "A_timestamped", "B_legacy")
    out["form_version"] = np.select(
        [df[split].notna().any(axis=1), out["timestamp"].notna()], ["v1_split_name", "v2_full_name"], "legacy_export")

    content = ["name", "email", "phone", "text"]
    out = out[out[content].notna().any(axis=1)]
    step("2 after dropping rows with no content", out)
    out = out.drop_duplicates(subset=["timestamp"] + content + ["honeypot_url"])
    step("3 after dropping exact duplicates", out)

    # The honeypot field only exists in the timestamped export; for legacy rows the label is unknown.
    out["honeypot_filled"] = np.where(out["timestamp"].notna(), out["honeypot_url"].notna().astype(float), np.nan)
    out = out.reset_index(drop=True)
    out.insert(0, "id", out.index + 1)
    return flag_unrecorded_window(out)


def flag_unrecorded_window(out):
    """Flag the longest run of consecutive unfilled submissions.

    One run is 646 rows and twelve months long while the next longest lasts four days, and the months on either
    side of it show normal hit rates. The site operator confirmed the form had no honeypot field then, so
    "not filled" cannot be trusted there. The recorded label is kept; honeypot_reliable says whether to use it.
    """
    stamped = out[out["timestamp"].notna()].sort_values(["timestamp", "id"])
    empty = stamped["honeypot_filled"].eq(0).to_numpy()
    run_id = np.cumsum(~empty)
    runs = (stamped[empty].groupby(run_id[empty])
            .agg(start=("timestamp", "min"), end=("timestamp", "max"), rows=("id", "size"))
            .sort_values("rows", ascending=False))
    longest, second = runs.iloc[0], runs.iloc[1]
    inside = out["id"].isin(stamped["id"][empty & (run_id == runs.index[0])])
    out["honeypot_reliable"] = np.where(out["honeypot_filled"].isna(), np.nan, (~inside).astype(float))
    log["honeypot_window"] = {"start": str(longest["start"]), "end": str(longest["end"]), "rows": int(longest["rows"]),
                              "second_longest_run_rows": int(second["rows"]),
                              "second_longest_run_days": int((second["end"] - second["start"]).days)}
    print(f"longest run of unfilled honeypot: {int(longest['rows'])} rows, {longest['start']} to {longest['end']}")
    return out


def build_features(df):
    df["message"] = [F.mask_pii(t, n) for t, n in zip(df["text"], df["name"])]
    df["has_message"] = (df["message"] != "").astype(int)
    df["script"] = df["message"].map(F.script_of)
    df["template_id"] = df["message"].map(F.template_id)
    counts = df.loc[df["template_id"] != "", "template_id"].value_counts()
    df["template_count"] = df["template_id"].map(counts).fillna(0).astype(int)

    text = pd.DataFrame([F.text_features(m) for m in df["message"]])
    contact = pd.DataFrame([F.contact_features(n, e, p, t)
                            for n, e, p, t in zip(df["name"], df["email"], df["phone"], df["text"])])

    domain = df["email"].str.lower().str.extract(r"@([\w.\-]+)$")[0]
    common = domain.value_counts()
    common = set(common[common >= MIN_DOMAIN_COUNT].index)
    df["email_domain"] = np.where(domain.isna(), "none", np.where(domain.isin(common), domain, "other"))

    ts = df["timestamp"]
    time = pd.DataFrame({
        "year": ts.dt.year, "quarter": ts.dt.quarter, "month": ts.dt.month,
        "weekday": ts.dt.day_name(), "hour": ts.dt.hour,
        "part_of_day": ts.dt.hour.map(part_of_day),
        "year_month": ts.dt.strftime("%Y-%m"),
    })
    return df, text, contact, time


def build_merged(df):
    spam = df[df["has_message"] == 1].drop_duplicates("template_id")
    spam = pd.DataFrame({"text": spam["message"], "label": 1, "source": "formtrap", "script": spam["script"]})

    sms = pd.read_csv(HAM, sep="\t", header=None, names=["cls", "text"], quoting=3, encoding="utf-8")
    sms["text"] = sms["text"].map(F.mask_pii)
    sms["tid"] = sms["text"].map(F.template_id)
    sms = sms[sms["tid"] != ""].drop_duplicates("tid")
    sms["script"] = sms["text"].map(F.script_of)
    ham = sms.loc[sms["cls"] == "ham", ["text", "script"]].assign(label=0, source="sms_ham_uci")
    # SMS spam is never used for training: it tests whether a model learned "spam" or only "which source".
    sms_spam = sms.loc[sms["cls"] == "spam", ["text", "script"]].assign(label=1, source="sms_spam_uci")

    cols = ["text", "label", "source", "script"]
    merged = pd.concat([spam[cols], ham[cols]]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    log["merged"] = {"spam_unique_templates": int(len(spam)), "ham_unique": int(len(ham)),
                     "sms_spam_check": int(len(sms_spam))}
    return merged, sms_spam[cols].reset_index(drop=True)


def pii_scan(df, published_texts):
    """Fail if any raw e-mail, phone number or sender name survives in a published text column."""
    blob = "\n".join(published_texts).lower()
    hits = {"email_pattern": len(F.EMAIL_RE.findall(blob)), "phone_pattern": len(F.PHONE_RE.findall(blob))}
    emails = {e.lower() for e in df["email"].dropna() if "@" in e}
    phones = {d for d in (re.sub(r"\D", "", p) for p in df["phone"].dropna()) if len(d) >= 7}
    hits["raw_email_literal"] = sum(e in blob for e in emails)
    hits["raw_phone_literal"] = sum(p in blob for p in phones)
    hits["own_name_in_message"] = int(sum(
        len(n) >= 5 and len(n.split()) >= 2 and n.lower() in m.lower()
        for n, m in zip(df["name"].fillna(""), df["message"])))
    log["pii_scan"] = hits
    print("PII scan:", hits)
    assert not any(hits.values()), f"PII left in published text: {hits}"


def write_card(df, merged):
    n, a, w = len(df), int(df["honeypot_filled"].notna().sum()), log["honeypot_window"]
    filled = int((df["honeypot_filled"] == 1).sum())
    ts = df["timestamp"].dropna()
    card = f"""# FormTrap contact-form spam, {ts.min():%Y}-{ts.max():%Y}

Real submissions received by one public website contact form between {ts.min():%B %Y} and {ts.max():%B %Y}.
Every row is unsolicited (spam or bot traffic); the form received no genuine enquiries in the exported sheets.
The form carried a hidden honeypot URL field, so for part of the data we know whether the sender filled it.

## Files

| File | Rows | Content |
| --- | --- | --- |
| `formtrap_spam_clean.csv` | {n:,} | One row per submission: masked message text, template id, coarse e-mail domain, honeypot label |
| `formtrap_features.csv` | {n:,} | Engineered numeric features for the same rows (join on `id`) |
| `formtrap_spam_ham_merged.csv` | {len(merged):,} | Spam-vs-legitimate corpus: {log['merged']['spam_unique_templates']:,} unique spam templates from this form + {log['merged']['ham_unique']:,} legitimate SMS messages |
| `external_sms_spam_check.csv` | {log['merged']['sms_spam_check']:,} | SMS spam from the same public collection as the legitimate SMS. Never used for training; it checks whether a model learned spam or only the source |
| `legit_contact_form_holdout.csv` | 40 | Hand-written legitimate contact-form style messages, used only as an out-of-domain check. **Synthetic.** |
| `prep_log.json` | - | Row count after each cleaning step and the PII scan result |

## Labels

- `honeypot_filled` (in the first two files): 1 if the hidden honeypot field was filled, 0 if left empty,
  blank if unknown. Recorded for the {a:,} timestamped rows ({filled:,} filled, {a - filled:,} not filled).
  The {n - a:,} rows from the older export have no timestamp and no honeypot column.
- `honeypot_reliable`: 0 for the {w['rows']:,} submissions between {w['start'][:10]} and {w['end'][:10]}, 1 for the
  other labelled rows. In that window not a single submission has the honeypot filled, for twelve months in a
  row, while the next longest such run is {w['second_longest_run_rows']} rows in {w['second_longest_run_days']} days and the months
  just before and after show ordinary hit rates. The form did not include the honeypot field in that period
  (confirmed by the site operator), so "not filled" should be read as "unknown" there. **Use `honeypot_filled` only where
  `honeypot_reliable` is 1.**
- `label` (merged file): 1 = spam from this form, 0 = legitimate message from another source.
  The two classes come from different sources, so a classifier can partly learn the source. Treat scores on this
  file as optimistic and check them on `legit_contact_form_holdout.csv`.

## Columns of `formtrap_spam_clean.csv`

`id`, `timestamp`, `source_block` (A_timestamped / B_legacy), `form_version`, `message`, `has_message`, `script`
(latin / cyrillic / other / none), `template_id` (hash of the message with URLs, numbers, e-mails and phones
replaced by tokens), `template_count` (rows sharing that template), `email_domain`, `honeypot_filled`,
`honeypot_reliable`.

## Columns of `formtrap_features.csv`

Text features: {", ".join(F.TEXT_FEATURES)}.

Contact-field features (computed on the raw fields, which are not published): {", ".join(F.CONTACT_FEATURES)}.

Time features: year, quarter, month, weekday, hour, part_of_day, year_month.

## Anonymization

- Sender name, e-mail address and phone number columns are removed. Only features derived from them are kept.
- Only the e-mail domain is kept, and only when at least {MIN_DOMAIN_COUNT} rows share it; otherwise `other`.
- Inside message text, e-mail addresses become `<EMAIL>`, phone numbers and other long digit runs become `<PHONE>`,
  the receiving site's name becomes `<SITE>`, and the sender's own name becomes `<NAME>`.
- Spam URLs are kept, because they are the main object of study.
- Free text can still contain names that the sender typed and that do not match the name field.

## Sources and licence

- Spam rows: collected by the dataset authors from their own website contact form.
- Legitimate SMS rows: SMS Spam Collection, T. A. Almeida and J. M. Gomez Hidalgo, UCI Machine Learning
  Repository, https://archive.ics.uci.edu/dataset/228/sms+spam+collection, licensed CC BY 4.0.
- This dataset is released under CC BY 4.0.
"""
    (OUT / "README.md").write_text(card, encoding="utf-8")
    meta = {"title": "FormTrap Contact-Form Spam 2020-2025",
            "id": "KAGGLE_USERNAME/formtrap-contact-form-spam",
            "licenses": [{"name": "CC-BY-4.0"}]}
    (OUT / "dataset-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = clean(load_raw())
    df, text, contact, time = build_features(df)
    merged, sms_spam = build_merged(df)

    clean_cols = ["id", "timestamp", "source_block", "form_version", "message", "has_message", "script",
                  "template_id", "template_count", "email_domain", "honeypot_filled", "honeypot_reliable"]
    feats = pd.concat([df[["id", "source_block", "has_message", "script", "template_id", "template_count",
                           "email_domain"]], text, contact, time, df[["honeypot_filled", "honeypot_reliable"]]], axis=1)

    pii_scan(df, list(df["message"]) + list(merged["text"]) + list(sms_spam["text"]) + list(df["email_domain"]))

    df[clean_cols].to_csv(OUT / "formtrap_spam_clean.csv", index=False)
    feats.to_csv(OUT / "formtrap_features.csv", index=False)
    merged.to_csv(OUT / "formtrap_spam_ham_merged.csv", index=False)
    sms_spam.to_csv(OUT / "external_sms_spam_check.csv", index=False)

    log["final"] = {
        "rows": int(len(df)),
        "with_message": int(df["has_message"].sum()),
        "honeypot_known": int(df["honeypot_filled"].notna().sum()),
        "honeypot_reliable": int((df["honeypot_reliable"] == 1).sum()),
        "honeypot_filled": int((df["honeypot_filled"] == 1).sum()),
        "unique_templates": int(df.loc[df["template_id"] != "", "template_id"].nunique()),
        "script": df["script"].value_counts().to_dict(),
        "merged_rows": int(len(merged)),
    }
    (OUT / "prep_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    write_card(df, merged)
    print(json.dumps(log["final"], indent=2))


if __name__ == "__main__":
    main()
