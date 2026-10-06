#!/usr/bin/env php
<?php
/**
 * CLI tool for running evaluation
 * Usage: php evaluate.php
 */

require_once __DIR__ . '/evaluator.php';

echo "\nHoneypot Security System - Evaluation Tool\n";
echo "==========================================\n\n";

try {
    $evaluator = new Evaluator();
    $results = $evaluator->runEvaluation();
    
    echo "\n✓ Evaluation completed successfully\n";
    exit(0);
} catch (Exception $e) {
    echo "\n✗ Evaluation failed: " . $e->getMessage() . "\n";
    exit(1);
}
