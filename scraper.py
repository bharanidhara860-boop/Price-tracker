import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


class ScrapeError(Exception):
    pass


def _clean_price(text):
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", str(text))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _from_json_ld(soup):
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            items = data["@graph"]
        for item in items:
            if not isinstance(item, dict):
                continue
            offers = item.get("offers")
            if isinstance(offers, list) and offers:
                offers = offers[0]
            if isinstance(offers, dict):
                price = _clean_price(offers.get("price") or offers.get("lowPrice"))
                if price:
                    return {"title": item.get("name") or "", "price": price}
    return None


def _from_selectors(soup):
    candidates = [
        ("div._30jeq3", "span.B_NuCI"),
        ("div.Nx9bqj", "span.VU-ZEz"),
        ("span.a-price-whole", "#productTitle"),
        ("#priceblock_ourprice", "#productTitle"),
        ("#priceblock_dealprice", "#productTitle"),
    ]
    for price_sel, title_sel in candidates:
        el = soup.select_one(price_sel)
        if el:
            price = _clean_price(el.get_text())
            if price:
                t = soup.select_one(title_sel)
                return {"title": t.get_text(strip=True) if t else "", "price": price}
    return None


def scrape_product(url):
    if "flipkart.com" not in url and "amazon." not in url and "amzn." not in url:
        raise ValueError("Only flipkart.com and amazon.* URLs are supported")

    resp = requests.get(url, headers=HEADERS, timeout=20)
    soup = BeautifulSoup(resp.text, "html.parser")

    result = _from_json_ld(soup) or _from_selectors(soup)
    if result is None:
        title = soup.title.get_text(strip=True)[:80] if soup.title else "no title"
        host = urlparse(resp.url).netloc
        raise ScrapeError(
            f"Price not found. HTTP {resp.status_code} from {host}, page title: {title}"
        )

    if not result["title"]:
        og = soup.find("meta", property="og:title")
        result["title"] = og["content"] if og and og.get("content") else url
    return result
