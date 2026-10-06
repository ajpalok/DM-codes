<?php
/**
 * Configuration file for Honeypot Security System
 */

return [
    // Database configuration
    'db' => [
        'host' => 'localhost',
        'port' => 3306,
        'database' => getenv('FORMTRAP_DB') ?: 'form_trap_dm',
        'username' => 'root',
        'password' => '',
        'charset' => 'utf8mb4',
        'options' => [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]
    ],

    // Honeypot field configuration
    'honeypot' => [
        // Hidden text field (CSS-invisible)
        'text_hidden' => 'website_url',
        
        // Semantic trap (looks required but isn't)
        'semantic' => 'company_code',
        
        // Time-based trap (populated by JS after delay)
        'time_trap' => 'security_token',
        
        // Minimum time in milliseconds before legitimate submission
        'min_submit_time_ms' => 2000,
        
        // Maximum time before suspicious (10 minutes)
        'max_submit_time_ms' => 600000,
    ],

    // Real form fields (expected fields)
    'expected_fields' => [
        'name',
        'email',
        'subject',
        'message',
        'form_render_time', // JS-populated timestamp
    ],

    // Risk scoring thresholds
    'risk_thresholds' => [
        'low' => 0,
        'medium' => 30,
        'high' => 60,
        'critical' => 100,
    ],

    // Pattern extraction settings
    'extraction' => [
        // Minimum occurrences to consider as a signature
        'min_occurrence' => 3,
        
        // Token size for n-gram extraction
        'ngram_size' => 3,
        
        // Similarity threshold for clustering (0-1)
        'cluster_similarity' => 0.75,
    ],

    // Rate limiting
    'rate_limit' => [
        'enabled' => true,
        'window_minutes' => 10,
        'max_submissions' => 5,
    ],

    // Logging
    'logging' => [
        'log_all_headers' => true,
        'log_path' => __DIR__ . '/logs/',
    ],

    // Security
    'security' => [
        'allowed_origins' => ['*'], // Set specific domains in production
        'max_payload_size' => 10240, // 10KB
    ],

    // Text-mining scoring service (ml_service/app.py). If it is unreachable, rule scoring continues alone.
    'ml' => [
        'enabled' => true,
        'url' => 'http://127.0.0.1:5055/predict',
        'timeout_ms' => 800,
    ],

    // Dashboard
    'dashboard' => [
        'items_per_page' => 50,
        'chart_days' => 30,
    ],
];
