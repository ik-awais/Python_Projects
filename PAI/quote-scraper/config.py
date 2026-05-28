# config.py
import os
from dotenv import load_dotenv
load_dotenv()
# Scraping settings
BASE_URL = "http://quotes.toscrape.com"
PAGES_TO_SCRAPE = 10  # Change this to scrape more/less pages
REQUEST_DELAY = 1  # Seconds between requests (be respectful)
USER_AGENT = "Mozilla/5.0 (Educational Project; Contact: student@example.com)"
# Google Sheets settings (optional)
GOOGLE_SHEETS_ENABLED = False  # Set to True if you want to use Google Sheets
SPREADSHEET_NAME = "Scraped Quotes"
WORKSHEET_NAME = "Quotes Data"