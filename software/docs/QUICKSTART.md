# QUICK START GUIDE

> This version of FormTrap also scores each message with a text model mined from five years of
> submissions. Start it with `python ml_service/app.py` (after `pip install -r ml_service/requirements.txt`)
> and open `mining.php` for the data-mining view. FormTrap works without the service; the model's rule
> simply does not trigger. See `docs/DATA_MINING.md`.

## Prerequisites Check

Before starting, ensure you have:
- [x] PHP 8.0+ installed (`php -v`)
- [x] MySQL 8.0+ or MariaDB 10.5+ installed
- [x] PDO MySQL extension enabled (`php -m | grep pdo_mysql`)
- [x] Web server (Apache/Nginx) OR PHP built-in server

## Installation (5 Minutes)

### Step 1: Database Setup

```bash
# Option A: Using MySQL CLI
mysql -u root -p -e "CREATE DATABASE form_trap_dm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p form_trap_dm < schema.sql

# Option B: Using phpMyAdmin
# 1. Create database named "form_trap_dm"
# 2. Import schema.sql file through phpMyAdmin interface
```

**Verify:**
```bash
mysql -u root -p form_trap_dm -e "SHOW TABLES;"
# Should show: submissions, submission_scores, signatures, clusters, rules, events, metrics
```

**Add the data-mining tables and rule:**
```bash
mysql -u root -p < migrations/002_ml.sql
# Adds the table ml_predictions and the rule ml_spam_score
```

### Step 2: Configure Database Credentials

Edit `config.php`:

```php
'db' => [
    'host' => 'localhost',
    'port' => 3306,
    'database' => 'form_trap_dm',
    'username' => 'root',          // ← Change to your MySQL user
    'password' => 'your_password', // ← Change to your MySQL password
    'charset' => 'utf8mb4',
]
```

### Step 3: Set Permissions (Linux/Mac only)

```bash
# Make cron script executable
chmod +x cron/run_extractor.php
chmod +x evaluate.php

# Create logs directory
mkdir -p logs
chmod 755 logs

# If using Apache, ensure www-data can write to logs
sudo chown -R www-data:www-data logs/  # Linux
# OR
sudo chown -R _www:_www logs/          # Mac
```

### Step 4: Test System

```bash
php test.php
```

**Expected output:**
```
=== Honeypot Security System - Quick Test ===

Test 1: Database Connection... ✓ PASS
Test 2: Normalizer... ✓ PASS
Test 3: Logger... ✓ PASS (Submission ID: 1)
Test 4: Scorer... ✓ PASS (Score: 23, Risk: medium)
Test 5: Extractor... ✓ PASS (Signatures: 1, Clusters: 0)
Test 6: API Stats... ✓ PASS
Test 7: Evaluator... ✓ PASS (Detection Rate: 0.00%)

=== Test Summary ===
All critical components tested.
```

If any test fails, check:
- Database credentials in `config.php`
- MySQL service is running
- PHP extensions installed (`php -m`)

### Step 5: Start Server

**Option A: PHP Built-in Server (Development)**
```bash
php -S 127.0.0.1:8090
```

**Option B: Apache Virtual Host (Production)**
```apache
<VirtualHost *:80>
    ServerName honeypot.local
    DocumentRoot /path/to/HoneyComp
    
    <Directory /path/to/HoneyComp>
        AllowOverride All
        Require all granted
    </Directory>
</VirtualHost>
```

Then add to `/etc/hosts`:
```
127.0.0.1 honeypot.local
```

### Step 6: Access System

Open your browser:

1. **Contact Form**: http://127.0.0.1:8090/index.php
   - Submit a test form (wait 3+ seconds before submitting)
   - Should see success message

2. **Dashboard**: http://127.0.0.1:8090/dashboard.php
   - View statistics, recent submissions, charts
   - Should show 1 submission from test

## Usage Examples

### Test Legitimate Submission

1. Go to http://127.0.0.1:8090/index.php
2. Fill form normally:
   - Name: John Doe
   - Email: john@example.com
   - Subject: Test
   - Message: This is a legitimate test message
3. Wait 3 seconds
4. Submit
5. Check dashboard → Should show as LOW risk

### Test Bot Detection

**Method 1: Using curl**
```bash
curl -X POST http://127.0.0.1:8090/submit.php \
  -d "name=Bot&email=bot@test.com&subject=spam&message=spam&website_url=http://spam.com"
```

Expected response:
```json
{"success":false,"message":"Submission blocked due to security concerns.","submission_id":2}
```

**Method 2: Using Python Bot Simulator**
```bash
# Install requests if needed
pip3 install requests

# Run simulator
python3 bot_simulator.py --target http://127.0.0.1:8090/submit.php --count 50

# Output will show:
# - Total submissions
# - Blocked vs accepted
# - Detection rate
```

### Run Pattern Extraction

```bash
# Manual run (processes last 5000 submissions)
php cron/run_extractor.php

# Expected output:
# Starting signature extraction...
# Extracted/updated 15 signatures
# Built 3 clusters
# Updated metrics
# Extraction completed in 0.89s
```

### Run Evaluation Report

```bash
php evaluate.php

# Generates comprehensive report showing:
# - Detection rate
# - Honeypot effectiveness
# - Rule effectiveness ranking
# - Performance metrics
# Saves to logs/evaluation_YYYY-MM-DD_HH-MM-SS.json
```

## Production Setup

### 1. Enable HTTPS (Required for production)

Edit `.htaccess`, uncomment:
```apache
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

Header set Strict-Transport-Security "max-age=31536000; includeSubDomains"
```

### 2. Configure Security Settings

Edit `config.php`:

```php
// Set specific allowed origins (NOT *)
'security' => [
    'allowed_origins' => ['https://yourdomain.com'],
    'max_payload_size' => 10240,
],

// Adjust rate limiting for your traffic
'rate_limit' => [
    'enabled' => true,
    'window_minutes' => 10,
    'max_submissions' => 5,  // Stricter for production
],

// Change honeypot field names periodically
'honeypot' => [
    'text_hidden' => 'user_website',    // Change these
    'semantic' => 'department_id',       // to prevent
    'time_trap' => 'csrf_token',        // reverse engineering
],
```

### 3. Set Up Cron Job

Add to crontab (`crontab -e`):

```bash
# Run extraction every hour
0 * * * * /usr/bin/php /path/to/HoneyComp/cron/run_extractor.php >> /path/to/HoneyComp/logs/extractor.log 2>&1

# Optional: Daily cleanup of old logs (keep 30 days)
0 2 * * * find /path/to/HoneyComp/logs -name "*.log" -mtime +30 -delete
```

### 4. Database Optimization (for high traffic)

```sql
-- Add additional indexes if needed
CREATE INDEX idx_submission_date_ip ON submissions(created_at, ip);
CREATE INDEX idx_score_risk_level ON submission_scores(risk_level, score);

-- Enable query cache (MySQL)
SET GLOBAL query_cache_size = 67108864;
SET GLOBAL query_cache_type = 1;
```

### 5. Monitoring

Create monitoring script:

```bash
#!/bin/bash
# monitor.sh - Check system health

# Check database connection
php -r "require 'db.php'; Database::getInstance()->query('SELECT 1');" || echo "DB ERROR"

# Check disk space
df -h | grep -E '9[0-9]%' && echo "DISK FULL WARNING"

# Check recent submissions
RECENT=$(mysql -u root -p form_trap_dm -se "SELECT COUNT(*) FROM submissions WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)")
echo "Submissions last hour: $RECENT"

# Check detection rate
php evaluate.php | grep "Detection Rate"
```

## Troubleshooting

### Error: "Database connection failed"

**Solution:**
```bash
# Check MySQL is running
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # Mac

# Test connection manually
mysql -u root -p -e "SELECT 1"

# Verify credentials in config.php
```

### Error: "Call to undefined function json_encode"

**Solution:**
```bash
# Install JSON extension
sudo apt-get install php-json  # Debian/Ubuntu
sudo yum install php-json      # CentOS/RHEL
brew install php               # Mac (includes JSON)
```

### Error: "Permission denied" for logs/

**Solution:**
```bash
chmod 755 logs/
# If using Apache:
sudo chown -R www-data:www-data logs/
```

### Dashboard shows "Failed to load"

**Solution:**
```bash
# Check API endpoint directly
curl http://127.0.0.1:8090/api_stats.php?action=stats

# Check browser console for errors (F12)
# Verify PHP error log
tail -f logs/php_errors.log
```

### High false positive rate (>10%)

**Solution:**
```php
// Adjust thresholds in config.php
'risk_thresholds' => [
    'medium' => 40,   // Increase to be less strict
    'high' => 70,
    'critical' => 120,
],

// OR disable aggressive rules
UPDATE rules SET enabled = 0 WHERE name = 'rapid_submission';
```

### Clustering too slow (>10s)

**Solution:**
```php
// Reduce processing load in config.php
'extraction' => [
    'min_occurrence' => 5,  // Increase to reduce signature count
    'cluster_similarity' => 0.85,  // More strict = fewer comparisons
],

// OR limit extractor to recent submissions
php cron/run_extractor.php  # Already limits to 5000
```

## Testing Checklist

Before going live:

- [ ] Database schema imported successfully
- [ ] `php test.php` shows all tests passing
- [ ] Contact form loads without errors
- [ ] Legitimate submission accepted (low risk)
- [ ] Bot simulation blocked (high risk)
- [ ] Dashboard displays statistics
- [ ] Charts render correctly
- [ ] Extraction runs without errors
- [ ] Evaluation generates report
- [ ] HTTPS enabled (production)
- [ ] Cron job scheduled
- [ ] Monitoring set up
- [ ] Logs directory writable
- [ ] Rate limiting tested
- [ ] False positive rate < 5%

## Support Resources

- **Full Documentation**: README.md (8000+ words)
- **Architecture Details**: PROJECT_SUMMARY.md
- **Development Timeline**: TIMELINE.md
- **Code Comments**: Inline PHPDoc in all files
- **Test Scripts**: test.php, bot_simulator.py

## Quick Command Reference

```bash
# Start development server
php -S 127.0.0.1:8090

# Run tests
php test.php

# Run bot simulation
python3 bot_simulator.py --target http://127.0.0.1:8090/submit.php --count 50

# Manual extraction
php cron/run_extractor.php

# Generate evaluation report
php evaluate.php

# Check database status
mysql -u root -p form_trap_dm -e "SELECT COUNT(*) FROM submissions"

# View recent logs
tail -f logs/extractor.log

# Backup database
mysqldump -u root -p form_trap_dm > backup_$(date +%Y%m%d).sql
```

## What to Do Next

### For Learning/Research:
1. Read through `README.md` for full understanding
2. Review source code (start with `submit.php` → `logger.php` → `scorer.php`)
3. Run bot simulator and analyze results
4. Modify rules in database and test effects
5. Generate evaluation report and analyze metrics

### For Production:
1. Complete production setup steps above
2. Test with real traffic for 1 week
3. Review dashboard daily
4. Adjust rule weights based on false positives
5. Document any custom rules added

### For Development:
1. Set up git repository
2. Implement admin panel for manual verification
3. Add unit tests with PHPUnit
4. Optimize clustering algorithm
5. Add export to STIX format

---

**System is now ready to use! Start with the contact form and explore the dashboard.**

🛡️ **Secure by design. Rules you can read, plus a small text model mined from real submissions.**
