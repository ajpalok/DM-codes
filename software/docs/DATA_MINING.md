# FormTrap with data mining: how to run

FormTrap is the PHP + MySQL honeypot contact form. This version adds a text model, campaign assignment and
association rules mined from five years of submissions (see `notebooks/FormTrap_DM.ipynb`).

## What was added

| File | Purpose |
| --- | --- |
| `ml_service/app.py` | Python service. `POST /predict` returns spam probability, campaign, the words behind the score and the mined rules the submission matches |
| `ml_service/artifacts/` | Models and JSON exported by the notebook (copied here by `tools/sync_artifacts.py`) |
| `ml_client.php` | Calls the service with a short timeout; returns nothing if the service is down |
| `scorer.php` | New rule type `ml_score`: stores the prediction and adds its weight when the probability reaches the threshold |
| `migrations/002_ml.sql` | Table `ml_predictions` and the rule `ml_spam_score` (weight 60, threshold 0.5) |
| `mining.php` | Dashboard page: OLAP explorer, model comparison, campaigns, mined and hand-written rules, latest scored submissions |
| `api_stats.php` | New actions `ml_summary` and `olap` |
| `cron/import_dataset.php` | Loads the prepared dataset into MySQL and scores every row |

## Run

Requirements: PHP 8 with `pdo_mysql` and `curl`, MySQL 8, Python 3.10+.

The short way, from the project root: `npm run dev` starts everything (and `npm run stop` stops it). By hand:

```bash
# 1. database (uses its own database, form_trap_dm; set credentials in config.php)
mysql -u root < schema.sql
mysql -u root < migrations/002_ml.sql

# 2. scoring service, http://127.0.0.1:5055
pip install -r ml_service/requirements.txt
python ml_service/app.py

# 3. web application, in a second terminal
php -S 127.0.0.1:8090

# 4. optional: load five years of history for the dashboard (about two minutes)
php cron/import_dataset.php
```

Open `http://127.0.0.1:8090/index.php` for the form, `dashboard.php` for the original dashboard and
`mining.php` for the data-mining view.

## How a submission is scored

1. `submit.php` logs the submission, then `Scorer` evaluates every enabled rule.
2. The `ml_score` rule sends name, e-mail, phone, subject and message to the service. The service masks e-mail
   addresses and phone numbers exactly as the training data was masked, then returns the spam probability.
3. The prediction is stored in `ml_predictions`. If the probability is at or above the rule's threshold, the
   rule's weight (60) is added to the risk score.
4. A score of 100 or more blocks the submission. The model alone reaches "high" risk, not the blocking
   threshold: it needs a second signal. This is deliberate, see Limits.

If the service is not running, step 2 returns nothing, the rule does not trigger, and FormTrap scores with its
other rules as before.

## Settings

- Service address and timeout: `config.php`, section `ml`.
- Threshold: `UPDATE rules SET condition_params = '{"threshold": 0.7}' WHERE name = 'ml_spam_score';`
  At 0.7 the model flagged none of the 40 genuine test messages and still caught 87% of form spam in
  cross-validation; at 0.5 it flagged one of the 40 and caught 93%.
- Weight: the `weight` column of the same rule.

## Limits

- The legitimate class used for training is public SMS, not real contact-form traffic. The 40 genuine
  contact-form messages used as a check are hand-written. Re-train on the site's own legitimate submissions
  once there are enough of them.
- The model knows the kinds of spam this form received. On SMS spam it catches about a fifth at threshold 0.5.
- It misses short spam. The spam it lets through has a median length of 23 characters and rarely contains a
  link: bare names, random strings and the one-line price enquiry sent in dozens of languages. These are the
  same senders that leave the honeypot empty. The mined association rules (for example "short message and
  joined name") do recognise them, which is why every prediction lists the rules it matched.
- Campaign assignment always returns the nearest campaign; the dashboard shows it for spam only.

## Re-training

```bash
python src/prepare_dataset.py        # rebuild the prepared dataset from the raw export
python tools/make_notebook.py        # run the notebook; writes artifacts/
python tools/sync_artifacts.py       # copy models to ml_service/artifacts/ and figures to paper/figures/
```

Restart `ml_service/app.py` afterwards.
