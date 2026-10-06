# FormTrap: honeypot contact form with mined spam detection

FormTrap protects a web contact form without a CAPTCHA. It combines three things:

- **Honeypot fields** that people cannot see and naive bots fill in.
- **Weighted scoring rules** (honeypot hits, timing, attack patterns, rate limits).
- **A text model mined from five years of real submissions**, which scores what a message says when the
  honeypot stays silent. The analysis behind it is in `../notebooks/FormTrap_DM.ipynb`.

The honeypot alone is not dependable: in the mined data its hit rate ranged from 98% of submissions in 2022 to
14% in the last quarter of 2023. That is why the content model was added.

## Architecture

```text
 Contact form (index.php + assets/form.js)
        |  POST
        v
 submit.php ----> Logger (logger.php, normalizer.php) ----> submissions
        |
        +-------> Scorer (scorer.php) ----------------------> submission_scores
                     |  rule "ml_spam_score"
                     v
                  ml_client.php --HTTP--> ml_service/app.py   (Python)
                     |                      spam probability, campaign,
                     v                      words behind the score, mined rules
                  ml_predictions

 cron/run_extractor.php ----> extractor.php ----> signatures, clusters, metrics

 dashboard.php   original analytics        \
 mining.php      data-mining view            >---- api_stats.php (JSON)
```

If the Python service is not running, `ml_client.php` returns nothing, the model's rule does not trigger, and
the other rules score the submission as before.

## Components

| File | Purpose |
| --- | --- |
| `index.php`, `assets/form.js` | The contact form with its honeypot fields and timing logic |
| `submit.php` | Submission endpoint: validation, rate limiting, logging, scoring, accept or block |
| `logger.php`, `normalizer.php` | Store the submission with metadata; normalize text and extract templates |
| `scorer.php` | Evaluates every enabled rule and adds up the weights |
| `ml_client.php` | Calls the scoring service with a short timeout |
| `ml_service/app.py` | Scoring service: logistic regression on TF-IDF, K-means campaign assignment, mined association rules |
| `ml_service/artifacts/` | Models and JSON exported by the notebook |
| `extractor.php`, `cron/run_extractor.php` | Signature extraction and clustering of repeated templates |
| `dashboard.php` | Live statistics, timeline, recent submissions, honeypot effectiveness |
| `mining.php` | OLAP explorer, model comparison, campaigns, mined and hand-written rules, latest scored submissions |
| `api_stats.php` | JSON endpoints for both dashboards |
| `evaluator.php`, `evaluate.php` | Evaluation report for the rule engine |
| `cron/import_dataset.php` | Loads the prepared dataset into the database and scores every row |
| `schema.sql`, `migrations/002_ml.sql` | Database schema and the data-mining migration |
| `setup_database.php` | Creates the database, tables and rules if they are missing; safe to run every time |
| `config.php`, `db.php` | Configuration and PDO wrapper |
| `test.php`, `bot_simulator.py` | Component tests and attack simulation |

## Database

Database name: `form_trap_dm` (set in `config.php`).

| Table | Purpose |
| --- | --- |
| `submissions` | Raw submissions with metadata and honeypot hits |
| `submission_scores` | Risk score, risk level and the rules that triggered |
| `ml_predictions` | Spam probability, label, campaign, top words and matched mined rules per submission |
| `rules` | The scoring rules and their weights |
| `signatures`, `clusters` | Extracted templates and their groups |
| `events`, `metrics` | System events and daily aggregates |

## Quick start

Requirements: PHP 8 with `pdo_mysql` and `curl`, MySQL 8, Python 3.10+.

**One command**, from the project root (needs Node.js): `npm run dev`. It creates the database if it is
missing, starts the scoring service and the web application, and prints the addresses. `npm run stop` stops
them. The steps it performs are:

```bash
# 1. database (or: php setup_database.php, which is safe to repeat)
mysql -u root < schema.sql
mysql -u root < migrations/002_ml.sql

# 2. scoring service (http://127.0.0.1:5055)
pip install -r ml_service/requirements.txt
python ml_service/app.py

# 3. web application, in a second terminal
php -S 127.0.0.1:8090

# 4. optional: five years of history for the dashboards (about two minutes)
php cron/import_dataset.php

# 5. check the components
php test.php
```

Open:

- `http://127.0.0.1:8090/index.php` the form
- `http://127.0.0.1:8090/dashboard.php` the original dashboard
- `http://127.0.0.1:8090/mining.php` the data-mining view

Set your MySQL user and password in `config.php` if they differ from `root` with no password.

## How a submission is scored

1. `submit.php` logs the submission and asks `Scorer` for a score.
2. Each enabled rule that matches adds its weight. The rule `ml_spam_score` sends the submission to the
   scoring service, stores the answer in `ml_predictions`, and adds 60 when the spam probability reaches the
   rule's threshold (0.5 by default).
3. Totals of 30, 60 and 100 mean medium, high and critical risk. A critical submission is blocked.

The model alone marks a submission as high risk and does not block it; blocking needs a second signal. The
model was trained without real legitimate contact-form traffic, so it flags for review.

## Scoring rules

15 rules ship with the system (`schema.sql` and `migrations/002_ml.sql`).

| Rule | Weight | Triggers when |
| --- | --- | --- |
| `sql_injection_attempt` | 100 | Input contains SQL injection patterns |
| `xss_attempt` | 80 | Input contains script injection patterns |
| `ml_spam_score` | 60 | Spam probability from the mined text model is at or above the threshold |
| `honeypot_text_filled` | 50 | The hidden text field is filled |
| `honeypot_semantic_filled` | 45 | The fake "required" field is filled |
| `template_cluster_match` | 40 | The message matches a known template cluster |
| `ip_rate_limit` | 35 | Five or more submissions from one IP in ten minutes |
| `honeypot_time_trap` | 30 | The time-trap token is missing |
| `rapid_submission` | 25 | Submitted in under two seconds |
| `repeated_signature` | 20 | The message template was seen ten or more times |
| `suspicious_user_agent` | 15 | The user agent names a bot or script |
| `repetitive_character_spam` | 15 | Long runs of one character |
| `abnormal_field_count` | 10 | Unusual number of filled fields |
| `no_referrer` | 8 | The HTTP referrer is missing |
| `email_format_invalid` | 5 | The e-mail address is malformed |

Change a weight or threshold in the `rules` table, for example:

```sql
UPDATE rules SET condition_params = '{"threshold": 0.7}' WHERE name = 'ml_spam_score';
```

## Configuration (`config.php`)

```php
'honeypot' => [
    'text_hidden' => 'website_url',      // field hidden by CSS
    'semantic' => 'company_code',        // fake required field
    'time_trap' => 'security_token',     // filled by JavaScript after a delay
    'min_submit_time_ms' => 2000,
],
'risk_thresholds' => ['low' => 0, 'medium' => 30, 'high' => 60, 'critical' => 100],
'ml' => [
    'enabled' => true,
    'url' => 'http://127.0.0.1:5055/predict',
    'timeout_ms' => 800,
],
```

## Testing

```bash
php test.php                                                        # eight component tests
python bot_simulator.py --target http://127.0.0.1:8090/submit.php   # simulated attacks

# a honeypot hit
curl -X POST http://127.0.0.1:8090/submit.php \
  -d "name=TestBot&email=bot@test.com&subject=Test&message=spam&website_url=http://spam.example"

# the scoring service by itself
curl -X POST http://127.0.0.1:5055/predict -H "Content-Type: application/json" \
  -d '{"name":"CarlosSob","message":"Make money online with our financial robot https://example.com/go"}'
```

`python excel_importer.py` is the original bulk importer. It reads the raw spreadsheet, which is kept outside
this folder because it contains personal data: pass `--excel "../data/raw/Contact Form (Responses).xlsx"`.

## Limits of the model

- Its legitimate class is public SMS, not real contact-form traffic. Re-train on the site's own legitimate
  submissions when there are enough of them.
- It knows the kinds of spam this form received; other kinds of spam are caught less often.
- It misses very short spam (a bare name, a one-line enquiry), which is also what evades the honeypot. The
  mined association rules reported with each prediction recognise those senders by their shape.
- Campaign assignment always returns the nearest campaign, so the dashboard shows it for spam only.

Details, measured numbers and re-training steps: `docs/DATA_MINING.md`.

## Production notes

- Use a dedicated database user with limited privileges, and serve the application over HTTPS.
- Set specific `allowed_origins` in `config.php` instead of `*`.
- Add a CSRF token to the form. SQL injection is prevented by prepared statements; output is escaped in the
  dashboards.
- Keep the scoring service bound to `127.0.0.1`; it has no authentication.
- Schedule `cron/run_extractor.php` hourly for signature extraction.

## Other documents

`docs/DATA_MINING.md` describes the data-mining integration. `docs/QUICKSTART.md` is the step-by-step setup
shown on the About page. The remaining files in `docs/` describe the original rule-only version of the project.

## License

MIT License. Free for educational and commercial use.
