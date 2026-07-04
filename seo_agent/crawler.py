"""
crawler.py
----------
Fetches pages and discovers URLs from a sitemap. Kept deliberately simple
(no JS rendering, no headless browser) — this reads the HTML your server
actually sends, which is also what most AI crawlers and many search bots see.
"""

import time
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

USER_AGENT = "AISEOAuditAgent/1.0 (+https://indexcraft.in)"


def fetch_html(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_robots_txt(domain: str, timeout: int = 20) -> str:
    url = urljoin(domain.rstrip("/") + "/", "robots.txt")
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def check_url_exists(domain: str, path: str, timeout: int = 20) -> dict:
    url = urljoin(domain.rstrip("/") + "/", path)
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        return {"exists": resp.status_code == 200, "url": url, "status_code": resp.status_code, "content": resp.text if resp.status_code == 200 else ""}
    except requests.RequestException as e:
        return {"exists": False, "url": url, "status_code": None, "content": "", "error": str(e)}


def fetch_sitemap_urls(sitemap_url: str, timeout: int = 20) -> list:
    resp = requests.get(sitemap_url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "xml")

    sub_sitemaps = [loc.text.strip() for loc in soup.select("sitemap > loc")]
    if sub_sitemaps:
        urls = []
        for sub in sub_sitemaps:
            urls.extend(fetch_sitemap_urls(sub, timeout=timeout))
        return urls

    return [loc.text.strip() for loc in soup.select("url > loc")]


def crawl_pages(urls: list, delay_seconds: float = 0.5) -> list:
    """
    Fetches each URL. Returns a list of {url, html, error} — errors are
    captured per-page rather than raised, so one broken page doesn't kill
    the whole audit run.
    """
    results = []
    for url in urls:
        try:
            html = fetch_html(url)
            results.append({"url": url, "html": html, "error": None})
        except Exception as e:
            results.append({"url": url, "html": "", "error": str(e)})
        time.sleep(delay_seconds)
    return results
