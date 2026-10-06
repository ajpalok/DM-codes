"""Text masking and feature extraction.

One definition shared by the dataset builder, the notebook and the scoring
service, so a live submission is turned into features exactly the way the
training rows were.
"""
import hashlib
import math
import re
from collections import Counter

URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"'\[\]]+", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\w.])\+?\d(?:[ \-.()]{0,2}\d){6,14}(?!\w)")
SITE_RE = re.compile(r"2haas(?:\.[a-z]{2,6})?", re.I)
MASK_RE = re.compile(r"<(?:EMAIL|PHONE|SITE|NAME)>")
REPEAT_RE = re.compile(r"(.)\1{3,}")

FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com",
             "live.com", "msn.com", "protonmail.com", "gmx.com", "ymail.com", "googlemail.com"}
RU_MAIL = {"mail.ru", "list.ru", "bk.ru", "inbox.ru", "rambler.ru", "yandex.ru", "yandex.com", "ya.ru"}

KEYWORDS = {
    "kw_money": r"money|earn|income|profit|cash|invest|loan|financial|\$\s?\d",
    "kw_crypto": r"crypto|bitcoin|\bbtc\b|ethereum|binance|wallet|\bnft\b|metamask|blockchain",
    "kw_seo": r"\bseo\b|backlink|ranking|\branks?\b|traffic|domain authority|\bmoz\b|google|web ?site|web design",
    "kw_pharma": r"viagra|cialis|pharmac|\bpills?\b|stromectol|ivermectin|prescription",
    "kw_adult": r"\bsex|dating|porn|\badult\b|escort|\bgirls\b|\bnude|xxx",
    "kw_gambling": r"casino|\bbet\b|betting|\bslots?\b|poker|gambl",
    "kw_unsub": r"unsubscribe|opt[ -]?out",
}
KEYWORD_RES = {k: re.compile(v, re.I) for k, v in KEYWORDS.items()}

TEXT_FEATURES = [
    "msg_len", "word_count", "avg_word_len", "line_count", "url_count", "email_mentions",
    "phone_mentions", "digit_ratio", "upper_ratio", "special_ratio", "non_ascii_ratio",
    "cyrillic_ratio", "char_entropy", "exclam_count", "has_bbcode", "has_html", "has_repeat",
] + list(KEYWORDS)
CONTACT_FEATURES = [
    "has_name", "name_len", "name_words", "name_has_digit", "name_joined", "name_equals_msg",
    "has_email", "email_valid", "email_local_len", "email_local_digits", "email_free", "email_ru",
    "has_phone", "phone_digits", "phone_ru_format", "phone_has_letters", "field_completion_ratio",
]


def _s(value):
    """Return a stripped string; None / NaN become ''."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def mask_pii(text, name=""):
    """Replace e-mail addresses, phone numbers, the host site and the sender's own name with tokens."""
    text = _s(text)
    name = _s(name)
    if not text:
        return ""
    if name and text.lower() == name.lower():
        return "<NAME>"
    text = EMAIL_RE.sub("<EMAIL>", text)
    text = PHONE_RE.sub("<PHONE>", text)
    text = SITE_RE.sub("<SITE>", text)
    if len(name) >= 5 and len(name.split()) >= 2:
        text = re.sub(re.escape(name), "<NAME>", text, flags=re.I)
    return text


def extract_template(text):
    """Port of Normalizer::extractTemplate (normalizer.php): keep the structure, drop the specific values."""
    t = _s(text).lower()
    t = EMAIL_RE.sub("<EMAIL>", t)
    t = re.sub(r"https?://[^\s]+", "<URL>", t)
    t = re.sub(r"\+?\d[\d\-\s()]{5,}\d", "<PHONE>", t)
    t = re.sub(r"\b\d+\b", "<NUM>", t)
    t = REPEAT_RE.sub("<REPEAT>", t)
    for tok in ("email", "phone", "site", "name"):
        t = t.replace(f"<{tok}>", f"<{tok.upper()}>")
    return re.sub(r"\s+", " ", t).strip()


def template_id(text):
    """Short stable hash of the template; '' for an empty message."""
    tpl = extract_template(text)
    return hashlib.sha1(tpl.encode("utf-8")).hexdigest()[:12] if tpl else ""


def char_entropy(text):
    """Shannon entropy of the character distribution, in bits."""
    if not text:
        return 0.0
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in Counter(text).values())


def script_of(text):
    """Dominant writing system of the message: latin, cyrillic, other or none."""
    letters = [c for c in MASK_RE.sub(" ", _s(text)) if c.isalpha()]
    if not letters:
        return "none"
    cyr = sum("Ѐ" <= c <= "ӿ" for c in letters)
    lat = sum(c.isascii() for c in letters)
    if cyr / len(letters) > 0.5:
        return "cyrillic"
    if lat / len(letters) > 0.5:
        return "latin"
    return "other"


def text_features(text):
    """Numeric features of a (masked) message. Works for an empty message too."""
    text = _s(text)
    core = MASK_RE.sub(" ", text)          # mask tokens must not count as upper-case words
    n = len(core.strip())
    words = re.findall(r"\w+", core)
    letters = [c for c in core if c.isalpha()]
    lower = core.lower()
    feats = {
        "msg_len": len(text),
        "word_count": len(words),
        "avg_word_len": sum(map(len, words)) / len(words) if words else 0.0,
        "line_count": text.count("\n") + 1 if text else 0,
        "url_count": len(URL_RE.findall(text)),
        "email_mentions": text.count("<EMAIL>"),
        "phone_mentions": text.count("<PHONE>"),
        "digit_ratio": sum(c.isdigit() for c in core) / n if n else 0.0,
        "upper_ratio": sum(c.isupper() for c in letters) / len(letters) if letters else 0.0,
        "special_ratio": sum(not c.isalnum() and not c.isspace() for c in core) / n if n else 0.0,
        "non_ascii_ratio": sum(not c.isascii() for c in core) / n if n else 0.0,
        "cyrillic_ratio": sum("Ѐ" <= c <= "ӿ" for c in letters) / len(letters) if letters else 0.0,
        "char_entropy": char_entropy(core.strip()),
        "exclam_count": core.count("!"),
        "has_bbcode": int("[url" in lower or "[/url]" in lower),
        "has_html": int(bool(re.search(r"<a\s|href=|</\w+>", lower))),
        "has_repeat": int(bool(REPEAT_RE.search(core))),
    }
    for key, rx in KEYWORD_RES.items():
        feats[key] = int(bool(rx.search(core)))
    return feats


def contact_features(name, email, phone, message=""):
    """Features of the name, e-mail and phone fields. Computed on raw values, which are never published."""
    name, email, phone, message = _s(name), _s(email), _s(phone), _s(message)
    local, _, domain = email.lower().rpartition("@")
    digits = re.sub(r"\D", "", phone)
    filled = [bool(name), bool(email), bool(phone), bool(message)]
    return {
        "has_name": int(bool(name)),
        "name_len": len(name),
        "name_words": len(name.split()),
        "name_has_digit": int(any(c.isdigit() for c in name)),
        "name_joined": int(bool(re.fullmatch(r"[A-Z][a-z]+[A-Z]\w*", name))),   # e.g. CarlosSob, AustinpetGM
        "name_equals_msg": int(bool(name) and name.lower() == message.lower()),
        "has_email": int(bool(email)),
        "email_valid": int(bool(EMAIL_RE.fullmatch(email))),
        "email_local_len": len(local),
        "email_local_digits": sum(c.isdigit() for c in local),
        "email_free": int(domain in FREE_MAIL),
        "email_ru": int(domain in RU_MAIL or domain.endswith(".ru")),
        "has_phone": int(bool(phone)),
        "phone_digits": len(digits),
        "phone_ru_format": int(len(digits) == 11 and digits[0] in "78"),
        "phone_has_letters": int(bool(re.search(r"[A-Za-z]", phone))),
        "field_completion_ratio": sum(filled) / len(filled),
    }
