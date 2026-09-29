import asyncio
import json
import logging
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "http://quotes.toscrape.com"
OUTPUT_FILE = "artifacts/data/quotes_async.json"

async def fetch_page(client: httpx.AsyncClient, page_num: int):
    url = f"{BASE_URL}/page/{page_num}/"
    logger.info(f"Fetching page {page_num}: {url}")
    response = await client.get(url, timeout=10.0)
    response.raise_for_status()
    return response.text

def parse_quotes(html: str):
    soup = BeautifulSoup(html, "html.parser")
    quotes_data = []
    
    quote_elements = soup.select("div.quote")
    for q in quote_elements:
        text_el = q.select_one("span.text")
        author_el = q.select_one("small.author")
        author_link_el = q.select_one("span a[href*='/author/']")
        tag_els = q.select("div.tags a.tag")
        
        quote_text = text_el.get_text(strip=True) if text_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        author_url = urljoin(BASE_URL, author_link_el["href"]) if author_link_el and author_link_el.has_attr("href") else None
        tags = [t.get_text(strip=True) for t in tag_els]
        
        quotes_data.append({
            "quote": quote_text,
            "author": author,
            "author_url": author_url,
            "tags": tags
        })
    return quotes_data

async def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    pages = [1, 2]
    all_quotes = []

    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Scraper Bot)"}) as client:
        tasks = [fetch_page(client, page) for page in pages]
        html_results = await asyncio.gather(*tasks)
        
        for idx, html in enumerate(html_results, 1):
            page_quotes = parse_quotes(html)
            logger.info(f"Page {idx} extracted {len(page_quotes)} quotes.")
            all_quotes.extend(page_quotes)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)

    logger.info(f"Successfully saved {len(all_quotes)} quotes to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
