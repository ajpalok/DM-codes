<?php
/**
 * Secure submission logger
 */

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/normalizer.php';

class Logger {
    private $db;
    private $config;

    public function __construct() {
        $this->db = Database::getInstance();
        $this->config = require __DIR__ . '/config.php';
    }

    /**
     * Log form submission with all metadata
     */
    public function logSubmission($formData, $metadata = []) {
        // Extract metadata
        $ip = $this->getClientIp();
        $userAgent = $_SERVER['HTTP_USER_AGENT'] ?? '';
        $referer = $_SERVER['HTTP_REFERER'] ?? '';
        
        // Collect request headers
        $headers = $this->config['logging']['log_all_headers'] 
            ? $this->getAllHeaders() 
            : [];

        // Detect honeypot hits
        $honeypotHits = $this->detectHoneypotHits($formData);
        
        // Calculate client timing
        $clientRenderTime = null;
        $serverReceivedMs = round(microtime(true) * 1000);
        
        if (isset($formData['form_render_time']) && is_numeric($formData['form_render_time'])) {
            $clientRenderTime = $serverReceivedMs - intval($formData['form_render_time']);
        }

        // Normalize form data
        $fieldsToNormalize = ['name', 'email', 'subject', 'message'];
        $normalizedText = InputNormalizer::normalizeFormData($formData, $fieldsToNormalize);

        // Generate flags
        $flags = $this->generateFlags($formData, $honeypotHits, $clientRenderTime);

        // Prepare data for insertion
        $insertData = [
            'ip' => $ip,
            'user_agent' => substr($userAgent, 0, 500),
            'referer' => substr($referer, 0, 500),
            'request_headers' => json_encode($headers),
            'raw_payload' => json_encode($formData),
            'form_name' => $metadata['form_name'] ?? 'contact_form',
            'honeypot_hits' => json_encode($honeypotHits),
            'client_render_time' => $clientRenderTime,
            'server_received_ms' => $serverReceivedMs,
            'normalized_text' => $normalizedText,
            'flags' => json_encode($flags),
        ];

        // Insert into database
        try {
            $submissionId = $this->db->insert('submissions', $insertData);
            
            // Log event
            $this->logEvent('submission_received', [
                'submission_id' => $submissionId,
                'ip' => $ip,
                'honeypot_triggered' => count($honeypotHits) > 0,
                'flags' => $flags,
            ]);

            return $submissionId;
        } catch (Exception $e) {
            error_log("Failed to log submission: " . $e->getMessage());
            throw $e;
        }
    }

    /**
     * Detect which honeypot fields were filled
     */
    private function detectHoneypotHits($formData) {
        $hits = [];
        $honeypotConfig = $this->config['honeypot'];

        // Check text hidden field
        if (!empty($formData[$honeypotConfig['text_hidden']])) {
            $hits[] = $honeypotConfig['text_hidden'];
        }

        // Check semantic trap
        if (!empty($formData[$honeypotConfig['semantic']])) {
            $hits[] = $honeypotConfig['semantic'];
        }

        // Check time trap (should be populated after delay)
        if (empty($formData[$honeypotConfig['time_trap']])) {
            $hits[] = $honeypotConfig['time_trap'] . '_missing';
        }

        return $hits;
    }

    /**
     * Generate detection flags based on initial analysis
     */
    private function generateFlags($formData, $honeypotHits, $clientRenderTime) {
        $flags = [];

        // Honeypot triggered
        if (count($honeypotHits) > 0) {
            $flags['honeypot_triggered'] = true;
        }

        // Rapid submission
        $minTime = $this->config['honeypot']['min_submit_time_ms'];
        if ($clientRenderTime !== null && $clientRenderTime < $minTime) {
            $flags['rapid_submission'] = true;
        }

        // Suspicious timing (too fast)
        if ($clientRenderTime !== null && $clientRenderTime < 500) {
            $flags['extremely_rapid'] = true;
        }

        // Bot-like user agent
        $userAgent = strtolower($_SERVER['HTTP_USER_AGENT'] ?? '');
        $botKeywords = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'python'];
        foreach ($botKeywords as $keyword) {
            if (strpos($userAgent, $keyword) !== false) {
                $flags['bot_user_agent'] = true;
                break;
            }
        }

        // Missing referer
        if (empty($_SERVER['HTTP_REFERER'])) {
            $flags['no_referer'] = true;
        }

        // Check for suspicious patterns in input
        foreach (['name', 'email', 'subject', 'message'] as $field) {
            if (isset($formData[$field])) {
                $suspiciousPatterns = InputNormalizer::detectSuspiciousPatterns($formData[$field]);
                if (!empty($suspiciousPatterns)) {
                    $flags['suspicious_pattern_' . $field] = $suspiciousPatterns;
                }
            }
        }

        // Invalid email
        if (isset($formData['email']) && !InputNormalizer::isValidEmail($formData['email'])) {
            $flags['invalid_email'] = true;
        }

        // Repetitive content
        if (isset($formData['message']) && InputNormalizer::hasRepetitivePattern($formData['message'])) {
            $flags['repetitive_content'] = true;
        }

        return $flags;
    }

    /**
     * Get real client IP (handles proxies)
     */
    private function getClientIp() {
        $headers = [
            'HTTP_CF_CONNECTING_IP', // Cloudflare
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'REMOTE_ADDR'
        ];

        foreach ($headers as $header) {
            if (!empty($_SERVER[$header])) {
                $ip = $_SERVER[$header];
                // Handle comma-separated list (X-Forwarded-For)
                if (strpos($ip, ',') !== false) {
                    $ips = explode(',', $ip);
                    $ip = trim($ips[0]);
                }
                // Validate IP
                if (filter_var($ip, FILTER_VALIDATE_IP)) {
                    return $ip;
                }
            }
        }

        return '0.0.0.0';
    }

    /**
     * Get all HTTP headers
     */
    private function getAllHeaders() {
        if (function_exists('getallheaders')) {
            return getallheaders();
        }

        // Fallback for servers without getallheaders()
        $headers = [];
        foreach ($_SERVER as $key => $value) {
            if (substr($key, 0, 5) === 'HTTP_') {
                $header = str_replace(' ', '-', ucwords(strtolower(str_replace('_', ' ', substr($key, 5)))));
                $headers[$header] = $value;
            }
        }
        return $headers;
    }

    /**
     * Log system event
     */
    public function logEvent($eventType, $eventData = []) {
        try {
            $this->db->insert('events', [
                'event_type' => $eventType,
                'event_data' => json_encode($eventData),
            ]);
        } catch (Exception $e) {
            error_log("Failed to log event: " . $e->getMessage());
        }
    }
}
