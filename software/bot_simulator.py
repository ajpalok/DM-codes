#!/usr/bin/env python3
"""
Bot Simulator - Automated attack testing for honeypot system
Simulates various bot behaviors to test detection effectiveness

Usage:
    python bot_simulator.py --target http://localhost:8000/submit.php --count 50
"""

import requests
import time
import random
import argparse
from datetime import datetime

class BotSimulator:
    def __init__(self, target_url):
        self.target_url = target_url
        self.results = {
            'total': 0,
            'blocked': 0,
            'accepted': 0,
            'errors': 0
        }

    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

    def submit_form(self, data, scenario):
        """Submit form data and record result"""
        try:
            response = requests.post(self.target_url, data=data, timeout=10)
            self.results['total'] += 1
            
            result = response.json()
            
            if response.status_code == 403 or not result.get('success'):
                self.results['blocked'] += 1
                status = "BLOCKED"
            else:
                self.results['accepted'] += 1
                status = "ACCEPTED"
            
            self.log(f"{scenario}: {status} (HTTP {response.status_code})")
            return result
            
        except Exception as e:
            self.results['errors'] += 1
            self.log(f"{scenario}: ERROR - {str(e)}")
            return None

    def scenario_honeypot_text_hidden(self):
        """Bot fills hidden CSS field"""
        data = {
            'name': 'John Doe',
            'email': 'john@example.com',
            'subject': 'Inquiry',
            'message': 'Hello, I am interested in your services.',
            'website_url': 'http://2haas.com',  # HONEYPOT FIELD
            'form_render_time': int(time.time() * 1000) - 5000
        }
        self.submit_form(data, "Honeypot (text_hidden)")

    def scenario_honeypot_semantic(self):
        """Bot fills fake required field"""
        data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com',
            'subject': 'Question',
            'message': 'I have a question about pricing.',
            'company_code': 'ABC123',  # HONEYPOT FIELD
            'form_render_time': int(time.time() * 1000) - 4000
        }
        self.submit_form(data, "Honeypot (semantic)")

    def scenario_rapid_submission(self):
        """Bot submits form too quickly"""
        data = {
            'name': 'Fast Bot',
            'email': 'bot@fast.com',
            'subject': 'Speed Test',
            'message': 'Quick submission',
            'form_render_time': int(time.time() * 1000) - 500  # Only 500ms
        }
        self.submit_form(data, "Rapid submission")

    def scenario_sql_injection(self):
        """Bot attempts SQL injection"""
        data = {
            'name': "' OR 1=1 --",
            'email': 'hacker@evil.com',
            'subject': 'DROP TABLE users',
            'message': "'; DROP TABLE submissions; --",
            'form_render_time': int(time.time() * 1000) - 3000
        }
        self.submit_form(data, "SQL injection")

    def scenario_xss_attempt(self):
        """Bot attempts XSS"""
        data = {
            'name': '<script>alert("XSS")</script>',
            'email': 'xss@attacker.com',
            'subject': 'Test',
            'message': '<iframe src="http://evil.com"></iframe>',
            'form_render_time': int(time.time() * 1000) - 3000
        }
        self.submit_form(data, "XSS attempt")

    def scenario_repetitive_spam(self):
        """Bot sends repetitive spam content"""
        data = {
            'name': 'Spammer',
            'email': 'spam@spam.com',
            'subject': 'BUY NOW!!!',
            'message': 'BUY BUY BUY ' * 50,  # Repetitive pattern
            'form_render_time': int(time.time() * 1000) - 2000
        }
        self.submit_form(data, "Repetitive spam")

    def scenario_bot_user_agent(self):
        """Bot with obvious user agent"""
        # Note: Would need to modify requests session headers
        data = {
            'name': 'Bot User',
            'email': 'bot@crawler.com',
            'subject': 'Crawling',
            'message': 'Automated content',
            'form_render_time': int(time.time() * 1000) - 3000
        }
        # In real implementation, add headers={'User-Agent': 'Python-Bot/1.0'}
        self.submit_form(data, "Bot user-agent")

    def scenario_legitimate_user(self):
        """Simulate legitimate user submission"""
        names = ['Alice Johnson', 'Bob Williams', 'Carol Davis', 'David Miller']
        subjects = ['Question about services', 'Partnership inquiry', 'Technical support', 'General inquiry']
        
        time.sleep(random.uniform(3, 8))  # Human-like delay
        
        data = {
            'name': random.choice(names),
            'email': f'user{random.randint(1000,9999)}@example.com',
            'subject': random.choice(subjects),
            'message': 'Hello, I am reaching out regarding your services. Please contact me at your earliest convenience.',
            'form_render_time': int(time.time() * 1000) - random.randint(5000, 15000),
            'security_token': f'tk_{random.randint(100000, 999999)}'  # Time trap populated
        }
        self.submit_form(data, "Legitimate user")

    def scenario_rate_limit_attack(self):
        """Rapid submissions from same IP to trigger rate limiting"""
        for i in range(6):  # Send 6 in quick succession
            data = {
                'name': f'Rapid User {i}',
                'email': f'rapid{i}@test.com',
                'subject': 'Spam',
                'message': 'Rate limit test',
                'form_render_time': int(time.time() * 1000) - 3000
            }
            self.submit_form(data, f"Rate limit test ({i+1}/6)")
            time.sleep(0.5)

    def run_mixed_simulation(self, count=50):
        """Run mixed attack scenarios"""
        scenarios = [
            (self.scenario_honeypot_text_hidden, 10),
            (self.scenario_honeypot_semantic, 10),
            (self.scenario_rapid_submission, 8),
            (self.scenario_sql_injection, 5),
            (self.scenario_xss_attempt, 5),
            (self.scenario_repetitive_spam, 7),
            (self.scenario_legitimate_user, 5),
        ]

        self.log("Starting mixed bot simulation...")
        self.log(f"Target: {self.target_url}")
        self.log(f"Total scenarios: {count}")
        print("-" * 60)

        for scenario_func, scenario_count in scenarios:
            for i in range(min(scenario_count, count // len(scenarios))):
                scenario_func()
                time.sleep(random.uniform(0.5, 2))  # Random delay between submissions

        # Run rate limit attack at the end
        self.log("\nTesting rate limiting...")
        self.scenario_rate_limit_attack()

        # Print results
        print("\n" + "=" * 60)
        self.log("SIMULATION COMPLETE")
        print("=" * 60)
        print(f"Total submissions: {self.results['total']}")
        print(f"Blocked:          {self.results['blocked']} ({self.results['blocked']/max(1,self.results['total'])*100:.1f}%)")
        print(f"Accepted:         {self.results['accepted']} ({self.results['accepted']/max(1,self.results['total'])*100:.1f}%)")
        print(f"Errors:           {self.results['errors']}")
        print("=" * 60)
        
        detection_rate = self.results['blocked'] / max(1, self.results['total']) * 100
        if detection_rate >= 80:
            print("✓ Detection rate EXCELLENT (≥80%)")
        elif detection_rate >= 60:
            print("⚠ Detection rate GOOD (60-79%)")
        else:
            print("✗ Detection rate NEEDS IMPROVEMENT (<60%)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bot Simulator for Honeypot Testing')
    parser.add_argument('--target', default='http://localhost:8000/submit.php', 
                       help='Target URL for form submission')
    parser.add_argument('--count', type=int, default=50,
                       help='Number of submissions to simulate')
    
    args = parser.parse_args()
    
    simulator = BotSimulator(args.target)
    simulator.run_mixed_simulation(args.count)
