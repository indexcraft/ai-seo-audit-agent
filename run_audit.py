#!/usr/bin/env python3
"""
AI SEO Audit Agent — full-site audit in one command.

    python run_audit.py --domain https://indexcraft.in --sitemap https://indexcraft.in/sitemap.xml

Combines technical SEO checks, content/readability scoring, structured
data detection, AI crawler access auditing, and llms.txt checking into
one HTML report + two CSVs. If OPENAI_API_KEY or ANTHROPIC_API_KEY is set
(directly or via a .env file), it also generates an LLM-written executive
summary and, optionally, per-page content-gap analysis against a target
keyword. Without a key, everything else still runs — the LLM layer is
an enhancement, not a requirement.
"""

import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

from seo_agent.crawler import fetch_html, fetch_robots_txt, fetch_sitemap_urls, crawl_pages, check_url_exists
from seo_agent.onpage_analyzer import analyze_page
from seo_agent.scoring import score_page, score_site
from seo_agent.ai_crawler_audit import audit_robots_txt, compute_visibility_score
from seo_agent.llms_txt_checker import quick_validate
from seo_agent.llm_analyst import get_configured_provider, generate_executive_summary, analyze_content_gap
from seo_agent.report_builder import build_html_report, write_pages_csv, write_issues_csv


def build_url_list(args) -> list:
    urls = list(args.urls) if args.urls else []
    if args.sitemap:
        print(f"[sitemap] discovering URLs from {args.sitemap}")
        try:
            sitemap_urls = fetch_sitemap_urls(args.sitemap)
            urls.extend(u for u in sitemap_urls if u not in urls)
            print(f"[sitemap] found {len(sitemap_urls)} URLs")
        except Exception as e:
            print(f"[sitemap] failed: {e}")
    if not urls:
        urls = [args.domain]
    if len(urls) > args.max_pages:
        print(f"[cap] {len(urls)} URLs found, capping to --max-pages={args.max_pages}")
        urls = urls[: args.max_pages]
    return urls


def run(args):
    os.makedirs(args.output_dir, exist_ok=True)

    urls = build_url_list(args)
    print(f"[crawl] fetching {len(urls)} page(s)")
    crawled = crawl_pages(urls, delay_seconds=args.delay)

    page_findings = []
    for page in crawled:
        if page["error"]:
            print(f"[warn] could not fetch {page['url']}: {page['error']}")
            continue
        page_findings.append(analyze_page(page["url"], page["html"]))

    if not page_findings:
        print("[error] no pages could be fetched — aborting")
        sys.exit(1)

    page_scores = [score_page(f) for f in page_findings]

    ai_results, ai_score = None, None
    try:
        robots_text = fetch_robots_txt(args.domain)
        ai_results = audit_robots_txt(robots_text)
        ai_score = compute_visibility_score(ai_results)
        print(f"[ai-crawlers] visibility score: {ai_score}/100")
    except Exception as e:
        print(f"[ai-crawlers] could not fetch robots.txt: {e}")

    llms_status = check_url_exists(args.domain, "llms.txt")
    llms_txt_exists = llms_status.get("exists", False)
    if llms_txt_exists:
        validation = quick_validate(llms_status["content"])
        print(f"[llms.txt] found — {validation['section_count']} sections, {validation['link_count']} links")
    else:
        print("[llms.txt] not found")

    site_summary = score_site(page_scores, ai_visibility_score=ai_score, llms_txt_exists=llms_txt_exists)
    print(f"\n[scores] overall={site_summary['overall_score']} technical={site_summary['technical_score']} content={site_summary['content_score']} geo={site_summary['geo_score']}")

    executive_summary = None
    content_gap_notes = {}
    provider = get_configured_provider()
    if provider:
        print(f"[llm] using {provider} for executive summary")
        all_issues = [{"severity": i["severity"], "check": i["check"], "url": f["url"], "message": i["message"]} for f in page_findings for i in f["issues"]]
        try:
            executive_summary = generate_executive_summary(site_summary, all_issues, target_keyword=args.target_keyword or "")
        except Exception as e:
            print(f"[llm] executive summary failed: {e}")

        if args.target_keyword:
            for page, finding in zip(crawled, page_findings):
                if page["error"]:
                    continue
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(page["html"], "html.parser")
                    for tag in soup(["script", "style", "nav", "footer", "header"]):
                        tag.decompose()
                    text = soup.get_text(separator=" ", strip=True)
                    content_gap_notes[finding["url"]] = analyze_content_gap(text, args.target_keyword)
                except Exception as e:
                    print(f"[llm] content gap analysis failed for {finding['url']}: {e}")
    else:
        print("[llm] no API key configured (OPENAI_API_KEY / ANTHROPIC_API_KEY) — skipping narrative summary")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_path = os.path.join(args.output_dir, f"report_{timestamp}.html")
    pages_csv_path = os.path.join(args.output_dir, f"pages_{timestamp}.csv")
    issues_csv_path = os.path.join(args.output_dir, f"issues_{timestamp}.csv")

    html_report = build_html_report(
        args.domain, site_summary, page_findings, page_scores,
        ai_crawler_results=ai_results, llms_txt_status=llms_status,
        executive_summary=executive_summary, content_gap_notes=content_gap_notes,
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    write_pages_csv(pages_csv_path, page_findings, page_scores)
    write_issues_csv(issues_csv_path, page_findings)

    print(f"\n=== DONE ===")
    print(f"HTML report: {html_path}")
    print(f"Pages CSV:   {pages_csv_path}")
    print(f"Issues CSV:  {issues_csv_path}")


def main():
    parser = argparse.ArgumentParser(description="AI SEO Audit Agent — full-site technical + content + GEO audit")
    parser.add_argument("--domain", required=True, help="e.g. https://indexcraft.in")
    parser.add_argument("--sitemap", help="Sitemap URL to discover pages from")
    parser.add_argument("--urls", nargs="*", help="Explicit URLs to crawl instead of/alongside sitemap")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between page fetches")
    parser.add_argument("--target-keyword", default="", help="Enables LLM content-gap analysis per page (requires an LLM API key)")
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    load_dotenv()
    main()
