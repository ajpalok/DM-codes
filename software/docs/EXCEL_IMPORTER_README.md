> **Note.** The raw spreadsheet contains personal data and is kept in `../data/raw/`, outside this folder.
> Pass its path with `--excel`. To load the anonymized dataset instead, use `php cron/import_dataset.php`.

# Excel Data Importer

This Python script imports contact form responses from an Excel file and submits them to the honeypot system via POST requests, just like the bot simulator.

## Features

- **Smart Name Processing**: Handles missing full names by combining first/middle/last names
- **Missing Field Handling**: Marks missing fields with `{field}_field_missing`
- **POST Submission**: Submits data via HTTP POST (not direct database insertion)
- **Error Handling**: Comprehensive error reporting and logging
- **Configurable**: Command-line options for file paths, delays, etc.

## Requirements

```bash
pip install pandas requests openpyxl
```

## Usage

```bash
python excel_importer.py [options]
```

### Options

- `--excel FILE`: Path to Excel file (default: "Contact Form (Responses).xlsx")
- `--target URL`: Form submission URL (default: "http://localhost:8000/submit.php")
- `--delay SECONDS`: Delay between submissions (default: 1.0)
- `--sheet NAME`: Excel sheet name (default: "spamCleaned")

### Example

```bash
# Import from default file
python excel_importer.py

# Import with custom settings
python excel_importer.py --excel "my_responses.xlsx" --target "http://localhost:8000/submit.php" --delay 0.5
```

## Excel File Format

The script expects an Excel file with a sheet named "spamCleaned" containing columns like:

| Full Name | First Name | Middle Name | Last Name | Email | Subject | Message |
|-----------|------------|-------------|-----------|-------|---------|---------|
| John Doe  |            |             |           | john@example.com | Inquiry | Hello... |
|           | Jane       |             | Smith     | jane@test.com | Question | I have... |

### Name Field Logic

1. **Full Name Priority**: If "Full Name" column exists and has data, use it
2. **Name Construction**: If no full name, combine First + Middle + Last names
3. **Missing Marker**: If no name data available, use "name_field_missing"

### Field Processing

- **Missing Fields**: Marked as `{field}_field_missing`
- **Data Types**: All fields converted to strings
- **Empty Values**: Treated as missing

## Output Example

```
================================================================================
[13:30:01] STARTING DATA IMPORT
================================================================================

Processing row 1/5:
  Name: John Doe
  Email: john@example.com
  Subject: Inquiry
  Message: Hello, I am interested in your services....

Row 1: SUCCESS - Thank you! Your message has been received.

Processing row 2/5:
  Name: Jane Smith
  Email: jane@test.com
  Subject: Question
  Message: I have a question about pricing....

Row 2: BLOCKED - Submission blocked due to security concerns.

================================================================================
IMPORT COMPLETE
================================================================================
Total rows processed: 5
Successfully submitted: 3 (60.0%)
Failed/Blocked: 2 (40.0%)
================================================================================
```

## Integration with Honeypot System

The script submits data exactly like the bot simulator:

- Adds proper timing data (`form_render_time`, `security_token`)
- Leaves honeypot fields empty (simulating legitimate users)
- Uses random delays to avoid rate limiting
- Handles all the same validation and scoring as real form submissions

This means imported data goes through the same security checks and gets logged/scored just like regular form submissions.