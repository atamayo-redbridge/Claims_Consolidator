Redbridge Large Claims Analyzer

Install

pip install -r requirements.txt

Run

streamlit run app.py

Important

The application reads the data sheet, adds 00 to 9-digit Member IDs, sums all claims by Member ID, and applies contract rules.

Still pending in contracts.py:

FENWAL 2025 laser Member ID and amount.

The program does not guess missing contract values.
