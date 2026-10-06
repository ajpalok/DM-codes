# FormTrap contact-form spam, 2020-2025

Real submissions received by one public website contact form between August 2020 and May 2025.
Every row is unsolicited (spam or bot traffic); the form received no genuine enquiries in the exported sheets.
The form carried a hidden honeypot URL field, so for part of the data we know whether the sender filled it.

## Files

| File | Rows | Content |
| --- | --- | --- |
| `formtrap_spam_clean.csv` | 5,439 | One row per submission: masked message text, template id, coarse e-mail domain, honeypot label |
| `formtrap_features.csv` | 5,439 | Engineered numeric features for the same rows (join on `id`) |
| `formtrap_spam_ham_merged.csv` | 7,639 | Spam-vs-legitimate corpus: 3,122 unique spam templates from this form + 4,517 legitimate SMS messages |
| `external_sms_spam_check.csv` | 621 | SMS spam from the same public collection as the legitimate SMS. Never used for training; it checks whether a model learned spam or only the source |
| `legit_contact_form_holdout.csv` | 40 | Hand-written legitimate contact-form style messages, used only as an out-of-domain check. **Synthetic.** |
| `prep_log.json` | - | Row count after each cleaning step and the PII scan result |

## Labels

- `honeypot_filled` (in the first two files): 1 if the hidden honeypot field was filled, 0 if left empty,
  blank if unknown. Recorded for the 2,856 timestamped rows (1,573 filled, 1,283 not filled).
  The 2,583 rows from the older export have no timestamp and no honeypot column.
- `honeypot_reliable`: 0 for the 647 submissions between 2024-03-15 and 2025-03-10, 1 for the
  other labelled rows. In that window not a single submission has the honeypot filled, for twelve months in a
  row, while the next longest such run is 98 rows in 3 days and the months
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

Text features: msg_len, word_count, avg_word_len, line_count, url_count, email_mentions, phone_mentions, digit_ratio, upper_ratio, special_ratio, non_ascii_ratio, cyrillic_ratio, char_entropy, exclam_count, has_bbcode, has_html, has_repeat, kw_money, kw_crypto, kw_seo, kw_pharma, kw_adult, kw_gambling, kw_unsub.

Contact-field features (computed on the raw fields, which are not published): has_name, name_len, name_words, name_has_digit, name_joined, name_equals_msg, has_email, email_valid, email_local_len, email_local_digits, email_free, email_ru, has_phone, phone_digits, phone_ru_format, phone_has_letters, field_completion_ratio.

Time features: year, quarter, month, weekday, hour, part_of_day, year_month.

## Anonymization

- Sender name, e-mail address and phone number columns are removed. Only features derived from them are kept.
- Only the e-mail domain is kept, and only when at least 5 rows share it; otherwise `other`.
- Inside message text, e-mail addresses become `<EMAIL>`, phone numbers and other long digit runs become `<PHONE>`,
  the receiving site's name becomes `<SITE>`, and the sender's own name becomes `<NAME>`.
- Spam URLs are kept, because they are the main object of study.
- Free text can still contain names that the sender typed and that do not match the name field.

## Sources and licence

- Spam rows: collected by the dataset authors from their own website contact form.
- Legitimate SMS rows: SMS Spam Collection, T. A. Almeida and J. M. Gomez Hidalgo, UCI Machine Learning
  Repository, https://archive.ics.uci.edu/dataset/228/sms+spam+collection, licensed CC BY 4.0.
- This dataset is released under CC BY 4.0.
