"""
onpage_analyzer.py
-------------------
Runs the checks a technical SEO would run manually on a single page:
title/meta length, heading structure, image alt coverage, internal/external
link counts, readability, structured data presence, indexability signals.

Returns one flat dict per page — designed to be easy to turn into a CSV
row or feed straight into scoring.py.
"""

import json
import re
import textstat
from urllib.parse import urlparse
from bs4 import BeautifulSoup

TITLE_MIN, TITLE_MAX = 30, 60
META_DESC_MIN, META_DESC_MAX = 70, 160


def analyze_page(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(url).netloc

    findings = {"url": url, "issues": []}

    title_tag = soup.title.string.strip() if soup.title and soup.title.string else ""
    findings["title"] = title_tag
    findings["title_length"] = len(title_tag)
    if not title_tag:
        findings["issues"].append({"severity": "error", "check": "title", "message": "Missing <title> tag"})
    elif not (TITLE_MIN <= len(title_tag) <= TITLE_MAX):
        findings["issues"].append({"severity": "warning", "check": "title", "message": f"Title length {len(title_tag)} chars — recommended {TITLE_MIN}-{TITLE_MAX}"})

    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_desc_tag.get("content", "").strip() if meta_desc_tag else ""
    findings["meta_description"] = meta_desc
    findings["meta_description_length"] = len(meta_desc)
    if not meta_desc:
        findings["issues"].append({"severity": "error", "check": "meta_description", "message": "Missing meta description"})
    elif not (META_DESC_MIN <= len(meta_desc) <= META_DESC_MAX):
        findings["issues"].append({"severity": "warning", "check": "meta_description", "message": f"Meta description length {len(meta_desc)} chars — recommended {META_DESC_MIN}-{META_DESC_MAX}"})

    canonical_tag = soup.find("link", attrs={"rel": "canonical"})
    findings["canonical_url"] = canonical_tag.get("href", "") if canonical_tag else ""
    if not canonical_tag:
        findings["issues"].append({"severity": "warning", "check": "canonical", "message": "No canonical URL specified"})

    robots_tag = soup.find("meta", attrs={"name": "robots"})
    robots_content = robots_tag.get("content", "").lower() if robots_tag else ""
    findings["noindex"] = "noindex" in robots_content
    if findings["noindex"]:
        findings["issues"].append({"severity": "error", "check": "indexability", "message": "Page has noindex — will not appear in search or be eligible for AI citation"})

    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    findings["has_viewport_meta"] = viewport_tag is not None
    if not viewport_tag:
        findings["issues"].append({"severity": "warning", "check": "mobile", "message": "No viewport meta tag — page may not be mobile-optimized"})

    h1_tags = soup.find_all("h1")
    findings["h1_count"] = len(h1_tags)
    findings["h1_text"] = h1_tags[0].get_text(strip=True) if h1_tags else ""
    if len(h1_tags) == 0:
        findings["issues"].append({"severity": "error", "check": "headings", "message": "No H1 found"})
    elif len(h1_tags) > 1:
        findings["issues"].append({"severity": "warning", "check": "headings", "message": f"{len(h1_tags)} H1 tags found — should be exactly 1"})

    heading_levels = [int(h.name[1]) for h in soup.find_all(re.compile(r"^h[1-6]$"))]
    findings["heading_hierarchy_ok"] = _check_heading_hierarchy(heading_levels)
    if not findings["heading_hierarchy_ok"] and heading_levels:
        findings["issues"].append({"severity": "warning", "check": "headings", "message": "Heading levels skip a level (e.g. H1 straight to H3) — hurts content structure clarity for both users and AI parsers"})

    images = soup.find_all("img")
    images_missing_alt = [img for img in images if not img.get("alt", "").strip()]
    findings["images_total"] = len(images)
    findings["images_missing_alt"] = len(images_missing_alt)
    if images_missing_alt:
        findings["issues"].append({"severity": "warning", "check": "images", "message": f"{len(images_missing_alt)} of {len(images)} images missing alt text"})

    links = soup.find_all("a", href=True)
    internal, external = 0, 0
    for link in links:
        href = link["href"]
        if href.startswith(("http://", "https://")):
            if urlparse(href).netloc == domain:
                internal += 1
            else:
                external += 1
        elif href.startswith("/"):
            internal += 1
    findings["internal_links"] = internal
    findings["external_links"] = external
    if internal == 0:
        findings["issues"].append({"severity": "warning", "check": "links", "message": "No internal links found — hurts crawlability and topic clustering"})

    ld_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    schema_types = set()
    for script in ld_scripts:
        try:
            data = json.loads(script.string or "{}")
            nodes = data.get("@graph", [data]) if isinstance(data, dict) else data if isinstance(data, list) else [data]
            for node in nodes:
                if isinstance(node, dict) and "@type" in node:
                    t = node["@type"]
                    schema_types.add(t if isinstance(t, str) else t[0] if t else "Unknown")
        except (json.JSONDecodeError, AttributeError):
            findings["issues"].append({"severity": "warning", "check": "structured_data", "message": "A JSON-LD block on this page failed to parse"})
    findings["structured_data_types"] = sorted(schema_types)
    findings["has_structured_data"] = len(schema_types) > 0
    if not schema_types:
        findings["issues"].append({"severity": "warning", "check": "structured_data", "message": "No structured data (JSON-LD) found — reduces rich-result and AI-citation eligibility"})

    # NOTE: JSON-LD must be extracted BEFORE stripping <script> tags below —
    # this ordering bug (script tags decomposed first, JSON-LD read second,
    # silently returning zero schema types) was caught during testing.
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    body_text = soup.get_text(separator=" ", strip=True)
    word_count = len(body_text.split())
    findings["word_count"] = word_count

    if word_count >= 50:
        try:
            findings["readability_flesch_score"] = round(textstat.flesch_reading_ease(body_text), 1)
            findings["readability_grade_level"] = round(textstat.flesch_kincaid_grade(body_text), 1)
        except Exception:
            findings["readability_flesch_score"] = None
            findings["readability_grade_level"] = None
    else:
        findings["readability_flesch_score"] = None
        findings["readability_grade_level"] = None

    if word_count < 300:
        findings["issues"].append({"severity": "warning", "check": "content", "message": f"Thin content — only {word_count} words (300+ generally recommended for a standalone page)"})

    return findings


def _check_heading_hierarchy(levels: list) -> bool:
    """Flags a skipped level (e.g. H1 -> H3 with no H2 in between). A single
    missing H1 is caught separately; this only checks for gaps in sequence."""
    if not levels:
        return True
    seen = sorted(set(levels))
    for i in range(len(seen) - 1):
        if seen[i + 1] - seen[i] > 1:
            return False
    return True
