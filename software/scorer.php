<?php
/**
 * Rule-based risk scoring engine
 * Evaluates submissions against detection rules and assigns risk scores
 */

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/normalizer.php';
require_once __DIR__ . '/ml_client.php';

class Scorer {
    private $db;
    private $config;
    private $rules;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->config = require __DIR__ . '/config.php';
        $this->loadRules();
    }

    /**
     * Load active rules from database
     */
    private function loadRules() {
        $this->rules = $this->db->fetchAll(
            "SELECT * FROM rules WHERE enabled = 1 ORDER BY severity DESC, weight DESC"
        );
    }

    /**
     * Score a submission by ID
     */
    public function scoreSubmission($submissionId) {
        // Fetch submission data
        $submission = $this->db->fetchOne(
            "SELECT * FROM submissions WHERE id = ?",
            [$submissionId]
        );

        if (!$submission) {
            throw new Exception("Submission not found");
        }

        // Decode JSON fields
        $submission['raw_payload'] = json_decode($submission['raw_payload'], true);
        $submission['honeypot_hits'] = json_decode($submission['honeypot_hits'], true);
        $submission['flags'] = json_decode($submission['flags'], true);
        $submission['request_headers'] = json_decode($submission['request_headers'], true);

        // Evaluate all rules
        $score = 0;
        $triggeredRules = [];

        foreach ($this->rules as $rule) {
            if ($this->evaluateRule($rule, $submission)) {
                $score += $rule['weight'];
                $triggeredRules[] = [
                    'id' => $rule['id'],
                    'name' => $rule['name'],
                    'weight' => $rule['weight'],
                    'severity' => $rule['severity']
                ];
            }
        }

        // Determine risk level
        $riskLevel = $this->determineRiskLevel($score);

        // Store score
        $this->db->insert('submission_scores', [
            'submission_id' => $submissionId,
            'score' => $score,
            'risk_level' => $riskLevel,
            'rules_triggered' => json_encode($triggeredRules)
        ]);

        return [
            'submission_id' => $submissionId,
            'score' => $score,
            'risk_level' => $riskLevel,
            'rules_triggered' => $triggeredRules
        ];
    }

    /**
     * Evaluate a single rule against submission
     */
    private function evaluateRule($rule, $submission) {
        $conditionType = $rule['condition_type'];
        $params = json_decode($rule['condition_params'], true);

        switch ($conditionType) {
            case 'honeypot_filled':
                return $this->checkHoneypotFilled($submission, $params);
            
            case 'rapid_submit':
                return $this->checkRapidSubmit($submission, $params);
            
            case 'pattern_match':
                return $this->checkPatternMatch($submission, $params);
            
            case 'repeated_pattern':
                return $this->checkRepeatedPattern($submission, $params);
            
            case 'cluster_match':
                return $this->checkClusterMatch($submission, $params);
            
            case 'field_count':
                return $this->checkFieldCount($submission, $params);
            
            case 'email_validation':
                return $this->checkEmailValidation($submission, $params);
            
            case 'header_check':
                return $this->checkHeader($submission, $params);
            
            case 'rate_limit':
                return $this->checkRateLimit($submission, $params);

            case 'ml_score':
                return $this->checkMlScore($submission, $params);

            default:
                return false;
        }
    }

    /**
     * Check if honeypot field was filled
     */
    private function checkHoneypotFilled($submission, $params) {
        $honeypotHits = $submission['honeypot_hits'] ?? [];
        
        if (empty($honeypotHits)) {
            return false;
        }

        // Check for specific field type if specified
        if (isset($params['field_type'])) {
            $honeypotConfig = $this->config['honeypot'];
            $targetField = $honeypotConfig[$params['field_type']] ?? null;
            
            if ($targetField) {
                return in_array($targetField, $honeypotHits) || 
                       in_array($targetField . '_missing', $honeypotHits);
            }
        }

        return true;
    }

    /**
     * Check rapid submission timing
     */
    private function checkRapidSubmit($submission, $params) {
        $thresholdMs = $params['threshold_ms'] ?? 2000;
        $clientTime = $submission['client_render_time'];

        return $clientTime !== null && $clientTime < $thresholdMs;
    }

    /**
     * Check pattern matching in fields
     */
    private function checkPatternMatch($submission, $params) {
        $field = $params['field'] ?? 'any';
        $patterns = $params['patterns'] ?? [];

        $fieldsToCheck = [];
        
        if ($field === 'any') {
            $fieldsToCheck = ['name', 'email', 'subject', 'message'];
        } elseif ($field === 'user_agent') {
            $fieldsToCheck = ['user_agent'];
        } else {
            $fieldsToCheck = [$field];
        }

        foreach ($fieldsToCheck as $fieldName) {
            $value = '';
            
            if ($fieldName === 'user_agent') {
                $value = $submission['user_agent'] ?? '';
            } elseif (isset($submission['raw_payload'][$fieldName])) {
                $value = $submission['raw_payload'][$fieldName];
            }

            $value = strtolower($value);
            
            foreach ($patterns as $pattern) {
                $pattern = strtolower($pattern);
                
                // Check if pattern is regex (enclosed in delimiters)
                if (preg_match('/^\/.*\/$/', $pattern)) {
                    if (@preg_match($pattern, $value)) {
                        return true;
                    }
                } else {
                    if (strpos($value, $pattern) !== false) {
                        return true;
                    }
                }
            }
        }

        return false;
    }

    /**
     * Check if signature appears repeatedly
     */
    private function checkRepeatedPattern($submission, $params) {
        $threshold = $params['threshold'] ?? 10;
        
        // Extract template from this submission
        $template = InputNormalizer::extractFormTemplate(
            $submission['raw_payload'],
            ['name', 'email', 'subject', 'message']
        );
        
        $hash = InputNormalizer::generateSignatureHash($template);

        // Check if this signature exists and meets threshold
        $signature = $this->db->fetchOne(
            "SELECT occurrence FROM signatures WHERE signature_hash = ?",
            [$hash]
        );

        return $signature && $signature['occurrence'] >= $threshold;
    }

    /**
     * Check if submission matches known attack cluster
     */
    private function checkClusterMatch($submission, $params) {
        // Extract template
        $template = InputNormalizer::extractFormTemplate(
            $submission['raw_payload'],
            ['name', 'email', 'subject', 'message']
        );
        
        $hash = InputNormalizer::generateSignatureHash($template);

        // Find signature
        $signature = $this->db->fetchOne(
            "SELECT id FROM signatures WHERE signature_hash = ?",
            [$hash]
        );

        if (!$signature) {
            return false;
        }

        // Check if signature belongs to any cluster
        $cluster = $this->db->fetchOne(
            "SELECT id FROM clusters WHERE JSON_CONTAINS(signature_ids, ?)",
            [json_encode([$signature['id']])]
        );

        return $cluster !== false;
    }

    /**
     * Check field count anomaly
     */
    private function checkFieldCount($submission, $params) {
        $min = $params['min'] ?? 0;
        $max = $params['max'] ?? PHP_INT_MAX;
        
        $filledFields = 0;
        foreach (['name', 'email', 'subject', 'message'] as $field) {
            if (!empty($submission['raw_payload'][$field])) {
                $filledFields++;
            }
        }

        return $filledFields < $min || $filledFields > $max;
    }

    /**
     * Validate email format
     */
    private function checkEmailValidation($submission, $params) {
        $email = $submission['raw_payload']['email'] ?? '';
        return !InputNormalizer::isValidEmail($email);
    }

    /**
     * Check HTTP header presence/absence
     */
    private function checkHeader($submission, $params) {
        $headerName = $params['header'] ?? '';
        $shouldBePresent = $params['present'] ?? true;

        $headerValue = $submission[$headerName] ?? null;
        
        if ($shouldBePresent) {
            return empty($headerValue);
        } else {
            return !empty($headerValue);
        }
    }

    /**
     * Check rate limiting
     */
    private function checkRateLimit($submission, $params) {
        $windowMinutes = $params['window_minutes'] ?? 10;
        $threshold = $params['threshold'] ?? 5;
        $ip = $submission['ip'];

        $count = $this->db->fetchColumn(
            "SELECT COUNT(*) FROM submissions 
             WHERE ip = ? AND created_at > DATE_SUB(NOW(), INTERVAL ? MINUTE)",
            [$ip, $windowMinutes]
        );

        return $count >= $threshold;
    }

    /**
     * Check the spam probability from the mined text model (ml_service).
     * The prediction is stored with the submission. If the service is down the rule does not trigger.
     */
    private function checkMlScore($submission, $params) {
        $threshold = $params['threshold'] ?? 0.5;
        $payload = $submission['raw_payload'] ?? [];

        $fields = ['threshold' => $threshold];
        foreach (['name', 'email', 'phone', 'subject', 'message'] as $field) {
            $fields[$field] = $payload[$field] ?? '';
        }

        $prediction = (new MlClient())->predict($fields);
        if ($prediction === null) {
            return false;
        }

        $this->db->query(
            "INSERT INTO ml_predictions
                (submission_id, spam_probability, label, campaign_id, campaign_label, top_terms, matched_rules, model_version)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
             ON DUPLICATE KEY UPDATE spam_probability = VALUES(spam_probability), label = VALUES(label),
                campaign_id = VALUES(campaign_id), campaign_label = VALUES(campaign_label),
                top_terms = VALUES(top_terms), matched_rules = VALUES(matched_rules),
                model_version = VALUES(model_version)",
            [
                $submission['id'],
                $prediction['spam_probability'],
                $prediction['label'],
                $prediction['campaign_id'],
                $prediction['campaign_label'],
                json_encode($prediction['top_terms'] ?? [], JSON_UNESCAPED_UNICODE),
                json_encode($prediction['matched_rules'] ?? [], JSON_UNESCAPED_UNICODE),
                $prediction['model_version'],
            ]
        );

        return $prediction['spam_probability'] >= $threshold;
    }

    /**
     * Determine risk level from score
     */
    private function determineRiskLevel($score) {
        $thresholds = $this->config['risk_thresholds'];

        if ($score >= $thresholds['critical']) {
            return 'critical';
        } elseif ($score >= $thresholds['high']) {
            return 'high';
        } elseif ($score >= $thresholds['medium']) {
            return 'medium';
        } else {
            return 'low';
        }
    }

    /**
     * Batch score multiple submissions
     */
    public function batchScore($submissionIds) {
        $results = [];
        
        foreach ($submissionIds as $id) {
            try {
                $results[$id] = $this->scoreSubmission($id);
            } catch (Exception $e) {
                $results[$id] = ['error' => $e->getMessage()];
            }
        }

        return $results;
    }
}
