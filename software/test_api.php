<?php
$url = 'http://localhost:8000/api_stats.php?action=top_patterns&limit=10';
$result = file_get_contents($url);
if ($result === false) {
    echo 'Failed to fetch data\n';
} else {
    $data = json_decode($result, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        echo 'Invalid JSON response\n';
    } else {
        echo 'API Response: ' . count($data) . ' patterns found\n';
        if (count($data) > 0) {
            echo 'First pattern: ' . substr($data[0]['pattern'], 0, 50) . '...\n';
            echo 'Occurrences: ' . $data[0]['occurrence'] . '\n';
        }
    }
}

