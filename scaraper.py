import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def _clean_price(text):
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text)
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def scrape_flipkart(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    price_el = soup.select_one("div._30jeq3") or soup.select_one("div.Nx9bqj")
    title_el = soup.select_one("span.B_NuCI") or soup.select_one("span.VU-ZEz")

    price = _clean_price(price_el.get_text()) if price_el else None
    title = title_el.get_text(strip=True) if title_el else url

    if price is None:
        return None
    return {"title": title, "price": price}


def scrape_amazon(url):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    price_el = (
        soup.select_one("span.a-price-whole")
        or soup.select_one("#priceblock_ourprice")
        or soup.select_one("#priceblock_dealprice")
    )
    title_el = soup.select_one("#productTitle")

    price = _clean_price(price_el.get_text()) if price_el else None
    title = title_el.get_text(strip=True) if title_el else url

    if price is None:
        return None
    return {"title": title, "price": price}


def scrape_product(url):
    if "flipkart.com" in url:
        return scrape_flipkart(url)
    elif "amazon." in url:
        return scrape_amazon(url)
    else:
        raise ValueError("Only flipkart.com and amazon.* URLs are supported")
