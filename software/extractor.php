<?php
/**
 * Signature and pattern extraction engine
 * Analyzes submissions to extract templates, create signatures, and build clusters
 */

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/normalizer.php';
require_once __DIR__ . '/logger.php';

class Extractor {
    private $db;
    private $config;
    private $logger;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->config = require __DIR__ . '/config.php';
        $this->logger = new Logger();
    }

    /**
     * Run full extraction pipeline
     */
    public function runExtraction($limitSubmissions = 1000) {
        $startTime = microtime(true);
        
        echo "Starting signature extraction...\n";

        // Extract signatures from recent unprocessed submissions
        $signatureCount = $this->extractSignatures($limitSubmissions);
        echo "Extracted/updated {$signatureCount} signatures\n";

        // Build clusters from signatures
        $clusterCount = $this->buildClusters();
        echo "Built {$clusterCount} clusters\n";

        // Update metrics
        $this->updateMetrics();
        echo "Updated metrics\n";

        $duration = round(microtime(true) - $startTime, 2);
        echo "Extraction completed in {$duration}s\n";

        // Log event
        $this->logger->logEvent('extraction_run', [
            'signatures_processed' => $signatureCount,
            'clusters_built' => $clusterCount,
            'duration_seconds' => $duration
        ]);

        return [
            'signatures' => $signatureCount,
            'clusters' => $clusterCount,
            'duration' => $duration
        ];
    }

    /**
     * Extract signatures from submissions
     */
    public function extractSignatures($limit = 1000) {
        // Fetch recent submissions
        $submissions = $this->db->fetchAll(
            "SELECT id, raw_payload, normalized_text 
             FROM submissions 
             ORDER BY created_at DESC 
             LIMIT ?",
            [$limit]
        );

        $processedCount = 0;
        $this->db->beginTransaction();

        try {
            foreach ($submissions as $submission) {
                $rawPayload = json_decode($submission['raw_payload'], true);
                
                // Extract template
                $template = InputNormalizer::extractFormTemplate(
                    $rawPayload,
                    ['name', 'email', 'subject', 'message']
                );

                // Generate signature hash
                $hash = InputNormalizer::generateSignatureHash($template);

                // Check if signature exists
                $existing = $this->db->fetchOne(
                    "SELECT id, occurrence, sample_submission_ids FROM signatures WHERE signature_hash = ?",
                    [$hash]
                );

                if ($existing) {
                    // Update existing signature
                    $sampleIds = json_decode($existing['sample_submission_ids'], true) ?? [];
                    
                    // Add current submission to samples (keep max 10)
                    if (!in_array($submission['id'], $sampleIds)) {
                        $sampleIds[] = $submission['id'];
                        $sampleIds = array_slice($sampleIds, -10);
                    }

                    $this->db->update(
                        'signatures',
                        [
                            'occurrence' => $existing['occurrence'] + 1,
                            'sample_submission_ids' => json_encode($sampleIds)
                        ],
                        'id = ?',
                        [$existing['id']]
                    );
                } else {
                    // Insert new signature
                    $this->db->insert('signatures', [
                        'signature_hash' => $hash,
                        'pattern' => $template,
                        'occurrence' => 1,
                        'sample_submission_ids' => json_encode([$submission['id']])
                    ]);
                }

                $processedCount++;
            }

            $this->db->commit();
        } catch (Exception $e) {
            $this->db->rollback();
            error_log("Signature extraction failed: " . $e->getMessage());
            throw $e;
        }

        return $processedCount;
    }

    /**
     * Build clusters from similar signatures
     */
    public function buildClusters() {
        // Fetch all signatures with multiple occurrences
        $minOccurrence = $this->config['extraction']['min_occurrence'];
        
        $signatures = $this->db->fetchAll(
            "SELECT id, pattern, occurrence FROM signatures 
             WHERE occurrence >= ? 
             ORDER BY occurrence DESC",
            [$minOccurrence]
        );

        if (count($signatures) < 2) {
            return 0;
        }

        $similarityThreshold = $this->config['extraction']['cluster_similarity'];
        $clusters = [];
        $assigned = [];

        // Simple greedy clustering
        foreach ($signatures as $i => $sig1) {
            if (isset($assigned[$sig1['id']])) {
                continue;
            }

            $cluster = [$sig1['id']];
            $assigned[$sig1['id']] = true;

            // Find similar signatures
            foreach ($signatures as $j => $sig2) {
                if ($i === $j || isset($assigned[$sig2['id']])) {
                    continue;
                }

                $similarity = InputNormalizer::calculateSimilarity(
                    $sig1['pattern'],
                    $sig2['pattern']
                );

                if ($similarity >= $similarityThreshold) {
                    $cluster[] = $sig2['id'];
                    $assigned[$sig2['id']] = true;
                }
            }

            // Only create cluster if it has 2+ signatures
            if (count($cluster) >= 2) {
                $clusters[] = $cluster;
            }
        }

        // Store clusters in database
        $this->db->query("DELETE FROM clusters"); // Clear old clusters
        
        $clusterCount = 0;
        foreach ($clusters as $idx => $signatureIds) {
            $label = "cluster_" . ($idx + 1);
            $description = "Auto-generated cluster with " . count($signatureIds) . " similar signatures";

            $this->db->insert('clusters', [
                'cluster_label' => $label,
                'signature_ids' => json_encode($signatureIds),
                'description' => $description
            ]);

            $clusterCount++;
        }

        return $clusterCount;
    }

    /**
     * Update daily metrics
     */
    public function updateMetrics() {
        $today = date('Y-m-d');

        // Count today's submissions
        $totalSubmissions = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submissions WHERE DATE(created_at) = ?",
            [$today]
        );

        // Count honeypot triggered
        $honeypotTriggered = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submissions 
             WHERE DATE(created_at) = ? 
             AND JSON_LENGTH(honeypot_hits) > 0",
            [$today]
        );

        // Count high risk
        $highRiskCount = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submission_scores ss
             JOIN submissions s ON ss.submission_id = s.id
             WHERE DATE(s.created_at) = ?
             AND ss.risk_level IN ('high', 'critical')",
            [$today]
        );

        // Count unique signatures
        $uniqueSignatures = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM signatures"
        );

        // Calculate detection rate (assuming honeypot trigger = detected bot)
        $detectionRate = $totalSubmissions > 0 
            ? round(($honeypotTriggered / $totalSubmissions) * 100, 2)
            : 0;

        // Insert or update metrics
        $existing = $this->db->fetchOne(
            "SELECT id FROM metrics WHERE metric_date = ?",
            [$today]
        );

        if ($existing) {
            $this->db->update(
                'metrics',
                [
                    'total_submissions' => $totalSubmissions,
                    'honeypot_triggered' => $honeypotTriggered,
                    'high_risk_count' => $highRiskCount,
                    'unique_signatures' => $uniqueSignatures,
                    'detection_rate' => $detectionRate
                ],
                'metric_date = ?',
                [$today]
            );
        } else {
            $this->db->insert('metrics', [
                'metric_date' => $today,
                'total_submissions' => $totalSubmissions,
                'honeypot_triggered' => $honeypotTriggered,
                'high_risk_count' => $highRiskCount,
                'unique_signatures' => $uniqueSignatures,
                'detection_rate' => $detectionRate
            ]);
        }
    }

    /**
     * Analyze specific submission for debugging
     */
    public function analyzeSubmission($submissionId) {
        $submission = $this->db->fetchOne(
            "SELECT * FROM submissions WHERE id = ?",
            [$submissionId]
        );

        if (!$submission) {
            return null;
        }

        $rawPayload = json_decode($submission['raw_payload'], true);
        
        // Extract template
        $template = InputNormalizer::extractFormTemplate(
            $rawPayload,
            ['name', 'email', 'subject', 'message']
        );

        // Generate hash
        $hash = InputNormalizer::generateSignatureHash($template);

        // Find matching signature
        $signature = $this->db->fetchOne(
            "SELECT * FROM signatures WHERE signature_hash = ?",
            [$hash]
        );

        // Extract n-grams
        $ngrams = [];
        foreach (['name', 'message'] as $field) {
            if (isset($rawPayload[$field])) {
                $fieldNgrams = InputNormalizer::extractNgrams($rawPayload[$field], 3);
                $ngrams[$field] = array_slice($fieldNgrams, 0, 10);
            }
        }

        return [
            'submission_id' => $submissionId,
            'template' => $template,
            'signature_hash' => $hash,
            'signature_found' => $signature !== false,
            'signature_occurrence' => $signature['occurrence'] ?? 0,
            'ngrams' => $ngrams
        ];
    }

    /**
     * Get top attack patterns
     */
    public function getTopPatterns($limit = 10) {
        return $this->db->fetchAll(
            "SELECT id, pattern, occurrence, last_seen 
             FROM signatures 
             ORDER BY occurrence DESC 
             LIMIT ?",
            [$limit]
        );
    }

    /**
     * Get cluster details
     */
    public function getClusterDetails($clusterId) {
        $cluster = $this->db->fetchOne(
            "SELECT * FROM clusters WHERE id = ?",
            [$clusterId]
        );

        if (!$cluster) {
            return null;
        }

        $signatureIds = json_decode($cluster['signature_ids'], true);
        
        // Fetch signatures in this cluster
        $placeholders = implode(',', array_fill(0, count($signatureIds), '?'));
        $signatures = $this->db->fetchAll(
            "SELECT * FROM signatures WHERE id IN ($placeholders) ORDER BY occurrence DESC",
            $signatureIds
        );

        return [
            'cluster' => $cluster,
            'signatures' => $signatures
        ];
    }
}
