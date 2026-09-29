import json
import os
import sys
import requests
from bs4 import BeautifulSoup

def scrape_quotes():
    base_url = "http://quotes.toscrape.com/page/{}/"
    output_path = "/workspaces/AAWS/artifacts/notebooks/generated/quotes_sample_result.json"
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    quotes_data = []
    
    for page in range(1, 4):
        url = base_url.format(page)
        print(f"Scraping page {page}: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        quote_elements = soup.select("div.quote")
        
        print(f"Found {len(quote_elements)} quotes on page {page}")
        
        for q in quote_elements:
            text_el = q.select_one("span.text")
            author_el = q.select_one("small.author")
            tag_els = q.select("div.tags a.tag")
            
            text = text_el.get_text(strip=True) if text_el else ""
            author = author_el.get_text(strip=True) if author_el else ""
            tags = [t.get_text(strip=True) for t in tag_els]
            
            quotes_data.append({
                "page": page,
                "text": text,
                "author": author,
                "tags": tags
            })
            
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quotes_data, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully saved {len(quotes_data)} quotes to {output_path}")

if __name__ == "__main__":
    scrape_quotes()
