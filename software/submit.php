<?php
/**
 * Form submission endpoint
 * Validates, logs, and scores submissions
 */

header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/logger.php';
require_once __DIR__ . '/scorer.php';

// Load config
$config = require __DIR__ . '/config.php';

// CORS handling (restrict in production)
$allowedOrigins = $config['security']['allowed_origins'];
if (in_array('*', $allowedOrigins) || in_array($_SERVER['HTTP_ORIGIN'] ?? '', $allowedOrigins)) {
    header('Access-Control-Allow-Origin: ' . ($_SERVER['HTTP_ORIGIN'] ?? '*'));
    header('Access-Control-Allow-Methods: POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
}

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit;
}

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

try {
    // Validate request size
    $rawInput = file_get_contents('php://input');
    if (strlen($rawInput) > $config['security']['max_payload_size']) {
        throw new Exception('Payload too large');
    }

    // Get form data
    $formData = $_POST;

    // Validate required fields
    $requiredFields = ['name', 'email', 'subject', 'message'];
    foreach ($requiredFields as $field) {
        if (empty($formData[$field])) {
            throw new Exception("Missing required field: $field");
        }
    }

    // Sanitize inputs for display (not for storage - we store raw)
    $sanitized = [];
    foreach ($formData as $key => $value) {
        $sanitized[$key] = is_string($value) ? trim($value) : $value;
    }

    // Check rate limiting
    if ($config['rate_limit']['enabled']) {
        $logger = new Logger();
        $ip = getClientIp();
        $windowMinutes = (int) $config['rate_limit']['window_minutes'];
        $maxSubmissions = (int) $config['rate_limit']['max_submissions'];

        // Skip rate limiting for localhost / development IPs
        if (!in_array($ip, ['127.0.0.1', '::1', '0.0.0.0'])) {
            // Compute cutoff time in PHP to avoid binding issues with INTERVAL ?
            $cutoff = date('Y-m-d H:i:s', strtotime("-{$windowMinutes} minutes"));

            $recentCount = (int) Database::getInstance()->fetchColumn(
                "SELECT COUNT(*) FROM submissions WHERE ip = ? AND created_at > ?",
                [$ip, $cutoff]
            );

            if ($recentCount >= $maxSubmissions) {
                http_response_code(429);
                echo json_encode([
                    'success' => false,
                    'message' => 'Rate limit exceeded. Please try again later.'
                ]);
                exit;
            }
        }
    }

    // Log the submission
    $logger = new Logger();
    $submissionId = $logger->logSubmission($formData);

    // Score the submission
    $scorer = new Scorer();
    $score = $scorer->scoreSubmission($submissionId);

    // Determine if submission should be accepted
    $riskThresholds = $config['risk_thresholds'];
    $blockThreshold = $riskThresholds['critical'];
    
    if ($score['score'] >= $blockThreshold) {
        // Block high-risk submissions
        http_response_code(403);
        echo json_encode([
            'success' => false,
            'message' => 'Submission blocked due to security concerns.',
            'submission_id' => $submissionId
        ]);
    } else {
        // Accept submission
        http_response_code(200);
        echo json_encode([
            'success' => true,
            'message' => 'Thank you for your message. We will respond soon.',
            'submission_id' => $submissionId
        ]);
    }

} catch (Exception $e) {
    error_log("Submission error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'message' => 'An error occurred. Please try again.'
    ]);
}

/**
 * Get client IP helper
 */
function getClientIp() {
    $headers = [
        'HTTP_CF_CONNECTING_IP',
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP',
        'REMOTE_ADDR'
    ];

    foreach ($headers as $header) {
        if (!empty($_SERVER[$header])) {
            $ip = $_SERVER[$header];
            if (strpos($ip, ',') !== false) {
                $ips = explode(',', $ip);
                $ip = trim($ips[0]);
            }
            if (filter_var($ip, FILTER_VALIDATE_IP)) {
                return $ip;
            }
        }
    }

    return '0.0.0.0';
}
