#!/usr/bin/env python3
"""
Excel Data Importer - Import spam contact form responses from Excel to honeypot system
Reads spam data from "./dataset/Contact Form (Responses).xlsx" sheet "SpamCleaned" and submits via POST
Uses URL-honeypot column to trigger honeypot traps and test the spam detection system

Usage:
    python excel_importer.py --excel "./dataset/Contact Form (Responses).xlsx" --target http://localhost:8000/submit.php
"""

import pandas as pd
import requests
import time
import random
import argparse
from datetime import datetime
import os

class ExcelDataImporter:
    def __init__(self, excel_file, target_url, delay=1.0, sheet_name='SpamCleaned'):
        self.excel_file = excel_file
        self.target_url = target_url
        self.delay = delay
        self.sheet_name = sheet_name
        self.results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }

    def log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] {message}")

    def process_name_field(self, row):
        """
        Process name field according to requirements:
        1. If full name exists, use it
        2. If not, try to join first, middle, last name with proper spacing
        3. If none exist, mark as missing
        """
        # Check for full name first (comprehensive list of possible column names)
        full_name = self.get_field_value(row, [
            'full_name', 'Full Name', 'name', 'Name', 'fullname', 'FullName',
            'full name', 'contact_name', 'Contact Name', 'person_name', 'Person Name'
        ])
        
        # Check if full name has meaningful content (not 'None', 'null', empty, etc.)
        if full_name and str(full_name).strip() and str(full_name).strip().lower() not in ['none', 'null', 'n/a', 'na', '']:
            return str(full_name).strip()

        # Try to construct from first/middle/last name with comprehensive column name checking
        first_name = self.get_field_value(row, [
            'first_name', 'First Name', 'firstname', 'FirstName', 'first name',
            'First name', 'given_name', 'Given Name', 'givenname', 'GivenName'
        ])
        middle_name = self.get_field_value(row, [
            'middle_name', 'Middle Name', 'middlename', 'MiddleName', 'middle name',
            'Middle name', 'mMiddle name', 'middle_initial', 'Middle Initial', 'mi', 'MI'
        ])
        last_name = self.get_field_value(row, [
            'last_name', 'Last Name', 'lastname', 'LastName', 'last name',
            'Last name', 'surname', 'Surname', 'family_name', 'Family Name', 'familyname', 'FamilyName'
        ])

        # Build name parts, ensuring proper spacing
        name_parts = []
        if first_name and str(first_name).strip():
            name_parts.append(str(first_name).strip())
        if middle_name and str(middle_name).strip():
            name_parts.append(str(middle_name).strip())
        if last_name and str(last_name).strip():
            name_parts.append(str(last_name).strip())

        # Only return concatenated name if we have at least one part
        if name_parts:
            return ' '.join(name_parts)

        # Only mark as missing if truly no name data exists
        return 'name_field_missing'

    def get_field_value(self, row, possible_names):
        """Get field value from row, checking multiple possible column names (case-insensitive)"""
        # Create a case-insensitive mapping of column names
        column_map = {str(col).lower().strip(): col for col in row.index}

        for name in possible_names:
            # Try exact match first
            if name in row.index and pd.notna(row[name]) and str(row[name]).strip():
                return str(row[name]).strip()

            # Try case-insensitive match
            name_lower = str(name).lower().strip()
            if name_lower in column_map and pd.notna(row[column_map[name_lower]]) and str(row[column_map[name_lower]]).strip():
                return str(row[column_map[name_lower]]).strip()

        return None

    def process_field(self, row, field_name, possible_names):
        """Process a field with missing field handling"""
        value = self.get_field_value(row, possible_names)
        if value:
            return value
        return f"{field_name}_field_missing"

    def prepare_form_data(self, row, index):
        """Prepare form data from Excel row"""
        # Process name field specially
        name = self.process_name_field(row)

        # Process other required fields
        email = self.process_field(row, 'email', ['email', 'Email', 'email_address', 'Email Address'])
        subject = self.process_field(row, 'subject', ['subject', 'Subject', 'topic', 'Topic'])
        message = self.process_field(row, 'message', ['message', 'Message', 'comments', 'Comments', 'body', 'Body'])
        # Handle encoding issues
        try:
            message = message.encode('utf-8').decode('utf-8')
        except:
            message = "Message with encoding issues"

        # Add timing data (simulate bot-like behavior - very fast)
        current_time = int(time.time() * 1000)
        render_time = current_time - random.randint(100, 500)  # Very fast (0.1-0.5 seconds)
        security_token = f"tk_{random.randint(100000, 999999)}_{random.randint(100000, 999999)}"

        form_data = {
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
            'form_render_time': render_time,
            'security_token': security_token
        }

        # Add honeypot fields - USE THE URL COLUMN TO TRIGGER HONEYPOT!
        url_honeypot = self.get_field_value(row, ['url-honeypot', 'URL-honeypot', 'url', 'URL'])
        if url_honeypot and str(url_honeypot).strip():
            form_data['website_url'] = str(url_honeypot).strip()
        else:
            form_data['website_url'] = ''  # Fallback if no URL

        # Sometimes also fill company_code to trigger additional honeypot
        if random.random() < 0.3:  # 30% chance
            form_data['company_code'] = f"COMP{random.randint(1000, 9999)}"
        else:
            form_data['company_code'] = ''

        return form_data

    def submit_form_data(self, form_data, row_index):
        """Submit form data via POST request"""
        try:
            response = requests.post(self.target_url, data=form_data, timeout=10)
            self.results['total'] += 1

            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get('success'):
                        self.results['successful'] += 1
                        status = "SUCCESS"
                        self.log(f"Row {row_index + 1}: {status} - {result.get('message', 'OK')}")
                    else:
                        self.results['failed'] += 1
                        status = "BLOCKED"
                        self.log(f"Row {row_index + 1}: {status} - {result.get('message', 'Blocked')}")
                except ValueError:
                    self.results['failed'] += 1
                    self.log(f"Row {row_index + 1}: ERROR - Invalid JSON response")
                    self.results['errors'].append(f"Row {row_index + 1}: Invalid JSON response")
            else:
                self.results['failed'] += 1
                self.log(f"Row {row_index + 1}: HTTP {response.status_code}")
                self.results['errors'].append(f"Row {row_index + 1}: HTTP {response.status_code}")

        except Exception as e:
            self.results['failed'] += 1
            error_msg = f"Row {row_index + 1}: ERROR - {str(e)}"
            self.log(error_msg)
            self.results['errors'].append(error_msg)

    def import_data(self):
        """Main import function"""
        if not os.path.exists(self.excel_file):
            self.log(f"ERROR: Excel file '{self.excel_file}' not found!")
            return False

        try:
            # Read Excel file
            self.log(f"Reading Excel file: {self.excel_file}")
            df = pd.read_excel(self.excel_file, sheet_name=self.sheet_name)

            self.log(f"Found {len(df)} rows in '{self.sheet_name}' sheet")
            self.log("Column names found:")
            for col in df.columns:
                self.log(f"  - {col}")

            print("\n" + "=" * 80)
            self.log("STARTING DATA IMPORT")
            print("=" * 80)

            # Process each row
            for index, row in df.iterrows():
                form_data = self.prepare_form_data(row, index)

                self.log(f"\nProcessing row {index + 1}/{len(df)}:")
                self.log(f"  Name: {form_data['name']}")
                self.log(f"  Email: {form_data['email']}")
                self.log(f"  Subject: {form_data['subject']}")
                self.log(f"  Message: {form_data['message'][:50]}...")
                if form_data['website_url']:
                    self.log(f"  🚨 HONEYPOT TRIGGER: URL = {form_data['website_url']}")
                if form_data['company_code']:
                    self.log(f"  🚨 HONEYPOT TRIGGER: Company Code = {form_data['company_code']}")

                self.submit_form_data(form_data, index)

                # Delay between submissions
                if self.delay > 0:
                    time.sleep(self.delay)

            # Print final results
            self.print_results()
            return True

        except Exception as e:
            self.log(f"ERROR reading Excel file: {str(e)}")
            return False

    def print_results(self):
        """Print final import results"""
        print("\n" + "=" * 80)
        self.log("IMPORT COMPLETE")
        print("=" * 80)
        print(f"Total rows processed: {self.results['total']}")
        print(f"Successfully submitted: {self.results['successful']} ({self.results['successful']/max(1,self.results['total'])*100:.1f}%)")
        print(f"Failed/Blocked: {self.results['failed']} ({self.results['failed']/max(1,self.results['total'])*100:.1f}%)")

        if self.results['errors']:
            print(f"\nErrors encountered ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(self.results['errors']) > 10:
                print(f"  ... and {len(self.results['errors']) - 10} more errors")

        print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description='Import contact form data from Excel to honeypot system')
    parser.add_argument('--excel', default='./dataset/Contact Form (Responses).xlsx',
                       help='Path to Excel file')
    parser.add_argument('--target', default='http://localhost:8000/submit.php',
                       help='Target URL for form submission')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between submissions in seconds')
    parser.add_argument('--sheet', default='SpamCleaned',
                       help='Excel sheet name to read from')

    args = parser.parse_args()

    # Check if required packages are installed
    try:
        import pandas as pd
        import requests
    except ImportError as e:
        print(f"ERROR: Missing required packages. Please install: pip install pandas requests openpyxl")
        print(f"Import error: {e}")
        return

    importer = ExcelDataImporter(args.excel, args.target, args.delay, args.sheet)
    success = importer.import_data()

    if not success:
        exit(1)

if __name__ == '__main__':
    main()