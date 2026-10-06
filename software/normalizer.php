<?php
/**
 * Input normalizer for pattern extraction and matching
 */

class InputNormalizer {
    
    /**
     * Normalize text for signature generation
     * Removes noise while preserving structural patterns
     */
    public static function normalizeText($text) {
        if (!is_string($text)) {
            return '';
        }

        // Convert to lowercase
        $normalized = mb_strtolower($text, 'UTF-8');
        
        // Remove excessive whitespace
        $normalized = preg_replace('/\s+/', ' ', $normalized);
        
        // Trim
        $normalized = trim($normalized);
        
        return $normalized;
    }

    /**
     * Normalize for template extraction (replace specific values with tokens)
     */
    public static function extractTemplate($text) {
        if (!is_string($text)) {
            return '';
        }

        $template = $text;

        // Normalize to lowercase for consistent tokenization
        $template = mb_strtolower($template, 'UTF-8');
        
        // Replace email addresses with token
        $template = preg_replace('/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/', '<EMAIL>', $template);
        
        // Replace URLs with token
        $template = preg_replace('/https?:\/\/[^\s]+/', '<URL>', $template);
        
        // Replace phone numbers with token (allow shorter local formats)
        // Match sequences that start and end with a digit and contain digits, spaces, hyphens or parentheses
        $template = preg_replace('/(\+?\d[\d\-\s\(\)]{5,}\d)/', '<PHONE>', $template);
        
        // Replace numbers with token
        $template = preg_replace('/\b\d+\b/', '<NUM>', $template);
        
        // Replace consecutive repeated characters (spam patterns)
        $template = preg_replace('/(.)\1{3,}/', '<REPEAT>', $template);
        
        // Normalize whitespace
        $template = preg_replace('/\s+/', ' ', $template);
        $template = trim($template);
        
        return $template;
    }

    /**
     * Normalize all form inputs and concatenate for signature
     */
    public static function normalizeFormData($formData, $fieldsToNormalize) {
        $normalized = [];
        
        foreach ($fieldsToNormalize as $field) {
            if (isset($formData[$field])) {
                $normalized[$field] = self::normalizeText($formData[$field]);
            }
        }
        
        // Concatenate all normalized fields with separator
        return implode(' | ', array_values($normalized));
    }

    /**
     * Extract template from all form inputs
     */
    public static function extractFormTemplate($formData, $fieldsToExtract) {
        $templates = [];
        
        foreach ($fieldsToExtract as $field) {
            if (isset($formData[$field])) {
                $templates[$field] = self::extractTemplate($formData[$field]);
            }
        }
        
        return implode(' | ', array_values($templates));
    }

    /**
     * Generate signature hash from normalized text
     */
    public static function generateSignatureHash($text) {
        return hash('sha256', $text);
    }

    /**
     * Calculate Levenshtein similarity ratio between two strings
     * Returns value between 0 and 1 (1 = identical)
     */
    public static function calculateSimilarity($str1, $str2) {
        $maxLen = max(strlen($str1), strlen($str2));
        if ($maxLen === 0) {
            return 1.0;
        }
        
        $distance = levenshtein(
            substr($str1, 0, 255),
            substr($str2, 0, 255)
        );
        
        return 1 - ($distance / $maxLen);
    }

    /**
     * Extract n-grams from text for pattern matching
     */
    public static function extractNgrams($text, $n = 3) {
        $text = self::normalizeText($text);
        $words = explode(' ', $text);
        $ngrams = [];
        
        for ($i = 0; $i <= count($words) - $n; $i++) {
            $ngram = implode(' ', array_slice($words, $i, $n));
            $ngrams[] = $ngram;
        }
        
        return $ngrams;
    }

    /**
     * Tokenize text into words
     */
    public static function tokenize($text) {
        $normalized = self::normalizeText($text);
        return array_filter(explode(' ', $normalized));
    }

    /**
     * Detect repetitive patterns
     */
    public static function hasRepetitivePattern($text, $threshold = 10) {
        // Check for character repetition
        if (preg_match('/(.)\\1{' . $threshold . ',}/', $text)) {
            return true;
        }
        
        // Check for word repetition
        $words = self::tokenize($text);
        if (count($words) > 0) {
            $wordCounts = array_count_values($words);
            foreach ($wordCounts as $count) {
                if ($count >= $threshold) {
                    return true;
                }
            }
        }
        
        return false;
    }

    /**
     * Validate email format
     */
    public static function isValidEmail($email) {
        return filter_var($email, FILTER_VALIDATE_EMAIL) !== false;
    }

    /**
     * Detect suspicious patterns in text
     */
    public static function detectSuspiciousPatterns($text) {
        $patterns = [
            'sql_injection' => '/(union\s+select|drop\s+table|or\s+1\s*=\s*1|xp_cmdshell|information_schema)/i',
            'xss' => '/(<script|javascript:|onerror\s*=|onload\s*=|<iframe)/i',
            'path_traversal' => '/(\.\.\/|\.\.\\\\)/i',
            'command_injection' => '/(;|\||&&|\$\(|`)/i',
        ];

        $detected = [];
        foreach ($patterns as $type => $pattern) {
            if (preg_match($pattern, $text)) {
                $detected[] = $type;
            }
        }

        return $detected;
    }
}
