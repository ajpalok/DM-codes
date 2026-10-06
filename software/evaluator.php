<?php
/**
 * Evaluation Framework
 * Measures system effectiveness: detection rate, false positives, rule accuracy
 */

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/logger.php';

class Evaluator {
    private $db;
    private $logger;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->logger = new Logger();
    }

    /**
     * Run full evaluation and generate report
     */
    public function runEvaluation() {
        echo "=== Honeypot Security System Evaluation ===\n\n";

        $results = [
            'detection_metrics' => $this->calculateDetectionMetrics(),
            'honeypot_trigger_rate' => $this->calculateHoneypotTriggerRate(),
            'rule_effectiveness' => $this->evaluateRuleEffectiveness(),
            'false_positive_analysis' => $this->analyzeFalsePositives(),
            'performance_metrics' => $this->collectPerformanceMetrics(),
            'pattern_coverage' => $this->analyzePatternCoverage(),
        ];

        $this->printEvaluationReport($results);
        $this->saveEvaluationReport($results);

        return $results;
    }

    /**
     * Calculate detection rate and related metrics
     */
    public function calculateDetectionMetrics() {
        // Total submissions
        $total = $this->db->fetchColumn("SELECT COUNT(*) FROM submissions");

        // Honeypot triggered (likely bots)
        $honeypotTriggered = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submissions WHERE JSON_LENGTH(honeypot_hits) > 0"
        );

        // High risk submissions
        $highRisk = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submission_scores WHERE risk_level IN ('high', 'critical')"
        );

        // Manually verified true positives (from metrics table)
        $truePositives = $this->db->fetchColumn(
            "SELECT SUM(true_positive_count) FROM metrics"
        ) ?: 0;

        // Manually verified false positives
        $falsePositives = $this->db->fetchColumn(
            "SELECT SUM(false_positive_count) FROM metrics"
        ) ?: 0;

        // Calculate rates
        $detectionRate = $total > 0 ? ($honeypotTriggered / $total) * 100 : 0;
        $highRiskRate = $total > 0 ? ($highRisk / $total) * 100 : 0;
        
        $precision = ($truePositives + $falsePositives) > 0 
            ? ($truePositives / ($truePositives + $falsePositives)) * 100 
            : 0;

        $recall = ($truePositives + ($total - $honeypotTriggered)) > 0
            ? ($truePositives / ($truePositives + ($total - $honeypotTriggered))) * 100
            : 0;

        $f1Score = ($precision + $recall) > 0
            ? 2 * ($precision * $recall) / ($precision + $recall)
            : 0;

        return [
            'total_submissions' => $total,
            'honeypot_triggered' => $honeypotTriggered,
            'high_risk_count' => $highRisk,
            'true_positives' => $truePositives,
            'false_positives' => $falsePositives,
            'detection_rate' => round($detectionRate, 2),
            'high_risk_rate' => round($highRiskRate, 2),
            'precision' => round($precision, 2),
            'recall' => round($recall, 2),
            'f1_score' => round($f1Score, 2),
        ];
    }

    /**
     * Calculate honeypot trigger rates by type
     */
    public function calculateHoneypotTriggerRate() {
        $config = require __DIR__ . '/config.php';
        $honeypots = $config['honeypot'];

        $rates = [];
        $total = $this->db->fetchColumn("SELECT COUNT(*) FROM submissions");

        foreach (['text_hidden', 'semantic', 'time_trap'] as $type) {
            $fieldName = $honeypots[$type];
            
            $triggered = $this->db->fetchColumn(
                "SELECT COUNT(*) FROM submissions 
                 WHERE JSON_SEARCH(honeypot_hits, 'one', ?) IS NOT NULL 
                 OR JSON_SEARCH(honeypot_hits, 'one', ?) IS NOT NULL",
                [$fieldName, $fieldName . '_missing']
            );

            $rate = $total > 0 ? ($triggered / $total) * 100 : 0;

            $rates[$type] = [
                'field_name' => $fieldName,
                'triggered_count' => $triggered,
                'trigger_rate' => round($rate, 2),
            ];
        }

        return $rates;
    }

    /**
     * Evaluate effectiveness of each rule
     */
    public function evaluateRuleEffectiveness() {
        $rules = $this->db->fetchAll("SELECT * FROM rules WHERE enabled = 1");
        $effectiveness = [];

        foreach ($rules as $rule) {
            // Count how many times this rule was triggered
            $triggerCount = $this->db->fetchColumn(
                "SELECT COUNT(*) FROM submission_scores 
                 WHERE JSON_SEARCH(rules_triggered, 'one', ?) IS NOT NULL",
                [$rule['id']]
            );

            // Count submissions where ONLY this rule triggered (isolate effectiveness)
            $isolatedTriggers = $this->db->fetchColumn(
                "SELECT COUNT(*) FROM submission_scores 
                 WHERE JSON_LENGTH(rules_triggered) = 1 
                 AND JSON_SEARCH(rules_triggered, 'one', ?) IS NOT NULL",
                [$rule['id']]
            );

            $effectiveness[] = [
                'rule_id' => $rule['id'],
                'rule_name' => $rule['name'],
                'severity' => $rule['severity'],
                'weight' => $rule['weight'],
                'trigger_count' => $triggerCount,
                'isolated_triggers' => $isolatedTriggers,
                'effectiveness_score' => $triggerCount > 0 ? round(($isolatedTriggers / $triggerCount) * 100, 2) : 0,
            ];
        }

        // Sort by trigger count descending
        usort($effectiveness, fn($a, $b) => $b['trigger_count'] - $a['trigger_count']);

        return $effectiveness;
    }

    /**
     * Analyze false positives
     */
    public function analyzeFalsePositives() {
        // Get submissions marked as false positives (manually verified)
        // In production, you'd have a manual review interface to mark these
        
        $falsePositiveRate = $this->db->fetchColumn(
            "SELECT 
                CASE 
                    WHEN SUM(true_positive_count + false_positive_count) > 0 
                    THEN (SUM(false_positive_count) / SUM(true_positive_count + false_positive_count)) * 100
                    ELSE 0 
                END as fp_rate
             FROM metrics"
        ) ?: 0;

        return [
            'false_positive_rate' => round($falsePositiveRate, 2),
            'note' => 'Manual verification required. Use dashboard to mark submissions as TP/FP.',
        ];
    }

    /**
     * Collect performance metrics
     */
    public function collectPerformanceMetrics() {
        // Average submission processing time (estimate from events)
        $extractionEvents = $this->db->fetchAll(
            "SELECT event_data FROM events 
             WHERE event_type = 'extraction_run' 
             ORDER BY created_at DESC 
             LIMIT 10"
        );

        $avgDuration = 0;
        if (!empty($extractionEvents)) {
            $durations = array_map(function($event) {
                $data = json_decode($event['event_data'], true);
                return $data['duration_seconds'] ?? 0;
            }, $extractionEvents);
            $avgDuration = array_sum($durations) / count($durations);
        }

        // Database size
        $dbSize = $this->db->fetchOne(
            "SELECT 
                table_name,
                ROUND(((data_length + index_length) / 1024 / 1024), 2) AS size_mb
             FROM information_schema.TABLES 
             WHERE table_schema = DATABASE()"
        );

        return [
            'avg_extraction_duration_seconds' => round($avgDuration, 2),
            'database_size_mb' => $dbSize ? $dbSize['size_mb'] : 'N/A',
            'total_signatures' => $this->db->fetchColumn("SELECT COUNT(*) FROM signatures"),
            'total_clusters' => $this->db->fetchColumn("SELECT COUNT(*) FROM clusters"),
        ];
    }

    /**
     * Analyze pattern coverage
     */
    public function analyzePatternCoverage() {
        // How many submissions match known signatures vs unknown
        $totalSubmissions = $this->db->fetchColumn("SELECT COUNT(*) FROM submissions");
        
        // Estimate by checking signature occurrence
        $knownPatterns = $this->db->fetchColumn(
            "SELECT SUM(occurrence) FROM signatures WHERE occurrence >= 3"
        ) ?: 0;

        $coverage = $totalSubmissions > 0 ? ($knownPatterns / $totalSubmissions) * 100 : 0;

        return [
            'total_submissions' => $totalSubmissions,
            'known_pattern_submissions' => $knownPatterns,
            'pattern_coverage' => round($coverage, 2),
            'unique_signatures' => $this->db->fetchColumn("SELECT COUNT(*) FROM signatures"),
        ];
    }

    /**
     * Print evaluation report to console
     */
    private function printEvaluationReport($results) {
        echo "--- Detection Metrics ---\n";
        foreach ($results['detection_metrics'] as $key => $value) {
            echo sprintf("%-30s: %s\n", ucwords(str_replace('_', ' ', $key)), $value);
        }

        echo "\n--- Honeypot Trigger Rates ---\n";
        foreach ($results['honeypot_trigger_rate'] as $type => $data) {
            echo sprintf("%-20s: %d triggers (%.2f%%)\n", 
                $type, $data['triggered_count'], $data['trigger_rate']);
        }

        echo "\n--- Top 10 Rule Effectiveness ---\n";
        foreach (array_slice($results['rule_effectiveness'], 0, 10) as $rule) {
            echo sprintf("%-40s: %d triggers (%.2f%% isolated)\n",
                $rule['rule_name'], $rule['trigger_count'], $rule['effectiveness_score']);
        }

        echo "\n--- False Positive Analysis ---\n";
        foreach ($results['false_positive_analysis'] as $key => $value) {
            echo sprintf("%-30s: %s\n", ucwords(str_replace('_', ' ', $key)), $value);
        }

        echo "\n--- Performance Metrics ---\n";
        foreach ($results['performance_metrics'] as $key => $value) {
            echo sprintf("%-35s: %s\n", ucwords(str_replace('_', ' ', $key)), $value);
        }

        echo "\n--- Pattern Coverage ---\n";
        foreach ($results['pattern_coverage'] as $key => $value) {
            echo sprintf("%-30s: %s\n", ucwords(str_replace('_', ' ', $key)), $value);
        }

        echo "\n=== Evaluation Complete ===\n";
    }

    /**
     * Save evaluation report to file
     */
    private function saveEvaluationReport($results) {
        $filename = __DIR__ . '/logs/evaluation_' . date('Y-m-d_H-i-s') . '.json';
        
        if (!is_dir(__DIR__ . '/logs')) {
            mkdir(__DIR__ . '/logs', 0755, true);
        }

        file_put_contents($filename, json_encode($results, JSON_PRETTY_PRINT));
        echo "\nReport saved to: $filename\n";
    }

    /**
     * Mark submission as true/false positive (for manual verification)
     */
    public function markSubmission($submissionId, $isTruePositive) {
        $submission = $this->db->fetchOne(
            "SELECT DATE(created_at) as date FROM submissions WHERE id = ?",
            [$submissionId]
        );

        if (!$submission) {
            return false;
        }

        $date = $submission['date'];
        $field = $isTruePositive ? 'true_positive_count' : 'false_positive_count';

        // Update metrics
        $this->db->query(
            "INSERT INTO metrics (metric_date, $field) 
             VALUES (?, 1) 
             ON DUPLICATE KEY UPDATE $field = $field + 1",
            [$date]
        );

        return true;
    }
}
