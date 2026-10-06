> **Note.** This document describes the original rule-only version of FormTrap. The current version adds
> a mined text model, campaign assignment and an OLAP view; see `README.md` and `docs/DATA_MINING.md`.

# FormTrap System Algorithms - Pseudocode

## 1. Preprocessing and Normalization

### 1.1 Text Normalization
```
FUNCTION NormalizeText(input_text)
    INPUT: raw text string from form field
    OUTPUT: normalized text string
    
    IF input_text is not string THEN
        RETURN empty string
    END IF
    
    // Convert to uniform case
    normalized ← CONVERT input_text TO lowercase using UTF-8 encoding
    
    // Reduce whitespace noise
    normalized ← REPLACE multiple consecutive whitespace WITH single space
    
    // Remove leading and trailing whitespace
    normalized ← TRIM whitespace from normalized
    
    RETURN normalized
END FUNCTION
```

### 1.2 Template Extraction
```
FUNCTION ExtractTemplate(input_text)
    INPUT: raw text string from form field
    OUTPUT: generalized template with value placeholders
    
    IF input_text is not string THEN
        RETURN empty string
    END IF
    
    template ← CONVERT input_text TO lowercase using UTF-8 encoding
    
    // Replace specific data types with generic tokens
    template ← REPLACE email patterns WITH "<EMAIL>" token
    template ← REPLACE URL patterns (http/https) WITH "<URL>" token
    template ← REPLACE phone number patterns WITH "<PHONE>" token
    template ← REPLACE numeric sequences WITH "<NUM>" token
    template ← REPLACE character repetitions (4+ consecutive) WITH "<REPEAT>" token
    
    // Normalize spacing
    template ← REPLACE multiple whitespace WITH single space
    template ← TRIM whitespace from template
    
    RETURN template
END FUNCTION
```

### 1.3 Form-Level Normalization
```
FUNCTION NormalizeFormData(form_data, fields_list)
    INPUT: form_data - dictionary of field names and values
           fields_list - list of field names to normalize
    OUTPUT: concatenated normalized string
    
    normalized_values ← INITIALIZE empty list
    
    FOR EACH field IN fields_list DO
        IF field EXISTS in form_data THEN
            normalized_value ← NormalizeText(form_data[field])
            APPEND normalized_value TO normalized_values
        END IF
    END FOR
    
    // Concatenate with separator for signature
    result ← JOIN normalized_values WITH delimiter " | "
    
    RETURN result
END FUNCTION
```

### 1.4 Signature Generation
```
FUNCTION GenerateSignatureHash(template_text)
    INPUT: template text (generalized pattern)
    OUTPUT: cryptographic hash string
    
    hash ← COMPUTE SHA-256 hash of template_text
    
    RETURN hash as hexadecimal string
END FUNCTION
```

---

## 2. Honeypot Signal Extraction

### 2.1 Main Extraction Pipeline
```
FUNCTION RunExtraction(submission_limit)
    INPUT: submission_limit - maximum submissions to process
    OUTPUT: extraction statistics dictionary
    
    START_TIMER()
    
    // Phase 1: Extract signatures from submissions
    signature_count ← ExtractSignatures(submission_limit)
    OUTPUT "Extracted " + signature_count + " signatures"
    
    // Phase 2: Build clusters from similar patterns
    cluster_count ← BuildClusters()
    OUTPUT "Built " + cluster_count + " clusters"
    
    // Phase 3: Update system metrics
    UpdateMetrics()
    OUTPUT "Updated metrics"
    
    duration ← GET_ELAPSED_TIME()
    
    // Log extraction event
    LOG_EVENT(type="extraction_run", 
              data={signatures: signature_count, 
                    clusters: cluster_count, 
                    duration: duration})
    
    RETURN {signatures: signature_count, 
            clusters: cluster_count, 
            duration: duration}
END FUNCTION
```

### 2.2 Signature Extraction
```
FUNCTION ExtractSignatures(limit)
    INPUT: limit - maximum number of submissions to process
    OUTPUT: count of processed signatures
    
    // Retrieve recent submissions from database
    submissions ← FETCH recent submissions FROM database LIMIT limit
    
    processed_count ← 0
    BEGIN_TRANSACTION()
    
    TRY
        FOR EACH submission IN submissions DO
            raw_payload ← DECODE JSON from submission.raw_payload
            
            // Extract generalized template from form fields
            template ← ExtractFormTemplate(raw_payload, 
                                          fields=["name", "email", "subject", "message"])
            
            // Generate unique signature identifier
            signature_hash ← GenerateSignatureHash(template)
            
            // Check if signature already exists in database
            existing_signature ← QUERY database WHERE signature_hash = signature_hash
            
            IF existing_signature EXISTS THEN
                // Update existing signature
                sample_ids ← DECODE JSON from existing_signature.sample_submission_ids
                
                // Add current submission to samples (maintain maximum 10)
                IF submission.id NOT IN sample_ids THEN
                    APPEND submission.id TO sample_ids
                    sample_ids ← KEEP last 10 elements of sample_ids
                END IF
                
                UPDATE database SET 
                    occurrence = occurrence + 1,
                    sample_submission_ids = ENCODE JSON(sample_ids)
                WHERE signature_hash = signature_hash
            ELSE
                // Create new signature entry
                INSERT INTO database.signatures
                    signature_hash ← signature_hash
                    pattern ← template
                    occurrence ← 1
                    sample_submission_ids ← ENCODE JSON([submission.id])
            END IF
            
            INCREMENT processed_count
        END FOR
        
        COMMIT_TRANSACTION()
    CATCH exception
        ROLLBACK_TRANSACTION()
        LOG_ERROR("Signature extraction failed: " + exception.message)
        THROW exception
    END TRY
    
    RETURN processed_count
END FUNCTION
```

### 2.3 Campaign Clustering
```
FUNCTION BuildClusters()
    INPUT: none (uses database signatures)
    OUTPUT: number of clusters created
    
    // Retrieve frequently occurring signatures
    min_occurrence ← GET configuration value for minimum occurrence
    signatures ← FETCH signatures FROM database 
                 WHERE occurrence >= min_occurrence
                 ORDER BY occurrence DESCENDING
    
    IF COUNT(signatures) < 2 THEN
        RETURN 0
    END IF
    
    similarity_threshold ← GET configuration value for cluster similarity
    clusters ← INITIALIZE empty list
    assigned ← INITIALIZE empty set
    
    // Greedy clustering algorithm
    FOR i FROM 0 TO LENGTH(signatures) - 1 DO
        signature_i ← signatures[i]
        
        IF signature_i.id IN assigned THEN
            CONTINUE to next iteration
        END IF
        
        cluster ← INITIALIZE list with [signature_i.id]
        ADD signature_i.id TO assigned
        
        // Find similar signatures
        FOR j FROM i + 1 TO LENGTH(signatures) - 1 DO
            signature_j ← signatures[j]
            
            IF signature_j.id IN assigned THEN
                CONTINUE to next iteration
            END IF
            
            // Calculate pattern similarity
            similarity ← CalculateSimilarity(signature_i.pattern, 
                                            signature_j.pattern)
            
            IF similarity >= similarity_threshold THEN
                APPEND signature_j.id TO cluster
                ADD signature_j.id TO assigned
            END IF
        END FOR
        
        // Create cluster only if it contains 2+ signatures
        IF LENGTH(cluster) >= 2 THEN
            APPEND cluster TO clusters
        END IF
    END FOR
    
    // Persist clusters to database
    DELETE all existing clusters FROM database
    
    cluster_count ← 0
    FOR index FROM 0 TO LENGTH(clusters) - 1 DO
        signature_ids ← clusters[index]
        label ← "cluster_" + (index + 1)
        description ← "Auto-generated cluster with " + LENGTH(signature_ids) + " signatures"
        
        INSERT INTO database.clusters
            cluster_label ← label
            signature_ids ← ENCODE JSON(signature_ids)
            description ← description
        
        INCREMENT cluster_count
    END FOR
    
    RETURN cluster_count
END FUNCTION
```

### 2.4 Pattern Similarity Calculation
```
FUNCTION CalculateSimilarity(pattern_1, pattern_2)
    INPUT: pattern_1, pattern_2 - template strings
    OUTPUT: similarity score (0.0 to 1.0)
    
    // Use string similarity metrics (e.g., Levenshtein, Jaccard, etc.)
    // This represents a placeholder for various similarity algorithms
    
    tokens_1 ← TOKENIZE pattern_1 BY delimiter " | "
    tokens_2 ← TOKENIZE pattern_2 BY delimiter " | "
    
    common_tokens ← INTERSECTION of tokens_1 and tokens_2
    total_tokens ← UNION of tokens_1 and tokens_2
    
    IF total_tokens is empty THEN
        RETURN 0.0
    END IF
    
    similarity ← COUNT(common_tokens) / COUNT(total_tokens)
    
    RETURN similarity
END FUNCTION
```

---

## 3. Rule-based Detection and Scoring

### 3.1 Main Scoring Function
```
FUNCTION ScoreSubmission(submission_id)
    INPUT: submission_id - unique identifier of submission
    OUTPUT: scoring results dictionary
    
    // Retrieve submission data from database
    submission ← FETCH submission FROM database WHERE id = submission_id
    
    IF submission NOT EXISTS THEN
        THROW exception "Submission not found"
    END IF
    
    // Decode JSON fields
    submission.raw_payload ← DECODE JSON from submission.raw_payload
    submission.honeypot_hits ← DECODE JSON from submission.honeypot_hits
    submission.flags ← DECODE JSON from submission.flags
    submission.request_headers ← DECODE JSON from submission.request_headers
    
    // Load active detection rules
    rules ← FETCH active rules FROM database ORDER BY severity, weight DESCENDING
    
    // Initialize scoring variables
    total_score ← 0
    triggered_rules ← INITIALIZE empty list
    
    // Evaluate each rule against submission
    FOR EACH rule IN rules DO
        rule_triggered ← EvaluateRule(rule, submission)
        
        IF rule_triggered = TRUE THEN
            total_score ← total_score + rule.weight
            APPEND {id: rule.id, 
                    name: rule.name, 
                    weight: rule.weight, 
                    severity: rule.severity} TO triggered_rules
        END IF
    END FOR
    
    // Determine risk classification
    risk_level ← DetermineRiskLevel(total_score)
    
    // Store scoring results
    INSERT INTO database.submission_scores
        submission_id ← submission_id
        score ← total_score
        risk_level ← risk_level
        rules_triggered ← ENCODE JSON(triggered_rules)
    
    RETURN {submission_id: submission_id,
            score: total_score,
            risk_level: risk_level,
            rules_triggered: triggered_rules}
END FUNCTION
```

### 3.2 Rule Evaluation Dispatcher
```
FUNCTION EvaluateRule(rule, submission)
    INPUT: rule - rule configuration object
           submission - submission data object
    OUTPUT: boolean (TRUE if rule triggered)
    
    condition_type ← rule.condition_type
    parameters ← DECODE JSON from rule.condition_params
    
    SWITCH condition_type DO
        CASE "honeypot_filled":
            RETURN CheckHoneypotFilled(submission, parameters)
        
        CASE "rapid_submit":
            RETURN CheckRapidSubmit(submission, parameters)
        
        CASE "pattern_match":
            RETURN CheckPatternMatch(submission, parameters)
        
        CASE "repeated_pattern":
            RETURN CheckRepeatedPattern(submission, parameters)
        
        CASE "cluster_match":
            RETURN CheckClusterMatch(submission, parameters)
        
        CASE "field_count":
            RETURN CheckFieldCount(submission, parameters)
        
        CASE "email_validation":
            RETURN CheckEmailValidation(submission, parameters)
        
        CASE "header_check":
            RETURN CheckHeader(submission, parameters)
        
        CASE "rate_limit":
            RETURN CheckRateLimit(submission, parameters)
        
        DEFAULT:
            RETURN FALSE
    END SWITCH
END FUNCTION
```

### 3.3 Individual Rule Checks

#### Honeypot Field Detection
```
FUNCTION CheckHoneypotFilled(submission, parameters)
    INPUT: submission - submission data
           parameters - rule parameters
    OUTPUT: boolean
    
    honeypot_hits ← submission.honeypot_hits OR empty list
    
    IF honeypot_hits is empty THEN
        RETURN FALSE
    END IF
    
    // Check for specific honeypot field type if specified
    IF parameters contains "field_type" THEN
        honeypot_config ← GET system honeypot configuration
        target_field ← honeypot_config[parameters.field_type]
        
        IF target_field EXISTS THEN
            RETURN (target_field IN honeypot_hits) OR 
                   (target_field + "_missing" IN honeypot_hits)
        END IF
    END IF
    
    // Any honeypot field was triggered
    RETURN TRUE
END FUNCTION
```

#### Rapid Submission Detection
```
FUNCTION CheckRapidSubmit(submission, parameters)
    INPUT: submission - submission data
           parameters - rule parameters with threshold
    OUTPUT: boolean
    
    threshold_ms ← parameters.threshold_ms OR 2000
    client_time ← submission.client_render_time
    
    // Check if submission was too fast (bot-like behavior)
    RETURN (client_time IS NOT NULL) AND (client_time < threshold_ms)
END FUNCTION
```

#### Pattern Matching Detection
```
FUNCTION CheckPatternMatch(submission, parameters)
    INPUT: submission - submission data
           parameters - rule parameters with patterns
    OUTPUT: boolean
    
    target_field ← parameters.field OR "any"
    patterns ← parameters.patterns OR empty list
    
    // Determine which fields to check
    IF target_field = "any" THEN
        fields_to_check ← ["name", "email", "subject", "message"]
    ELSE IF target_field = "user_agent" THEN
        fields_to_check ← ["user_agent"]
    ELSE
        fields_to_check ← [target_field]
    END IF
    
    // Check each field against patterns
    FOR EACH field_name IN fields_to_check DO
        IF field_name = "user_agent" THEN
            value ← submission.user_agent OR ""
        ELSE IF field_name EXISTS IN submission.raw_payload THEN
            value ← submission.raw_payload[field_name]
        ELSE
            value ← ""
        END IF
        
        value ← CONVERT value TO lowercase
        
        FOR EACH pattern IN patterns DO
            pattern ← CONVERT pattern TO lowercase
            
            // Check if pattern is regular expression
            IF pattern starts with "/" AND ends with "/" THEN
                IF value MATCHES regex pattern THEN
                    RETURN TRUE
                END IF
            ELSE
                // Simple substring matching
                IF value CONTAINS pattern THEN
                    RETURN TRUE
                END IF
            END IF
        END FOR
    END FOR
    
    RETURN FALSE
END FUNCTION
```

#### Cluster Matching Detection
```
FUNCTION CheckClusterMatch(submission, parameters)
    INPUT: submission - submission data
           parameters - cluster identifiers
    OUTPUT: boolean
    
    // Extract template from submission
    template ← ExtractFormTemplate(submission.raw_payload, 
                                   fields=["name", "email", "subject", "message"])
    signature_hash ← GenerateSignatureHash(template)
    
    // Find signature in database
    signature ← QUERY database.signatures WHERE signature_hash = signature_hash
    
    IF signature NOT EXISTS THEN
        RETURN FALSE
    END IF
    
    // Check if signature belongs to known malicious cluster
    clusters ← FETCH clusters FROM database WHERE signature.id IN signature_ids
    
    IF parameters contains "cluster_ids" THEN
        target_clusters ← parameters.cluster_ids
        FOR EACH cluster IN clusters DO
            IF cluster.id IN target_clusters THEN
                RETURN TRUE
            END IF
        END FOR
    ELSE
        // Any cluster membership indicates campaign
        RETURN clusters is not empty
    END IF
    
    RETURN FALSE
END FUNCTION
```

### 3.4 Risk Level Classification
```
FUNCTION DetermineRiskLevel(score)
    INPUT: score - numerical risk score
    OUTPUT: risk level classification string
    
    // Threshold-based classification
    IF score >= 80 THEN
        RETURN "critical"
    ELSE IF score >= 60 THEN
        RETURN "high"
    ELSE IF score >= 40 THEN
        RETURN "medium"
    ELSE IF score >= 20 THEN
        RETURN "low"
    ELSE
        RETURN "minimal"
    END IF
END FUNCTION
```

---

## 4. Campaign Identification

### 4.1 Campaign Detection Through Clustering
```
FUNCTION IdentifyCampaigns(time_window)
    INPUT: time_window - time period for analysis (e.g., days)
    OUTPUT: list of identified campaigns
    
    // Retrieve recent submissions within time window
    start_date ← CURRENT_DATE - time_window
    submissions ← FETCH submissions FROM database 
                  WHERE created_at >= start_date
    
    // Extract signatures for all submissions
    signature_map ← INITIALIZE empty dictionary
    
    FOR EACH submission IN submissions DO
        template ← ExtractFormTemplate(submission.raw_payload,
                                      fields=["name", "email", "subject", "message"])
        signature_hash ← GenerateSignatureHash(template)
        
        IF signature_hash NOT IN signature_map THEN
            signature_map[signature_hash] ← INITIALIZE empty list
        END IF
        
        APPEND submission TO signature_map[signature_hash]
    END FOR
    
    // Build clusters representing campaigns
    clusters ← BuildClusters()
    
    // Analyze each cluster as potential campaign
    campaigns ← INITIALIZE empty list
    
    FOR EACH cluster IN clusters DO
        signatures ← FETCH signatures WHERE id IN cluster.signature_ids
        
        campaign_submissions ← INITIALIZE empty list
        total_occurrence ← 0
        
        FOR EACH signature IN signatures DO
            total_occurrence ← total_occurrence + signature.occurrence
            related_submissions ← FETCH submissions 
                                  WHERE id IN signature.sample_submission_ids
            APPEND related_submissions TO campaign_submissions
        END FOR
        
        // Calculate campaign metrics
        campaign_metrics ← AnalyzeCampaignMetrics(campaign_submissions)
        
        campaign ← {
            cluster_id: cluster.id,
            cluster_label: cluster.cluster_label,
            total_submissions: total_occurrence,
            unique_patterns: COUNT(signatures),
            time_span: campaign_metrics.time_span,
            submission_rate: campaign_metrics.submission_rate,
            ip_diversity: campaign_metrics.ip_diversity,
            user_agent_diversity: campaign_metrics.user_agent_diversity
        }
        
        APPEND campaign TO campaigns
    END FOR
    
    RETURN campaigns
END FUNCTION
```

### 4.2 Campaign Metrics Analysis
```
FUNCTION AnalyzeCampaignMetrics(submissions)
    INPUT: submissions - list of submissions in campaign
    OUTPUT: campaign metrics dictionary
    
    IF submissions is empty THEN
        RETURN empty metrics
    END IF
    
    // Temporal analysis
    timestamps ← EXTRACT created_at FROM submissions
    earliest ← MIN(timestamps)
    latest ← MAX(timestamps)
    time_span ← latest - earliest
    submission_rate ← COUNT(submissions) / time_span (in hours)
    
    // Source diversity analysis
    ip_addresses ← EXTRACT UNIQUE ip_address FROM submissions
    user_agents ← EXTRACT UNIQUE user_agent FROM submissions
    
    ip_diversity ← COUNT(ip_addresses) / COUNT(submissions)
    ua_diversity ← COUNT(user_agents) / COUNT(submissions)
    
    // Pattern consistency
    templates ← INITIALIZE empty list
    FOR EACH submission IN submissions DO
        template ← ExtractFormTemplate(submission.raw_payload,
                                      fields=["name", "email", "subject", "message"])
        APPEND template TO templates
    END FOR
    unique_templates ← COUNT UNIQUE templates
    pattern_consistency ← 1 - (unique_templates / COUNT(submissions))
    
    RETURN {
        time_span: time_span,
        submission_rate: submission_rate,
        ip_diversity: ip_diversity,
        user_agent_diversity: ua_diversity,
        pattern_consistency: pattern_consistency
    }
END FUNCTION
```

### 4.3 Campaign Severity Assessment
```
FUNCTION AssessCampaignSeverity(campaign)
    INPUT: campaign - campaign data structure
    OUTPUT: severity score and classification
    
    severity_score ← 0
    
    // High volume indicator
    IF campaign.total_submissions > 100 THEN
        severity_score ← severity_score + 30
    ELSE IF campaign.total_submissions > 50 THEN
        severity_score ← severity_score + 20
    ELSE IF campaign.total_submissions > 10 THEN
        severity_score ← severity_score + 10
    END IF
    
    // Rapid submission rate indicator
    IF campaign.submission_rate > 10 THEN  // >10 per hour
        severity_score ← severity_score + 25
    ELSE IF campaign.submission_rate > 5 THEN
        severity_score ← severity_score + 15
    ELSE IF campaign.submission_rate > 1 THEN
        severity_score ← severity_score + 5
    END IF
    
    // Low diversity indicates automated attack
    IF campaign.ip_diversity < 0.1 THEN  // <10% unique IPs
        severity_score ← severity_score + 20
    END IF
    
    IF campaign.user_agent_diversity < 0.05 THEN  // <5% unique UAs
        severity_score ← severity_score + 15
    END IF
    
    // High pattern consistency indicates coordinated campaign
    IF campaign.pattern_consistency > 0.9 THEN
        severity_score ← severity_score + 10
    END IF
    
    // Classify severity
    IF severity_score >= 70 THEN
        classification ← "critical"
    ELSE IF severity_score >= 50 THEN
        classification ← "high"
    ELSE IF severity_score >= 30 THEN
        classification ← "medium"
    ELSE
        classification ← "low"
    END IF
    
    RETURN {severity_score: severity_score, classification: classification}
END FUNCTION
```

---

## 5. Evaluation Strategy

### 5.1 Overall System Evaluation
```
FUNCTION RunEvaluation()
    INPUT: none (uses system data)
    OUTPUT: comprehensive evaluation report
    
    OUTPUT "=== Honeypot Security System Evaluation ==="
    
    results ← INITIALIZE empty dictionary
    
    // Evaluate different aspects of system performance
    results.detection_metrics ← CalculateDetectionMetrics()
    results.honeypot_trigger_rate ← CalculateHoneypotTriggerRate()
    results.rule_effectiveness ← EvaluateRuleEffectiveness()
    results.false_positive_analysis ← AnalyzeFalsePositives()
    results.performance_metrics ← CollectPerformanceMetrics()
    results.pattern_coverage ← AnalyzePatternCoverage()
    
    // Display and save results
    PrintEvaluationReport(results)
    SaveEvaluationReport(results)
    
    RETURN results
END FUNCTION
```

### 5.2 Detection Metrics Calculation
```
FUNCTION CalculateDetectionMetrics()
    INPUT: none (queries database)
    OUTPUT: detection performance metrics
    
    // Gather submission statistics
    total_submissions ← COUNT submissions FROM database
    
    honeypot_triggered ← COUNT submissions FROM database 
                         WHERE honeypot_hits is not empty
    
    high_risk_submissions ← COUNT submission_scores FROM database
                           WHERE risk_level IN ["high", "critical"]
    
    // Gather validation statistics
    true_positives ← SUM true_positive_count FROM metrics table
    false_positives ← SUM false_positive_count FROM metrics table
    
    // Calculate performance rates
    IF total_submissions > 0 THEN
        detection_rate ← (honeypot_triggered / total_submissions) × 100
        high_risk_rate ← (high_risk_submissions / total_submissions) × 100
    ELSE
        detection_rate ← 0
        high_risk_rate ← 0
    END IF
    
    // Calculate precision (positive predictive value)
    IF (true_positives + false_positives) > 0 THEN
        precision ← (true_positives / (true_positives + false_positives)) × 100
    ELSE
        precision ← 0
    END IF
    
    // Calculate recall (sensitivity)
    true_negatives ← total_submissions - honeypot_triggered
    IF (true_positives + true_negatives) > 0 THEN
        recall ← (true_positives / (true_positives + true_negatives)) × 100
    ELSE
        recall ← 0
    END IF
    
    // Calculate F1-score (harmonic mean of precision and recall)
    IF (precision + recall) > 0 THEN
        f1_score ← 2 × (precision × recall) / (precision + recall)
    ELSE
        f1_score ← 0
    END IF
    
    RETURN {
        total_submissions: total_submissions,
        honeypot_triggered: honeypot_triggered,
        high_risk_count: high_risk_submissions,
        true_positives: true_positives,
        false_positives: false_positives,
        detection_rate: ROUND(detection_rate, 2),
        high_risk_rate: ROUND(high_risk_rate, 2),
        precision: ROUND(precision, 2),
        recall: ROUND(recall, 2),
        f1_score: ROUND(f1_score, 2)
    }
END FUNCTION
```

### 5.3 Honeypot Effectiveness Analysis
```
FUNCTION CalculateHoneypotTriggerRate()
    INPUT: none (queries database)
    OUTPUT: honeypot-specific metrics by type
    
    honeypot_types ← ["invisible_field", "timing_trap", "mouse_movement", "tab_order"]
    trigger_rates ← INITIALIZE empty dictionary
    
    total_with_honeypot ← COUNT submissions FROM database 
                          WHERE honeypot_hits is not empty
    
    FOR EACH honeypot_type IN honeypot_types DO
        // Count submissions triggering specific honeypot type
        count ← COUNT submissions FROM database 
                WHERE honeypot_hits CONTAINS honeypot_type
        
        IF total_with_honeypot > 0 THEN
            rate ← (count / total_with_honeypot) × 100
        ELSE
            rate ← 0
        END IF
        
        trigger_rates[honeypot_type] ← {
            count: count,
            rate: ROUND(rate, 2)
        }
    END FOR
    
    RETURN trigger_rates
END FUNCTION
```

### 5.4 Rule Effectiveness Evaluation
```
FUNCTION EvaluateRuleEffectiveness()
    INPUT: none (queries database)
    OUTPUT: per-rule effectiveness metrics
    
    rules ← FETCH all rules FROM database
    rule_stats ← INITIALIZE empty list
    
    FOR EACH rule IN rules DO
        // Count how often rule was triggered
        triggered_count ← COUNT submission_scores FROM database
                         WHERE rules_triggered CONTAINS rule.id
        
        // Get submissions where only this rule triggered
        solo_triggers ← COUNT submission_scores FROM database
                       WHERE rules_triggered = [rule.id]
        
        // Calculate rule contribution
        total_scored ← COUNT submission_scores FROM database
        
        IF total_scored > 0 THEN
            trigger_rate ← (triggered_count / total_scored) × 100
            solo_rate ← (solo_triggers / triggered_count) × 100 
                        IF triggered_count > 0 ELSE 0
        ELSE
            trigger_rate ← 0
            solo_rate ← 0
        END IF
        
        // Analyze rule accuracy (requires manual labeling)
        validated_submissions ← FETCH submissions 
                               WHERE rule.id IN rules_triggered 
                               AND manual_label is not null
        
        IF COUNT(validated_submissions) > 0 THEN
            correct_triggers ← COUNT validated_submissions 
                              WHERE manual_label = "bot"
            accuracy ← (correct_triggers / COUNT(validated_submissions)) × 100
        ELSE
            accuracy ← null
        END IF
        
        APPEND {
            rule_id: rule.id,
            rule_name: rule.name,
            triggered_count: triggered_count,
            trigger_rate: ROUND(trigger_rate, 2),
            solo_rate: ROUND(solo_rate, 2),
            accuracy: ROUND(accuracy, 2) IF accuracy is not null ELSE "N/A",
            weight: rule.weight,
            severity: rule.severity
        } TO rule_stats
    END FOR
    
    // Sort by trigger count descending
    rule_stats ← SORT rule_stats BY triggered_count DESCENDING
    
    RETURN rule_stats
END FUNCTION
```

### 5.5 False Positive Analysis
```
FUNCTION AnalyzeFalsePositives()
    INPUT: none (queries database)
    OUTPUT: false positive analysis results
    
    // Get high-risk submissions manually marked as legitimate
    false_positives ← FETCH submissions FROM database
                     WHERE risk_level IN ["high", "critical"]
                     AND manual_label = "legitimate"
    
    false_positive_count ← COUNT(false_positives)
    
    // Analyze which rules caused false positives
    rule_fp_counts ← INITIALIZE empty dictionary
    
    FOR EACH fp_submission IN false_positives DO
        triggered_rules ← DECODE JSON from fp_submission.rules_triggered
        
        FOR EACH rule IN triggered_rules DO
            IF rule.id NOT IN rule_fp_counts THEN
                rule_fp_counts[rule.id] ← {name: rule.name, count: 0}
            END IF
            
            rule_fp_counts[rule.id].count ← rule_fp_counts[rule.id].count + 1
        END FOR
    END FOR
    
    // Calculate false positive rate
    total_high_risk ← COUNT submissions FROM database
                     WHERE risk_level IN ["high", "critical"]
    
    IF total_high_risk > 0 THEN
        fp_rate ← (false_positive_count / total_high_risk) × 100
    ELSE
        fp_rate ← 0
    END IF
    
    // Sort rules by false positive contribution
    fp_by_rule ← CONVERT rule_fp_counts TO list
    fp_by_rule ← SORT fp_by_rule BY count DESCENDING
    
    RETURN {
        false_positive_count: false_positive_count,
        false_positive_rate: ROUND(fp_rate, 2),
        total_high_risk: total_high_risk,
        rules_causing_fps: fp_by_rule
    }
END FUNCTION
```

### 5.6 Performance Metrics Collection
```
FUNCTION CollectPerformanceMetrics()
    INPUT: none (queries database and system)
    OUTPUT: system performance statistics
    
    // Database performance
    avg_scoring_time ← CALCULATE AVERAGE execution time of ScoreSubmission()
    avg_extraction_time ← CALCULATE AVERAGE execution time of ExtractSignatures()
    
    // System throughput
    submissions_per_day ← CALCULATE AVERAGE daily submission count
    processing_rate ← 1 / avg_scoring_time  // submissions per second
    
    // Storage metrics
    total_submissions ← COUNT submissions FROM database
    total_signatures ← COUNT signatures FROM database
    total_clusters ← COUNT clusters FROM database
    database_size ← GET database size in megabytes
    
    // Pattern efficiency
    compression_ratio ← total_submissions / total_signatures 
                        IF total_signatures > 0 ELSE 0
    
    RETURN {
        avg_scoring_time_ms: ROUND(avg_scoring_time, 2),
        avg_extraction_time_ms: ROUND(avg_extraction_time, 2),
        submissions_per_day: ROUND(submissions_per_day, 2),
        processing_rate: ROUND(processing_rate, 2),
        total_submissions: total_submissions,
        total_signatures: total_signatures,
        total_clusters: total_clusters,
        database_size_mb: ROUND(database_size, 2),
        compression_ratio: ROUND(compression_ratio, 2)
    }
END FUNCTION
```

### 5.7 Pattern Coverage Analysis
```
FUNCTION AnalyzePatternCoverage()
    INPUT: none (queries database)
    OUTPUT: pattern coverage metrics
    
    // Analyze signature distribution
    total_submissions ← COUNT submissions FROM database
    submissions_with_signatures ← COUNT DISTINCT submissions
                                  WHERE signature_hash EXISTS in signatures
    
    coverage_rate ← (submissions_with_signatures / total_submissions) × 100
                    IF total_submissions > 0 ELSE 0
    
    // Analyze cluster coverage
    submissions_in_clusters ← COUNT submissions
                             WHERE signature_hash IN 
                             (SELECT signature_hash FROM signatures s
                              JOIN clusters c ON s.id IN c.signature_ids)
    
    cluster_coverage ← (submissions_in_clusters / total_submissions) × 100
                      IF total_submissions > 0 ELSE 0
    
    // Analyze pattern diversity
    total_signatures ← COUNT signatures FROM database
    avg_occurrence ← CALCULATE AVERAGE occurrence FROM signatures
    max_occurrence ← CALCULATE MAX occurrence FROM signatures
    
    // Find most common patterns
    top_patterns ← FETCH TOP 10 signatures 
                   ORDER BY occurrence DESCENDING
    
    RETURN {
        signature_coverage: ROUND(coverage_rate, 2),
        cluster_coverage: ROUND(cluster_coverage, 2),
        total_unique_patterns: total_signatures,
        avg_pattern_occurrence: ROUND(avg_occurrence, 2),
        max_pattern_occurrence: max_occurrence,
        top_patterns: top_patterns
    }
END FUNCTION
```

### 5.8 Report Generation
```
FUNCTION PrintEvaluationReport(results)
    INPUT: results - evaluation results dictionary
    OUTPUT: formatted console output
    
    OUTPUT "Detection Metrics:"
    OUTPUT "  Total Submissions: " + results.detection_metrics.total_submissions
    OUTPUT "  Detection Rate: " + results.detection_metrics.detection_rate + "%"
    OUTPUT "  Precision: " + results.detection_metrics.precision + "%"
    OUTPUT "  Recall: " + results.detection_metrics.recall + "%"
    OUTPUT "  F1-Score: " + results.detection_metrics.f1_score
    OUTPUT ""
    
    OUTPUT "Honeypot Effectiveness:"
    FOR EACH honeypot_type, metrics IN results.honeypot_trigger_rate DO
        OUTPUT "  " + honeypot_type + ": " + metrics.count + " (" + metrics.rate + "%)"
    END FOR
    OUTPUT ""
    
    OUTPUT "Rule Effectiveness (Top 5):"
    FOR i FROM 0 TO MIN(4, LENGTH(results.rule_effectiveness) - 1) DO
        rule ← results.rule_effectiveness[i]
        OUTPUT "  " + rule.rule_name + ": " + rule.triggered_count + " triggers (" + 
               rule.trigger_rate + "%), accuracy: " + rule.accuracy
    END FOR
    OUTPUT ""
    
    OUTPUT "False Positive Analysis:"
    OUTPUT "  FP Count: " + results.false_positive_analysis.false_positive_count
    OUTPUT "  FP Rate: " + results.false_positive_analysis.false_positive_rate + "%"
    OUTPUT ""
    
    OUTPUT "Performance Metrics:"
    OUTPUT "  Avg Scoring Time: " + results.performance_metrics.avg_scoring_time_ms + " ms"
    OUTPUT "  Processing Rate: " + results.performance_metrics.processing_rate + " submissions/s"
    OUTPUT "  Compression Ratio: " + results.performance_metrics.compression_ratio + ":1"
    OUTPUT ""
    
    OUTPUT "Pattern Coverage:"
    OUTPUT "  Signature Coverage: " + results.pattern_coverage.signature_coverage + "%"
    OUTPUT "  Cluster Coverage: " + results.pattern_coverage.cluster_coverage + "%"
    OUTPUT "  Unique Patterns: " + results.pattern_coverage.total_unique_patterns
END FUNCTION
```

```
FUNCTION SaveEvaluationReport(results)
    INPUT: results - evaluation results dictionary
    OUTPUT: JSON file saved to disk
    
    timestamp ← GET current timestamp formatted as "YYYY-MM-DD_HH-MM-SS"
    filename ← "evaluation_" + timestamp + ".json"
    filepath ← "logs/" + filename
    
    // Serialize results to JSON
    json_content ← ENCODE results as JSON with pretty formatting
    
    // Write to file
    WRITE json_content TO filepath
    
    OUTPUT "Evaluation report saved to: " + filepath
    
    RETURN filepath
END FUNCTION
```

---

## 6. Summary

This pseudocode documentation describes the core algorithms of the FormTrap honeypot-based bot detection system:

1. **Preprocessing and Normalization**: Standardizes input data by removing noise, converting to uniform case, and extracting generalized templates with value placeholders for pattern matching.

2. **Honeypot Signal Extraction**: Generates unique signatures from submission templates, tracks occurrence frequencies, and builds clusters of similar patterns to identify automated attack campaigns.

3. **Rule-based Detection and Scoring**: Evaluates submissions against configurable detection rules (honeypot triggers, timing anomalies, pattern matches, etc.) and assigns numerical risk scores with severity classifications.

4. **Campaign Identification**: Groups submissions with similar signatures into clusters, analyzes temporal and source diversity patterns, and assesses campaign severity based on volume, rate, and consistency metrics.

5. **Evaluation Strategy**: Measures system effectiveness through detection metrics (precision, recall, F1-score), rule effectiveness analysis, false positive rates, performance benchmarks, and pattern coverage statistics.

The system follows a multi-layered defense approach combining behavioral analysis, pattern recognition, and statistical evaluation to distinguish automated bot submissions from legitimate user interactions.
