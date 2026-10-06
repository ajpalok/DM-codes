<?php
/**
 * Load the prepared dataset into the database and score every row, so the dashboard and the OLAP view
 * have five years of history to show.
 *
 * Usage: php cron/import_dataset.php [path/to/formtrap_spam_clean.csv] [--limit=N]
 *
 * Only timestamped rows are imported (the OLAP time dimension needs a date). Names, e-mail addresses and phone
 * numbers are not in the prepared dataset, so those fields are stored empty.
 */

require_once __DIR__ . '/../db.php';
require_once __DIR__ . '/../normalizer.php';
require_once __DIR__ . '/../scorer.php';

$path = __DIR__ . '/../../data/prepared/formtrap_spam_clean.csv';
$limit = PHP_INT_MAX;
foreach (array_slice($argv, 1) as $arg) {
    if (strpos($arg, '--limit=') === 0) {
        $limit = (int) substr($arg, 8);
    } else {
        $path = $arg;
    }
}

$handle = fopen($path, 'r');
if ($handle === false) {
    fwrite(STDERR, "Cannot open $path\n");
    exit(1);
}

$config = require __DIR__ . '/../config.php';
$honeypotField = $config['honeypot']['text_hidden'];
$db = Database::getInstance();
$scorer = new Scorer();

$header = fgetcsv($handle, 0, ',', '"', '');
$col = array_flip($header);
$imported = 0;
$skipped = 0;
$start = microtime(true);

while (($row = fgetcsv($handle, 0, ',', '"', '')) !== false && $imported < $limit) {
    $timestamp = $row[$col['timestamp']];
    $message = $row[$col['message']];
    if ($timestamp === '' || $message === '') {
        $skipped++;
        continue;
    }

    $payload = ['name' => '', 'email' => '', 'subject' => '', 'message' => $message];
    $filled = $row[$col['honeypot_filled']] !== '' && (float) $row[$col['honeypot_filled']] == 1.0;
    // Inside the unrecorded window (see the notebook, Section 1.3) the honeypot outcome is unknown.
    $recorded = $row[$col['honeypot_reliable']] !== '' && (float) $row[$col['honeypot_reliable']] == 1.0;

    $submissionId = $db->insert('submissions', [
        'created_at' => $timestamp,
        'ip' => '0.0.0.0',
        'user_agent' => 'dataset-import',
        'referer' => '',
        'request_headers' => json_encode([]),
        'raw_payload' => json_encode($payload, JSON_INVALID_UTF8_SUBSTITUTE | JSON_UNESCAPED_UNICODE),
        'form_name' => 'contact_form',
        'honeypot_hits' => json_encode($filled ? [$honeypotField] : []),
        'client_render_time' => null,
        'server_received_ms' => strtotime($timestamp) * 1000,
        'normalized_text' => InputNormalizer::normalizeFormData($payload, ['message']),
        'flags' => json_encode(['imported' => true, 'honeypot_recorded' => $recorded]),
    ]);
    $scorer->scoreSubmission($submissionId);

    $imported++;
    if ($imported % 250 === 0) {
        echo "  $imported rows...\n";
    }
}
fclose($handle);

$predicted = $db->fetchColumn("SELECT COUNT(*) FROM ml_predictions");
printf("Imported %d rows (%d skipped: no timestamp or no message) in %.1fs. Rows with a model prediction: %d\n",
    $imported, $skipped, microtime(true) - $start, $predicted);
if ($predicted == 0) {
    echo "No predictions were stored: start the scoring service (python ml_service/app.py) and run again.\n";
}
