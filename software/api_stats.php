<?php
/**
 * JSON API endpoints for dashboard
 */

header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');

require_once __DIR__ . '/db.php';
require_once __DIR__ . '/extractor.php';

$action = $_GET['action'] ?? '';

try {
    $db = Database::getInstance();
    $response = [];

    switch ($action) {
        case 'stats':
            $response = getStats($db);
            break;

        case 'recent_submissions':
            $limit = intval($_GET['limit'] ?? 50);
            $response = getRecentSubmissions($db, $limit);
            break;

        case 'risk_distribution':
            $response = getRiskDistribution($db);
            break;

        case 'top_patterns':
            $limit = intval($_GET['limit'] ?? 10);
            $response = getTopPatterns($db, $limit);
            break;

        case 'timeline':
            $range = $_GET['range'] ?? '30d';
            $response = getTimeline($db, $range);
            break;

        case 'honeypot_effectiveness':
            $response = getHoneypotEffectiveness($db);
            break;

        case 'submission_detail':
            $id = intval($_GET['id'] ?? 0);
            $response = getSubmissionDetail($db, $id);
            break;

        case 'cluster_list':
            $response = getClusterList($db);
            break;

        case 'ml_summary':
            $response = getMlSummary($db);
            break;

        case 'olap':
            $response = getOlap($db, $_GET);
            break;

        default:
            http_response_code(400);
            $response = ['error' => 'Invalid action'];
    }

    echo json_encode($response, JSON_PRETTY_PRINT);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => $e->getMessage()]);
}

/**
 * Get overall statistics
 */
function getStats($db) {
    $totalSubmissions = $db->fetchColumn("SELECT COUNT(*) FROM submissions");
    $todaySubmissions = $db->fetchColumn(
        "SELECT COUNT(*) FROM submissions WHERE DATE(created_at) = CURDATE()"
    );
    $honeypotTriggered = $db->fetchColumn(
        "SELECT COUNT(*) FROM submissions WHERE JSON_LENGTH(honeypot_hits) > 0"
    );
    $highRiskCount = $db->fetchColumn(
        "SELECT COUNT(*) FROM submission_scores WHERE risk_level IN ('high', 'critical')"
    );
    $uniqueSignatures = $db->fetchColumn("SELECT COUNT(*) FROM signatures");
    $totalClusters = $db->fetchColumn("SELECT COUNT(*) FROM clusters");

    $detectionRate = $totalSubmissions > 0 
        ? round(($honeypotTriggered / $totalSubmissions) * 100, 2) 
        : 0;

    return [
        'total_submissions' => $totalSubmissions,
        'today_submissions' => $todaySubmissions,
        'honeypot_triggered' => $honeypotTriggered,
        'high_risk_count' => $highRiskCount,
        'unique_signatures' => $uniqueSignatures,
        'total_clusters' => $totalClusters,
        'detection_rate' => $detectionRate
    ];
}

/**
 * Get recent submissions with scores
 */
function getRecentSubmissions($db, $limit) {
    return $db->fetchAll(
        "SELECT 
            s.id,
            s.created_at,
            s.ip,
            s.user_agent,
            JSON_LENGTH(s.honeypot_hits) as honeypot_count,
            s.client_render_time,
            ss.score,
            ss.risk_level
         FROM submissions s
         LEFT JOIN submission_scores ss ON s.id = ss.submission_id
         ORDER BY s.created_at DESC
         LIMIT ?",
        [$limit]
    );
}

/**
 * Get risk level distribution
 */
function getRiskDistribution($db) {
    $distribution = $db->fetchAll(
        "SELECT risk_level, COUNT(*) as count 
         FROM submission_scores 
         GROUP BY risk_level"
    );

    $result = ['low' => 0, 'medium' => 0, 'high' => 0, 'critical' => 0];
    foreach ($distribution as $row) {
        $result[$row['risk_level']] = intval($row['count']);
    }

    return $result;
}

/**
 * Get top attack patterns
 */
function getTopPatterns($db, $limit) {
    return $db->fetchAll(
        "SELECT id, pattern, occurrence, last_seen 
         FROM signatures 
         ORDER BY occurrence DESC 
         LIMIT ?",
        [$limit]
    );
}

/**
 * Get timeline data
 */
function getTimeline($db, $range) {
    // Parse range parameter (e.g., '30m', '1h', '12h', '1d', '7d', '30d')
    $unit = substr($range, -1); // Last character (m, h, d)
    $value = intval(substr($range, 0, -1)); // Number part

    $interval = '';
    $groupBy = '';
    $dateFormat = '';

    switch ($unit) {
        case 'm': // minutes
            $interval = "INTERVAL {$value} MINUTE";
            $format = "DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:00')";
            $groupBy = $format;
            $dateFormat = $format;
            break;
        case 'h': // hours
            $interval = "INTERVAL {$value} HOUR";
            $format = "DATE_FORMAT(created_at, '%Y-%m-%d %H:00:00')";
            $groupBy = $format;
            $dateFormat = $format;
            break;
        case 'd': // days
        default:
            $interval = "INTERVAL {$value} DAY";
            $groupBy = "DATE(created_at)";
            $dateFormat = "DATE(created_at)";
            break;
    }

    $unitMap = ['m' => 'MINUTE', 'h' => 'HOUR', 'd' => 'DAY'];
    $sqlUnit = $unitMap[$unit] ?? 'DAY';

    $sql = "SELECT 
            {$dateFormat} as date,
            COUNT(*) as total,
            SUM(CASE WHEN JSON_LENGTH(honeypot_hits) > 0 THEN 1 ELSE 0 END) as honeypot_triggered
         FROM submissions
         WHERE created_at >= DATE_SUB(NOW(), INTERVAL {$value} {$sqlUnit})
         GROUP BY {$groupBy}
         ORDER BY date ASC";

    return $db->fetchAll($sql, []);
}

/**
 * Get honeypot effectiveness metrics
 */
function getHoneypotEffectiveness($db) {
    $config = require __DIR__ . '/config.php';
    $honeypots = $config['honeypot'];

    $effectiveness = [];
    
    // Count hits per honeypot type
    foreach (['text_hidden', 'semantic', 'time_trap'] as $type) {
        $fieldName = $honeypots[$type];
        
        $count = $db->fetchColumn(
            "SELECT COUNT(*) FROM submissions 
             WHERE JSON_SEARCH(honeypot_hits, 'one', ?) IS NOT NULL",
            [$fieldName]
        );

        $effectiveness[$type] = [
            'field_name' => $fieldName,
            'hits' => $count
        ];
    }

    return $effectiveness;
}

/**
 * Get detailed submission info
 */
function getSubmissionDetail($db, $id) {
    $submission = $db->fetchOne("SELECT * FROM submissions WHERE id = ?", [$id]);
    
    if (!$submission) {
        return ['error' => 'Submission not found'];
    }

    // Decode JSON fields
    $submission['raw_payload'] = json_decode($submission['raw_payload'], true);
    $submission['honeypot_hits'] = json_decode($submission['honeypot_hits'], true);
    $submission['flags'] = json_decode($submission['flags'], true);
    $submission['request_headers'] = json_decode($submission['request_headers'], true);

    // Get score
    $score = $db->fetchOne(
        "SELECT * FROM submission_scores WHERE submission_id = ?",
        [$id]
    );

    if ($score) {
        $score['rules_triggered'] = json_decode($score['rules_triggered'], true);
        $submission['score'] = $score;
    }

    // Analyze pattern
    $extractor = new Extractor();
    $analysis = $extractor->analyzeSubmission($id);
    $submission['analysis'] = $analysis;

    return $submission;
}

/**
 * Get cluster list
 */
function getClusterList($db) {
    $clusters = $db->fetchAll(
        "SELECT id, cluster_label, description, 
                JSON_LENGTH(signature_ids) as signature_count,
                updated_at
         FROM clusters 
         ORDER BY updated_at DESC"
    );

    return $clusters;
}

/**
 * Predictions of the mined text model: totals, live campaign counts and the latest scored submissions
 */
function getMlSummary($db) {
    $totals = $db->fetchOne(
        "SELECT COUNT(*) AS scored,
                COALESCE(SUM(label = 'spam'), 0) AS spam,
                COALESCE(SUM(label = 'legitimate'), 0) AS legitimate,
                MAX(model_version) AS model_version
         FROM ml_predictions"
    );
    $totals['unscored'] = $db->fetchColumn(
        "SELECT COUNT(*) FROM submissions s LEFT JOIN ml_predictions p ON p.submission_id = s.id WHERE p.id IS NULL"
    );

    $campaigns = $db->fetchAll(
        "SELECT campaign_id, campaign_label, COUNT(*) AS submissions
         FROM ml_predictions WHERE label = 'spam'
         GROUP BY campaign_id, campaign_label ORDER BY submissions DESC"
    );

    $recent = $db->fetchAll(
        "SELECT s.id, s.created_at, p.spam_probability, p.label, p.campaign_label, p.top_terms, p.matched_rules,
                ss.score, ss.risk_level, JSON_LENGTH(s.honeypot_hits) AS honeypot_count,
                LEFT(JSON_UNQUOTE(JSON_EXTRACT(s.raw_payload, '$.message')), 140) AS message
         FROM ml_predictions p
         JOIN submissions s ON s.id = p.submission_id
         LEFT JOIN submission_scores ss ON ss.submission_id = s.id
         ORDER BY s.id DESC LIMIT 15"
    );
    foreach ($recent as &$row) {
        $row['top_terms'] = json_decode($row['top_terms'] ?? '[]', true);
        $row['matched_rules'] = json_decode($row['matched_rules'] ?? '[]', true);
    }

    $rules = $db->fetchAll("SELECT name, description, severity, weight, condition_type FROM rules WHERE enabled = 1 ORDER BY weight DESC");

    return ['totals' => $totals, 'campaigns' => $campaigns, 'recent' => $recent, 'rules' => $rules];
}

/**
 * OLAP view over the submissions fact table.
 *   level = year | quarter | month   roll-up / drill-down along the time hierarchy
 *   year  = 2023                     slice: fix one value of the time dimension
 *   label = spam | legitimate        dice: restrict a second dimension as well
 *   by    = none | label | campaign | risk   second dimension of the result
 * GROUP BY ... WITH ROLLUP adds the subtotal and grand-total rows.
 */
function getOlap($db, $query) {
    $periods = [
        'year' => "CAST(YEAR(s.created_at) AS CHAR)",
        'quarter' => "CONCAT(YEAR(s.created_at), ' Q', QUARTER(s.created_at))",
        'month' => "DATE_FORMAT(s.created_at, '%Y-%m')",
    ];
    $groups = [
        'none' => null,
        'label' => "COALESCE(p.label, 'not scored')",
        'campaign' => "COALESCE(p.campaign_label, 'not scored')",
        'risk' => "COALESCE(ss.risk_level, 'not scored')",
    ];
    $level = isset($periods[$query['level'] ?? '']) ? $query['level'] : 'year';
    $by = array_key_exists($query['by'] ?? '', $groups) ? $query['by'] : 'none';

    $config = require __DIR__ . '/config.php';
    $params = [json_encode($config['honeypot']['text_hidden'])];
    $where = [];
    if (!empty($query['year']) && ctype_digit((string) $query['year'])) {
        $where[] = "YEAR(s.created_at) = ?";
        $params[] = (int) $query['year'];
    }
    if (in_array($query['label'] ?? '', ['spam', 'legitimate'], true)) {
        $where[] = "p.label = ?";
        $params[] = $query['label'];
    }

    $period = $periods[$level];
    $group = $groups[$by];
    $select = $group ? "$period AS period, $group AS grp" : "$period AS period";
    $groupBy = $group ? "$period, $group" : $period;
    $whereSql = $where ? 'WHERE ' . implode(' AND ', $where) : '';

    // A row is "labelled" unless it was imported from the window in which the honeypot was not recorded.
    $rows = $db->fetchAll(
        "SELECT $select,
                COUNT(*) AS submissions,
                SUM(COALESCE(s.flags->>'$.honeypot_recorded', 'true') <> 'false') AS labelled,
                SUM(JSON_CONTAINS(s.honeypot_hits, ?)) AS honeypot_hits,
                COUNT(p.id) AS scored,
                COALESCE(SUM(p.label = 'spam'), 0) AS ml_spam
         FROM submissions s
         LEFT JOIN ml_predictions p ON p.submission_id = s.id
         LEFT JOIN submission_scores ss ON ss.submission_id = s.id
         $whereSql
         GROUP BY $groupBy WITH ROLLUP",
        $params
    );

    foreach ($rows as &$row) {
        foreach (['submissions', 'labelled', 'honeypot_hits', 'scored', 'ml_spam'] as $measure) {
            $row[$measure] = (int) $row[$measure];
        }
        $row['hit_rate'] = $row['labelled'] > 0 ? round($row['honeypot_hits'] / $row['labelled'], 4) : null;
        $row['ml_spam_rate'] = $row['scored'] > 0 ? round($row['ml_spam'] / $row['scored'], 4) : null;
        // WITH ROLLUP marks its summary rows with NULL in the rolled-up column
        $row['is_total'] = $row['period'] === null;
        $row['is_subtotal'] = $group && $row['period'] !== null && $row['grp'] === null;
    }

    $years = $db->fetchAll("SELECT DISTINCT YEAR(created_at) AS y FROM submissions ORDER BY y");
    return ['level' => $level, 'by' => $by, 'rows' => $rows, 'years' => array_column($years, 'y')];
}
