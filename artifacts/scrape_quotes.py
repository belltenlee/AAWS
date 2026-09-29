import json
import os
import requests
from bs4 import BeautifulSoup

def scrape_quotes():
    urls = [
        "http://quotes.toscrape.com/",
        "http://quotes.toscrape.com/page/2/"
    ]
    
    quotes_data = []
    
    for url in urls:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        quote_elements = soup.select("div.quote")
        for q in quote_elements:
            text_el = q.select_one("span.text")
            author_el = q.select_one("small.author")
            tag_els = q.select("div.tags a.tag")
            
            text = text_el.get_text(strip=True) if text_el else ""
            author = author_el.get_text(strip=True) if author_el else ""
            tags = [t.get_text(strip=True) for t in tag_els]
            
            quotes_data.append({
                "text": text,
                "author": author,
                "tags": tags
            })
            
    out_dir = "artifacts/data"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "quotes_multiagent.json")
    
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(quotes_data, f, ensure_ascii=False, indent=2)
        
    print(f"Scraped {len(quotes_data)} quotes successfully to {out_file}")

if __name__ == "__main__":
    scrape_quotes()
