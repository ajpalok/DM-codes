"""FormTrap scoring service.

Loads the models exported by notebooks/FormTrap_DM.ipynb and scores one contact-form submission:
spam probability (logistic regression on TF-IDF), campaign (nearest K-means centroid) and the mined
association rules whose conditions the submission meets.

    python app.py            # http://127.0.0.1:5055
"""
import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
from flask import Flask, jsonify, request

HERE = Path(__file__).resolve().parent
ART = Path(os.environ.get("FORMTRAP_ARTIFACTS", HERE / "artifacts"))
sys.path.insert(0, str(HERE))
import features as F  # noqa: E402  (same module the training data was built with)

app = Flask(__name__)
spam_model = joblib.load(ART / "spam_model.joblib")
campaign_model = joblib.load(ART / "campaign_model.joblib")
card = json.loads((ART / "model_card.json").read_text(encoding="utf-8"))
clusters = json.loads((ART / "clusters.json").read_text(encoding="utf-8"))
rules = json.loads((ART / "rules.json").read_text(encoding="utf-8"))

CAMPAIGN_LABEL = {int(c["campaign"]): c["label"] for c in clusters["campaigns"]}
MODEL_VERSION = f'{card["model"]} (scikit-learn {card["sklearn_version"]})'
MINED_RULES = [dict(r, outcome=outcome) for outcome in ("honeypot_filled", "honeypot_empty") for r in rules[outcome]]


def spam_terms(text, k=5):
    """The words in this message that push the score toward spam, strongest first."""
    vectorizer, classifier = spam_model[0], spam_model[-1]
    x = vectorizer.transform([text])
    if hasattr(classifier, "coef_"):
        weights = classifier.coef_[0]
    elif hasattr(classifier, "feature_log_prob_"):
        weights = classifier.feature_log_prob_[1] - classifier.feature_log_prob_[0]
    else:
        return []
    contribution = x.multiply(weights).tocoo()
    vocabulary = vectorizer.get_feature_names_out()
    ranked = sorted(zip(contribution.col, contribution.data), key=lambda p: -p[1])[:k]
    return [{"term": str(vocabulary[j]), "weight": round(float(w), 3)} for j, w in ranked if w > 0]


def campaign_of(text):
    """Nearest campaign centroid; -1 when the message shares no vocabulary with the mined templates."""
    vector = campaign_model["vectorizer"].transform([text])
    if vector.nnz == 0:
        return -1
    return int(campaign_model["kmeans"].predict(campaign_model["lsa"].transform(vector))[0])


def items_of(text, name, email, phone):
    """The Apriori items of a submission, named exactly as in the notebook."""
    t = F.text_features(text)
    c = F.contact_features(name, email, phone, text)
    script = F.script_of(text)
    return {
        "url=none": t["url_count"] == 0, "url=one": t["url_count"] == 1, "url=2+": t["url_count"] >= 2,
        "len=empty": t["msg_len"] == 0, "len=short": 1 <= t["msg_len"] <= 50,
        "len=medium": 51 <= t["msg_len"] <= 300, "len=long": t["msg_len"] > 300,
        "script=latin": script == "latin", "script=cyrillic": script == "cyrillic",
        "markup=bbcode/html": bool(t["has_bbcode"] or t["has_html"]),
        "name=joined": bool(c["name_joined"]),
        "email=free": bool(c["email_free"]), "email=ru": bool(c["email_ru"]), "email=none": not c["has_email"],
        "phone=ru_format": bool(c["phone_ru_format"]), "phone=none": not c["has_phone"],
        "topic=money": bool(t["kw_money"]), "topic=seo": bool(t["kw_seo"]), "topic=crypto": bool(t["kw_crypto"]),
    }


def matched_rules(items):
    out = []
    for rule in MINED_RULES:
        if all(items.get(item, False) for item in rule["antecedent"].split(", ")):
            out.append({"if": rule["antecedent"], "then": rule["consequent"],
                        "confidence": round(float(rule["confidence"]), 3), "lift": round(float(rule["lift"]), 2)})
    return out


@app.get("/health")
def health():
    return jsonify(status="ok", model=MODEL_VERSION, default_threshold=card["default_threshold"],
                   campaigns=len(CAMPAIGN_LABEL), mined_rules=len(MINED_RULES))


@app.post("/predict")
def predict():
    data = request.get_json(silent=True) or request.form.to_dict()
    name, email, phone = (str(data.get(k) or "") for k in ("name", "email", "phone"))
    raw = "\n".join(str(data.get(k)) for k in ("subject", "message") if data.get(k))
    text = F.mask_pii(raw, name)                      # same masking as the training data
    if not text:
        return jsonify(error="empty message"), 400

    probability = float(spam_model.predict_proba(np.array([text], dtype=object))[0, 1])
    threshold = float(data.get("threshold") or card["default_threshold"])
    campaign = campaign_of(text)
    return jsonify(
        spam_probability=round(probability, 5),
        label="spam" if probability >= threshold else "legitimate",
        threshold=threshold,
        campaign_id=campaign,
        campaign_label=CAMPAIGN_LABEL.get(campaign, "unknown"),
        top_terms=spam_terms(text),
        matched_rules=matched_rules(items_of(text, name, email, phone)),
        model_version=MODEL_VERSION,
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5055)))
