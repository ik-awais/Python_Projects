# google_sheets.py - Updated for Python 3.12
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
def setup_google_sheets():
    """Setup Google Sheets connection with modern auth"""
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    # Load credentials from your downloaded JSON file
    creds = Credentials.from_service_account_file(
        'credentials.json',  # Your downloaded credentials file
        scopes=scope
    )
    return gspread.authorize(creds)
def export_to_google_sheets(quotes_data, spreadsheet_name="Scraped Quotes"):
    """Export quotes to Google Sheets"""
    try:
        df = pd.DataFrame(quotes_data)
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x))
        gc = setup_google_sheets()
        # Open or create spreadsheet
        try:
            sh = gc.open(spreadsheet_name)
        except gspread.SpreadsheetNotFound:
            sh = gc.create(spreadsheet_name)
        # Use first worksheet
        worksheet = sh.sheet1
        worksheet.clear()
        # Update with data
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        print(f"✅ Exported to Google Sheets: {spreadsheet_name}")
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")