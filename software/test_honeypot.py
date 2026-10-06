#!/usr/bin/env python3
import pandas as pd
import requests
import time
import random

def get_field_value(row, possible_names):
    for name in possible_names:
        if name in row.index and pd.notna(row[name]) and str(row[name]).strip():
            return str(row[name]).strip()
    return None

df = pd.read_excel('./dataset/Contact Form (Responses).xlsx', sheet_name='SpamCleaned', nrows=3)

print('TESTING HONEYPOT TRIGGERING')
print('=' * 30)

for idx, row in df.iterrows():
    url_honeypot = get_field_value(row, ['url-honeypot', 'URL-honeypot', 'url', 'URL'])

    form_data = {
        'name': str(row.get('First name', '')) + ' ' + str(row.get('Last name', '')),
        'email': str(row.get('Email', '')),
        'subject': 'Spam Test',
        'message': 'Spam message test',
        'form_render_time': int(time.time() * 1000) - random.randint(100, 500),
        'security_token': f'tk_{random.randint(100000, 999999)}',
        'website_url': url_honeypot if url_honeypot else '',
        'company_code': ''
    }

    print(f'Row {idx+1}: website_url = {form_data["website_url"]}')

    try:
        response = requests.post('http://localhost:8000/submit.php', data=form_data, timeout=10)
        result = response.json()
        if result.get('success'):
            print(f'  -> SUBMITTED')
        else:
            print(f'  -> BLOCKED: honeypot triggered')
    except Exception as e:
        print(f'  -> ERROR: {str(e)}')

    time.sleep(0.5)

print('DONE')