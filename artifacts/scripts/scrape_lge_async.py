import asyncio
import json
import logging
import os
import random
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.lge.co.kr"
CATEGORY_URL = f"{BASE_URL}/category/refrigerators"
OUTPUT_FILE = "artifacts/data/lge_async.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

async def fetch_category_products(client: httpx.AsyncClient):
    logger.info(f"Fetching category page: {CATEGORY_URL}")
    response = await client.get(CATEGORY_URL, headers=HEADERS, follow_redirects=True, timeout=15.0)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    product_links = soup.select("a[href*='/refrigerators/']")
    
    products = {}
    for a in product_links:
        href = a.get("href", "")
        clean_path = href.split("?")[0]
        # match paths like /refrigerators/t876mee1h1
        parts = [p for p in clean_path.split("/") if p]
        if len(parts) == 2 and parts[0] == "refrigerators":
            if clean_path not in products:
                # Extract any metadata visible in the card
                title_el = a.select_one(".product-card-title_headline")
                sku_el = a.select_one(".product-card-title_sku")
                benefit_price_el = a.select_one(".maximum_benefit_price .price")
                base_price_el = a.select_one(".base_price .current_price .price")
                discount_el = a.select_one(".discount_rate")
                
                sku_text = sku_el.get_text(strip=True).replace("모델명", "").strip() if sku_el else ""
                
                products[clean_path] = {
                    "path": clean_path,
                    "full_url": urljoin(BASE_URL, clean_path),
                    "card_title": title_el.get_text(strip=True) if title_el else "",
                    "sku": sku_text,
                    "benefit_price": benefit_price_el.get_text(strip=True) + "원" if benefit_price_el else None,
                    "base_price": base_price_el.get_text(strip=True) + "원" if base_price_el else None,
                    "discount_rate": discount_el.get_text(strip=True).replace("할인율", "").strip() if discount_el else None,
                }
    
    product_list = list(products.values())
    logger.info(f"Discovered {len(product_list)} refrigerator models from category page.")
    return product_list

async def fetch_product_detail(client: httpx.AsyncClient, product_meta: dict):
    url = product_meta["full_url"]
    logger.info(f"Fetching detail page: {url}")
    response = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=15.0)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    
    # Extract JSON-LD product data
    product_ld = None
    for script in soup.find_all("script", type="application/ld+json"):
        if script.string and '"Product"' in script.string:
            try:
                data = json.loads(script.string)
                if data.get("@type") == "Product":
                    product_ld = data
                    break
            except Exception as e:
                logger.warning(f"Error parsing JSON-LD: {e}")

    # Fallback to HTML elements if JSON-LD is missing
    model_name = product_meta.get("sku") or ""
    product_name = product_meta.get("card_title") or ""
    description = ""
    price = product_meta.get("base_price") or ""
    specs = {}
    image_url = ""
    canonical_url = str(response.url)

    if product_ld:
        model_name = product_ld.get("model") or product_ld.get("sku") or model_name
        product_name = product_ld.get("name") or product_name
        description = product_ld.get("description") or ""
        image_url = product_ld.get("image") or ""
        canonical_url = product_ld.get("url") or canonical_url
        
        offers = product_ld.get("offers", {})
        if isinstance(offers, dict) and "price" in offers:
            raw_price = offers.get("price")
            price = f"{int(raw_price):,}원" if str(raw_price).isdigit() else str(raw_price)

        additional_props = product_ld.get("additionalProperty", [])
        for prop in additional_props:
            if isinstance(prop, dict) and "name" in prop and "value" in prop:
                specs[prop["name"]] = prop["value"]

    # If specs is empty, extract from HTML description / badges
    if not specs:
        desc_spans = soup.select(".product-card-title_description em")
        if desc_spans:
            specs["요약_사양"] = ", ".join(span.get_text(strip=True) for span in desc_spans)

    result = {
        "model_name": model_name,
        "product_name": product_name,
        "price": price,
        "benefit_price": product_meta.get("benefit_price"),
        "discount_rate": product_meta.get("discount_rate"),
        "description": description,
        "specs": specs,
        "url": canonical_url,
        "image_url": image_url
    }
    return result

async def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        products = await fetch_category_products(client)
        if len(products) < 3:
            raise RuntimeError(f"Expected at least 3 models, but only found {len(products)}")
        
        # Pick 3 random models
        selected = random.sample(products, 3)
        logger.info(f"Selected 3 random models: {[p['sku'] or p['path'] for p in selected]}")
        
        tasks = [fetch_product_detail(client, p) for p in selected]
        results = await asyncio.gather(*tasks)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"Successfully collected {len(results)} refrigerator models to {OUTPUT_FILE}")
    for item in results:
        logger.info(f" - [{item['model_name']}] {item['product_name']} | {item['price']} (혜택가: {item['benefit_price']})")

if __name__ == "__main__":
    asyncio.run(main())
