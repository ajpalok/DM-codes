-- Data-mining integration: predictions of the text model and the rule that uses them.
-- Run after schema.sql:  mysql -u root < migrations/002_ml.sql

USE form_trap_dm;

CREATE TABLE IF NOT EXISTS ml_predictions (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    submission_id BIGINT UNSIGNED NOT NULL,
    spam_probability DECIMAL(6,5) NOT NULL,
    label ENUM('spam', 'legitimate') NOT NULL,
    campaign_id INT NULL COMMENT 'K-means campaign; -1 = no shared vocabulary',
    campaign_label VARCHAR(120) NULL,
    top_terms JSON NULL COMMENT 'Words that pushed the score toward spam',
    matched_rules JSON NULL COMMENT 'Mined association rules whose conditions hold',
    model_version VARCHAR(80) NOT NULL,
    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id) ON DELETE CASCADE,
    UNIQUE KEY unique_prediction (submission_id),
    INDEX idx_label (label),
    INDEX idx_campaign (campaign_id)
) ENGINE=InnoDB;

-- Weight 60 puts a submission at "high" risk on the model's word alone; it takes a second signal to reach the
-- blocking threshold (100). The model was trained without real legitimate contact-form traffic, so it flags
-- for review and does not block by itself.
INSERT INTO rules (name, description, severity, weight, condition_type, condition_params)
VALUES ('ml_spam_score', 'Spam probability from the mined text model is at or above the threshold',
        'high', 60, 'ml_score', '{"threshold": 0.5}')
ON DUPLICATE KEY UPDATE description = VALUES(description);
