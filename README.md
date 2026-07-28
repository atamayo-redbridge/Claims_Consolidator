Redbridge Large Claims Analyzer

A Streamlit application that reads claim workbooks, consolidates claims by Member ID, and applies the corresponding Redbridge contract rules independently for each company and Group Number.

Install

pip install -r requirements.txt

Run

streamlit run app.py

How it works

The application:

Reads the data sheet from each uploaded workbook.

Detects the Group Number, Member ID, claim amount, member name, and benefit type.

Adds 00 to Member IDs that contain exactly 9 digits.

Recognizes MED, RX, DENT, and VISION claim files.

Treats DENTAL as DENT for compatibility.

Allows claim files from multiple companies to be uploaded together.

Separates claims by Group Number and analyzes each company independently.

Sums all claims by Group Number and Member ID.

Applies the configured contract deductible, maximum liability, lasers, exclusions, and covered benefits.

Allows an optional alternative deductible.

Generates a separate Excel report for each analyzed company.

Important

Each workbook must contain a sheet named:

data

The contract catalog is maintained in:

contracts.py

The program does not guess missing contract values. If a deductible, maximum liability, laser, exclusion, policy year, or contract is not configured, the application displays an error or warning instead of inventing a value.

Pending contract information

The following information is still pending in contracts.py:

FENWAL 2025 laser Member ID.

FENWAL 2025 laser deductible amount.

Project files

app.py
claims_reader.py
claims_engine.py
contracts.py
excel_report.py
requirements.txt
README.md
