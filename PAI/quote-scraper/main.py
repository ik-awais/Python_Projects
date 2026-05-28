# main.py
import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from config import BASE_URL, PAGES_TO_SCRAPE, REQUEST_DELAY, USER_AGENT, GOOGLE_SHEETS_ENABLED
import json
class QuoteScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        self.all_quotes = []      
    def scrape_page(self, page_num):
        """Scrape a single page of quotes"""
        if page_num == 1:
            url = f"{BASE_URL}/"
        else:
            url = f"{BASE_URL}/page/{page_num}/"      
        try:
            print(f"📥 Scraping page {page_num}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()        
            soup = BeautifulSoup(response.text, 'html.parser')
            quotes = soup.find_all('div', class_='quote')            
            if not quotes:
                return False  # No more pages           
            page_quotes = []
            for quote in quotes:
                quote_data = {
                    'text': quote.find('span', class_='text').text.strip('“”'),
                    'author': quote.find('small', class_='author').text,
                    'author_url': quote.find('a')['href'] if quote.find('a') else '',
                    'tags': [tag.text for tag in quote.find_all('a', class_='tag')],
                    'tag_count': len(quote.find_all('a', class_='tag')),
                    'scraped_at': datetime.now().isoformat()
                }
                page_quotes.append(quote_data)
                self.all_quotes.append(quote_data)            
            print(f"   ✅ Found {len(page_quotes)} quotes on page {page_num}")
            return True          
        except requests.RequestException as e:
            print(f"   ❌ Error scraping page {page_num}: {e}")
            return False
    def scrape_all_pages(self, max_pages=PAGES_TO_SCRAPE):
        """Scrape multiple pages until no more content or max pages reached"""
        print(f"\n🚀 Starting scraper for up to {max_pages} pages...\n")       
        for page in range(1, max_pages + 1):
            success = self.scrape_page(page)
            if not success:
                print(f"\n📖 No more content after page {page-1}")
                break            
            # Be respectful - delay between requests
            if page < max_pages:
                time.sleep(REQUEST_DELAY)        
        print(f"\n✨ Scraping complete! Total quotes: {len(self.all_quotes)}")
        return self.all_quotes   
    def get_statistics(self):
        """Generate statistics about scraped data"""
        if not self.all_quotes:
            return {}       
        df = pd.DataFrame(self.all_quotes)        
        stats = {
            'total_quotes': len(self.all_quotes),
            'unique_authors': df['author'].nunique(),
            'total_tags': df['tag_count'].sum(),
            'avg_tags_per_quote': df['tag_count'].mean(),
            'top_authors': df['author'].value_counts().head(5).to_dict(),
            'most_common_tags': self._get_top_tags(10)
        }        
        return stats    
    def _get_top_tags(self, n=10):
        """Get most common tags"""
        all_tags = []
        for quote in self.all_quotes:
            all_tags.extend(quote['tags'])       
        tag_counts = pd.Series(all_tags).value_counts()
        return tag_counts.head(n).to_dict()   
    def save_to_csv(self, filename='quotes_data.csv'):
        """Save scraped data to CSV file"""
        df = pd.DataFrame(self.all_quotes)
        # Convert tags list to string for CSV
        df['tags'] = df['tags'].apply(lambda x: ', '.join(x))      
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"💾 Data saved to {filename}")
        return filename   
    def save_to_json(self, filename='quotes_data.json'):
        """Save scraped data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_quotes, f, indent=2, ensure_ascii=False)
        print(f"💾 Data saved to {filename}")
    def display_sample(self, num=5):
        """Display sample of scraped quotes"""
        if not self.all_quotes:
            print("No data to display")
            return       
        print(f"\n📖 SAMPLE QUOTES (first {num}):\n")
        print("=" * 80)       
        for i, quote in enumerate(self.all_quotes[:num], 1):
            print(f"\nQuote #{i}:")
            print(f"  💬 \"{quote['text']}\"")
            print(f"  👤 Author: {quote['author']}")
            print(f"  🏷️  Tags: {', '.join(quote['tags'])}")
            print("-" * 80)
    def filter_quotes_by_author(self, author_name):
        """Filter quotes by author name"""
        filtered = [q for q in self.all_quotes if author_name.lower() in q['author'].lower()]
        print(f"\n🎯 Found {len(filtered)} quotes by {author_name}")
        return filtered
    def filter_quotes_by_tag(self, tag_name):
        """Filter quotes by tag"""
        filtered = [q for q in self.all_quotes if tag_name.lower() in [t.lower() for t in q['tags']]]
        print(f"\n🎯 Found {len(filtered)} quotes with tag '{tag_name}'")
        return filtered
    def search_quotes(self, keyword):
        """Search quotes containing keyword"""
        filtered = [q for q in self.all_quotes if keyword.lower() in q['text'].lower()]
        print(f"\n🔍 Found {len(filtered)} quotes containing '{keyword}'")
        return filtered
    def export_to_excel(self, filename='quotes_analysis.xlsx'):
        """Export with multiple sheets for analysis"""
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # All quotes
            df_all = pd.DataFrame(self.all_quotes)
            df_all['tags'] = df_all['tags'].apply(lambda x: ', '.join(x))
            df_all.to_excel(writer, sheet_name='All Quotes', index=False)
            # Author summary
            author_summary = df_all.groupby('author').size().reset_index(name='quote_count')
            author_summary = author_summary.sort_values('quote_count', ascending=False)
            author_summary.to_excel(writer, sheet_name='Author Summary', index=False)
            # Tag analysis
            all_tags = []
            for quote in self.all_quotes:
                all_tags.extend(quote['tags'])
            tag_summary = pd.Series(all_tags).value_counts().reset_index()
            tag_summary.columns = ['tag', 'count']
            tag_summary.to_excel(writer, sheet_name='Tag Analysis', index=False)           
        print(f"📊 Excel file saved: {filename}")
def main():
    # Initialize scraper
    scraper = QuoteScraper() 
    # Scrape quotes
    quotes = scraper.scrape_all_pages()
    if quotes:
        # Display sample
        scraper.display_sample(3)
        # Get statistics
        stats = scraper.get_statistics()
        print("\n📊 STATISTICS:")
        print("=" * 50)
        print(f"Total Quotes: {stats['total_quotes']}")
        print(f"Unique Authors: {stats['unique_authors']}")
        print(f"Total Tags: {stats['total_tags']}")
        print(f"Average Tags per Quote: {stats['avg_tags_per_quote']:.2f}")        
        print("\n🏆 Top 5 Authors:")
        for author, count in stats['top_authors'].items():
            print(f"  • {author}: {count} quotes")        
        print("\n🔥 Top 10 Tags:")
        for tag, count in list(stats['most_common_tags'].items())[:10]:
            print(f"  • {tag}: {count} times")       
        # Save data locally
        csv_file = scraper.save_to_csv()
        json_file = scraper.save_to_json()       
        # Optional: Export to Google Sheets
        if GOOGLE_SHEETS_ENABLED:
            try:
                from google_sheets import export_to_google_sheets
                export_to_google_sheets(scraper.all_quotes)
            except Exception as e:
                print(f"⚠️  Could not export to Google Sheets: {e}")       
        return scraper.all_quotes
    else:
        print("❌ No data scraped")
        return []
if __name__ == "__main__":
    # Run the scraper
    data = main()
    print("\n✅ Done! Check your CSV and JSON files.")