-- Contact Form Honeypot & Attack Pattern Analysis System
-- Database Schema for MySQL/MariaDB

CREATE DATABASE IF NOT EXISTS form_trap_dm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE form_trap_dm;

-- Table to store form submissions
-- Raw submission storage
CREATE TABLE IF NOT EXISTS submissions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip VARCHAR(45) NOT NULL,
    user_agent TEXT,
    referer TEXT,
    request_headers JSON,
    raw_payload JSON NOT NULL,
    form_name VARCHAR(100) DEFAULT 'contact_form',
    honeypot_hits JSON COMMENT 'Array of honeypot field names that were filled',
    client_render_time INT UNSIGNED COMMENT 'Client-side milliseconds from load to submit',
    server_received_ms BIGINT UNSIGNED COMMENT 'Server timestamp in milliseconds',
    normalized_text TEXT COMMENT 'Concatenated normalized input for pattern matching',
    flags JSON COMMENT 'Detection flags: bot_likely, suspicious_timing, etc',
    INDEX idx_created (created_at),
    INDEX idx_ip (ip),
    INDEX idx_form (form_name)
) ENGINE=InnoDB;


-- Risk scores per submission
CREATE TABLE IF NOT EXISTS submission_scores (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    submission_id BIGINT UNSIGNED NOT NULL,
    score INT NOT NULL DEFAULT 0 COMMENT 'Higher = more suspicious',
    risk_level ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'low',
    rules_triggered JSON COMMENT 'Array of rule IDs that matched',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_submission (submission_id),
    INDEX idx_score (score),
    INDEX idx_risk (risk_level)
) ENGINE=InnoDB;

-- Extracted signatures (templates/patterns)
CREATE TABLE IF NOT EXISTS signatures (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    signature_hash VARCHAR(64) NOT NULL UNIQUE COMMENT 'SHA256 of normalized pattern',
    pattern TEXT NOT NULL COMMENT 'Template representation',
    occurrence INT UNSIGNED DEFAULT 1,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    sample_submission_ids JSON COMMENT 'Array of submission IDs that match this signature',
    INDEX idx_hash (signature_hash),
    INDEX idx_occurrence (occurrence DESC)
) ENGINE=InnoDB;

-- Cluster groupings of related signatures
CREATE TABLE IF NOT EXISTS clusters (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cluster_label VARCHAR(100) NOT NULL,
    signature_ids JSON NOT NULL COMMENT 'Array of signature IDs in this cluster',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_label (cluster_label)
) ENGINE=InnoDB;

-- Detection rules
CREATE TABLE IF NOT EXISTS rules (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    severity ENUM('low', 'medium', 'high', 'critical') NOT NULL DEFAULT 'medium',
    weight INT NOT NULL DEFAULT 10 COMMENT 'Score contribution when rule triggers',
    condition_type VARCHAR(50) NOT NULL COMMENT 'honeypot_filled, rapid_submit, repeated_pattern, etc',
    condition_params JSON COMMENT 'Rule-specific parameters',
    enabled TINYINT(1) DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB;

-- System events and extraction runs
CREATE TABLE IF NOT EXISTS events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL COMMENT 'extraction_run, alert, threshold_exceeded, etc',
    event_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type (event_type),
    INDEX idx_created (created_at)
) ENGINE=InnoDB;

-- Aggregated metrics for evaluation
CREATE TABLE IF NOT EXISTS metrics (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    metric_date DATE NOT NULL,
    total_submissions INT UNSIGNED DEFAULT 0,
    honeypot_triggered INT UNSIGNED DEFAULT 0,
    high_risk_count INT UNSIGNED DEFAULT 0,
    unique_signatures INT UNSIGNED DEFAULT 0,
    false_positive_count INT UNSIGNED DEFAULT 0 COMMENT 'Manually verified',
    true_positive_count INT UNSIGNED DEFAULT 0 COMMENT 'Manually verified',
    detection_rate DECIMAL(5,2) COMMENT 'Percentage',
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_date (metric_date)
) ENGINE=InnoDB;

-- Insert default rules
INSERT INTO rules (name, description, severity, weight, condition_type, condition_params) VALUES
('honeypot_text_filled', 'Hidden text field filled (invisible CSS)', 'high', 50, 'honeypot_filled', '{"field_type": "text_hidden"}'),
('honeypot_semantic_filled', 'Semantic trap field filled (fake required field)', 'high', 45, 'honeypot_filled', '{"field_type": "semantic"}'),
('honeypot_time_trap', 'Time-based trap field filled', 'medium', 30, 'honeypot_filled', '{"field_type": "time_trap"}'),
('rapid_submission', 'Form submitted in under 2 seconds', 'medium', 25, 'rapid_submit', '{"threshold_ms": 2000}'),
('suspicious_user_agent', 'User-Agent contains bot keywords', 'low', 15, 'pattern_match', '{"field": "user_agent", "patterns": ["bot", "crawler", "scraper", "curl", "wget"]}'),
('repeated_signature', 'Signature seen 10+ times', 'medium', 20, 'repeated_pattern', '{"threshold": 10}'),
('template_cluster_match', 'Matches known attack template cluster', 'high', 40, 'cluster_match', '{}'),
('abnormal_field_count', 'Unusual number of filled fields', 'low', 10, 'field_count', '{"min": 2, "max": 10}'),
('sql_injection_attempt', 'Input contains SQL injection patterns', 'critical', 100, 'pattern_match', '{"field": "any", "patterns": ["UNION SELECT", "DROP TABLE", "OR 1=1", "--", "xp_cmdshell"]}'),
('xss_attempt', 'Input contains XSS patterns', 'high', 80, 'pattern_match', '{"field": "any", "patterns": ["<script", "javascript:", "onerror=", "onload="]}'),
('email_format_invalid', 'Email field malformed or suspicious', 'low', 5, 'email_validation', '{}'),
('repetitive_character_spam', 'Input contains excessive character repetition', 'medium', 15, 'pattern_match', '{"field": "any", "patterns": ["(.)\\\\1{10,}"]}'),
('no_referrer', 'Missing HTTP referrer header', 'low', 8, 'header_check', '{"header": "referer", "present": true}'),
('ip_rate_limit', 'Same IP submitted 5+ times in 10 minutes', 'high', 35, 'rate_limit', '{"window_minutes": 10, "threshold": 5}');
