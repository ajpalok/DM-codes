#!/usr/bin/env php
<?php
/**
 * Cron job runner for signature extraction
 * Run this script periodically (e.g., every hour via crontab)
 * 
 * Example crontab entry:
 * 0 * * * * /usr/bin/php /path/to/HoneyComp/cron/run_extractor.php >> /path/to/logs/extractor.log 2>&1
 */

// Set working directory to project root
chdir(__DIR__ . '/..');

require_once __DIR__ . '/../extractor.php';

echo "[" . date('Y-m-d H:i:s') . "] Starting extraction job\n";

try {
    $extractor = new Extractor();
    $result = $extractor->runExtraction(5000); // Process last 5000 submissions
    
    echo "[" . date('Y-m-d H:i:s') . "] Extraction completed successfully\n";
    echo "  - Signatures: {$result['signatures']}\n";
    echo "  - Clusters: {$result['clusters']}\n";
    echo "  - Duration: {$result['duration']}s\n";
    
    exit(0);
} catch (Exception $e) {
    echo "[" . date('Y-m-d H:i:s') . "] ERROR: " . $e->getMessage() . "\n";
    echo $e->getTraceAsString() . "\n";
    exit(1);
}
