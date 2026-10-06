<?php
/**
 * Client for the text-mining scoring service (ml_service/app.py).
 * Returns null when the service is disabled or unreachable, so callers fall back to rule scoring alone.
 */

class MlClient {
    private $config;

    public function __construct() {
        $all = require __DIR__ . '/config.php';
        $this->config = $all['ml'] ?? ['enabled' => false];
    }

    /**
     * Score one submission.
     * @param array $fields name, email, phone, subject, message
     * @return array|null decoded service response, or null on any failure
     */
    public function predict($fields) {
        if (empty($this->config['enabled'])) {
            return null;
        }

        $timeout = (int) ($this->config['timeout_ms'] ?? 800);
        $ch = curl_init($this->config['url']);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($fields, JSON_INVALID_UTF8_SUBSTITUTE),
            CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT_MS => $timeout,
            CURLOPT_TIMEOUT_MS => $timeout,
        ]);
        $body = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);

        if ($body === false || $status !== 200) {
            error_log("ML service unavailable (HTTP $status): $error");
            return null;
        }

        $data = json_decode($body, true);
        return isset($data['spam_probability']) ? $data : null;
    }
}
