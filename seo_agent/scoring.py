"""
scoring.py
----------
Turns raw findings from onpage_analyzer.py (and the site-level AI crawler
audit) into 0-100 scores across three dimensions:

  - technical : title/meta/canonical/indexability/mobile/headings/images/links
  - content   : word count + readability
  - geo       : structured data + AI crawler access + llms.txt

Each dimension is scored independently so a report can say "your technical
SEO is fine but you're invisible to AI crawlers" instead of one vague
number that hides which team needs to fix what.
"""

TECHNICAL_CHECKS = {"title", "meta_description", "canonical", "indexability", "mobile", "headings", "links", "images"}
CONTENT_CHECKS = {"content"}
GEO_CHECKS = {"structured_data"}

SEVERITY_PENALTY = {"error": 15, "warning": 5}


def score_page(findings: dict) -> dict:
    technical_penalty = 0
    content_penalty = 0
    geo_penalty = 0

    for issue in findings["issues"]:
        penalty = SEVERITY_PENALTY.get(issue["severity"], 5)
        check = issue["check"]
        if check in GEO_CHECKS:
            geo_penalty += penalty
        elif check in CONTENT_CHECKS:
            content_penalty += penalty
        else:
            technical_penalty += penalty  # title/meta/canonical/indexability/mobile/headings/images/links

    technical_score = max(0, 100 - technical_penalty)
    content_score = max(0, 100 - content_penalty)
    geo_score = max(0, 100 - geo_penalty)

    # Readability nudges the content score: very hard-to-read text loses a
    # few points even without triggering a hard "issue".
    flesch = findings.get("readability_flesch_score")
    if flesch is not None:
        if flesch < 30:
            content_score = max(0, content_score - 10)
        elif flesch < 50:
            content_score = max(0, content_score - 5)

    overall = round((technical_score * 0.4) + (content_score * 0.3) + (geo_score * 0.3), 1)

    return {
        "technical_score": technical_score,
        "content_score": content_score,
        "geo_score": geo_score,
        "overall_score": overall,
    }


def score_site(page_scores: list, ai_visibility_score: float = None, llms_txt_exists: bool = False) -> dict:
    """
    page_scores: list of the per-page score dicts from score_page()
    ai_visibility_score: 0-100 from the robots.txt AI crawler audit, or None if not run
    """
    if not page_scores:
        return {"overall_score": 0, "technical_score": 0, "content_score": 0, "geo_score": 0}

    avg_technical = round(sum(p["technical_score"] for p in page_scores) / len(page_scores), 1)
    avg_content = round(sum(p["content_score"] for p in page_scores) / len(page_scores), 1)
    avg_page_geo = round(sum(p["geo_score"] for p in page_scores) / len(page_scores), 1)

    # Site-level GEO score blends per-page structured data coverage with the
    # domain-wide AI crawler access score, since both determine whether the
    # site can be cited by AI search tools at all.
    if ai_visibility_score is not None:
        site_geo = round((avg_page_geo * 0.6) + (ai_visibility_score * 0.4), 1)
    else:
        site_geo = avg_page_geo

    if llms_txt_exists:
        site_geo = min(100, site_geo + 5)

    overall = round((avg_technical * 0.4) + (avg_content * 0.3) + (site_geo * 0.3), 1)

    return {
        "technical_score": avg_technical,
        "content_score": avg_content,
        "geo_score": site_geo,
        "overall_score": overall,
        "ai_visibility_score": ai_visibility_score,
        "llms_txt_exists": llms_txt_exists,
    }
