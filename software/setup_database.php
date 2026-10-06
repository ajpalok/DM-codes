<?php
/**
 * Create the database, the tables and the scoring rules if they are missing. Safe to run every time.
 *
 * Usage: php setup_database.php
 * Prints progress, then one JSON line: {"created": bool, "submissions": N, "rules": N}
 * Exit code 2 means the MySQL server could not be reached.
 */

$config = require __DIR__ . '/config.php';
$db = $config['db'];
$name = $db['database'];
if (!preg_match('/^[A-Za-z0-9_]+$/', $name)) {
    fwrite(STDERR, "Invalid database name in config.php: $name\n");
    exit(1);
}

try {
    $pdo = new PDO(
        sprintf('mysql:host=%s;port=%d;charset=%s', $db['host'], $db['port'], $db['charset']),
        $db['username'],
        $db['password'],
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
} catch (PDOException $e) {
    fwrite(STDERR, "Cannot reach MySQL at {$db['host']}:{$db['port']} as '{$db['username']}': " . $e->getMessage() . "\n");
    fwrite(STDERR, "Start the MySQL service (for example: net start MySQL) and check the credentials in config.php.\n");
    exit(2);
}

/**
 * Split a .sql file into statements. Statements end with ";" at the end of a line; full-line comments are
 * dropped. CREATE DATABASE and USE are skipped because the database name comes from config.php.
 */
function statements($path) {
    $lines = array_filter(
        preg_split('/\R/', file_get_contents($path)),
        fn($line) => !preg_match('/^\s*--/', $line)
    );
    $out = [];
    foreach (preg_split('/;\s*$/m', implode("\n", $lines)) as $statement) {
        $statement = trim($statement);
        if ($statement !== '' && !preg_match('/^(CREATE\s+DATABASE|USE)\b/i', $statement)) {
            $out[] = $statement;
        }
    }
    return $out;
}

$pdo->exec("CREATE DATABASE IF NOT EXISTS `$name` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci");
$pdo->exec("USE `$name`");

$hasRules = (bool) $pdo->query("SHOW TABLES LIKE 'rules'")->fetch();
if (!$hasRules) {
    echo "Creating the tables and the default rules in `$name`...\n";
    foreach (statements(__DIR__ . '/schema.sql') as $statement) {
        $pdo->exec($statement);
    }
}

// The data-mining migration is written to be repeatable.
foreach (statements(__DIR__ . '/migrations/002_ml.sql') as $statement) {
    $pdo->exec($statement);
}

$submissions = (int) $pdo->query("SELECT COUNT(*) FROM submissions")->fetchColumn();
$rules = (int) $pdo->query("SELECT COUNT(*) FROM rules WHERE enabled = 1")->fetchColumn();
echo "Database `$name` is ready: $rules rules, $submissions submissions.\n";
echo json_encode(['created' => !$hasRules, 'submissions' => $submissions, 'rules' => $rules]) . "\n";
