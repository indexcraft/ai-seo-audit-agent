"""
smoke_test.py
-------------
Verifies the full agent WITHOUT hitting real websites or real LLM APIs
(all mocked) — run this any time after changing code, or right after
cloning the repo.

Usage: python smoke_test.py
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from seo_agent.onpage_analyzer import analyze_page
from seo_agent.scoring import score_page, score_site
from seo_agent.ai_crawler_audit import audit_robots_txt, compute_visibility_score
from seo_agent.llms_txt_checker import quick_validate
from seo_agent.llm_analyst import get_configured_provider, generate_executive_summary
from seo_agent.report_builder import build_html_report, write_pages_csv, write_issues_csv

GOOD_PARAGRAPH = "Technical SEO audits help websites perform better in search results. A good audit checks page speed, mobile friendliness, and structured data. " * 15

GOOD_HTML = f"""<html><head>
<title>Complete Guide to Technical SEO Auditing in 2026</title>
<meta name="description" content="Learn how to perform a comprehensive technical SEO audit covering crawlability, structured data, and AI search visibility.">
<link rel="canonical" href="https://example.com/guide">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Article","headline":"Test"}}</script>
</head><body>
<h1>Complete Guide to Technical SEO Auditing</h1>
<h2>Introduction</h2>
<p>{GOOD_PARAGRAPH}</p>
<img src="a.jpg" alt="Diagram of SEO audit process">
<a href="/page2">Internal link</a>
<a href="https://external.com">External link</a>
</body></html>"""

BAD_HTML = """<html><head><meta name="robots" content="noindex"></head>
<body><h1>Only H1</h1><h3>Skipped H2</h3><p>Too short.</p><img src="a.jpg"></body></html>"""


def main():
    checks = 0

    good = analyze_page("https://example.com/good", GOOD_HTML)
    assert good["issues"] == [], f"Expected zero issues on a fully valid page, got {good['issues']}"
    assert good["has_structured_data"] is True, "Structured data should be detected — regression guard for the script-tag-decompose-order bug"
    assert good["word_count"] > 300
    print("[PASS] fully-optimized page produces zero issues; structured data correctly detected")
    checks += 1

    bad = analyze_page("https://example.com/bad", BAD_HTML)
    bad_checks = {i["check"] for i in bad["issues"]}
    assert "title" in bad_checks and "meta_description" in bad_checks and "indexability" in bad_checks
    assert "headings" in bad_checks
    print(f"[PASS] broken page correctly flags {len(bad['issues'])} issues across title/meta/indexability/headings/etc.")
    checks += 1

    good_score = score_page(good)
    bad_score = score_page(bad)
    assert good_score["overall_score"] > bad_score["overall_score"]
    print(f"[PASS] scoring correctly ranks good page ({good_score['overall_score']}) above bad page ({bad_score['overall_score']})")
    checks += 1

    site_summary = score_site([good_score, bad_score], ai_visibility_score=80.0, llms_txt_exists=True)
    assert 0 <= site_summary["overall_score"] <= 100
    print(f"[PASS] site-level scoring aggregates correctly: overall={site_summary['overall_score']}")
    checks += 1

    selective_robots = "User-agent: GPTBot\nDisallow: /\nUser-agent: *\nAllow: /\n"
    ai_results = audit_robots_txt(selective_robots)
    ai_score = compute_visibility_score(ai_results)
    assert ai_score == 100.0, f"Blocking only a training bot should still score 100 on visibility, got {ai_score}"
    gptbot = next(r for r in ai_results if r["name"] == "GPTBot")
    assert gptbot["allowed"] is False
    print("[PASS] AI crawler audit correctly distinguishes training-bot blocks from visibility score")
    checks += 1

    valid_llms = "# Test\n\n> summary\n\n## Section\n- [link](https://x.com)\n"
    result = quick_validate(valid_llms)
    assert result["looks_valid"] is True
    invalid_llms = "just some text, no structure"
    result2 = quick_validate(invalid_llms)
    assert result2["looks_valid"] is False
    print("[PASS] llms.txt quick-validate correctly distinguishes valid from invalid content")
    checks += 1

    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SEO_AGENT_LLM_PROVIDER"):
        os.environ.pop(var, None)
    assert get_configured_provider() is None
    os.environ["ANTHROPIC_API_KEY"] = "fake"
    assert get_configured_provider() == "anthropic"
    print("[PASS] LLM provider auto-detection works correctly (none configured -> None, key present -> correct provider)")
    checks += 1

    with patch("seo_agent.llm_analyst.call_llm", return_value="Mocked summary.\n1. Fix X\n2. Fix Y"):
        summary = generate_executive_summary(site_summary, [{"severity": "error", "check": "title", "url": "https://x.com", "message": "Missing title"}])
    assert "Mocked summary" in summary
    print("[PASS] executive summary generation calls through correctly with a mocked LLM response")
    checks += 1

    os.makedirs("/tmp/seo_agent_smoke_test", exist_ok=True)
    html_report = build_html_report(
        "example.com", site_summary, [good, bad], [good_score, bad_score],
        ai_crawler_results=ai_results, llms_txt_status={"exists": False, "url": "https://example.com/llms.txt"},
        executive_summary="Test summary.",
    )
    assert "<html" in html_report and "score-card" in html_report and "Test summary." in html_report
    with open("/tmp/seo_agent_smoke_test/report.html", "w") as f:
        f.write(html_report)

    write_pages_csv("/tmp/seo_agent_smoke_test/pages.csv", [good, bad], [good_score, bad_score])
    write_issues_csv("/tmp/seo_agent_smoke_test/issues.csv", [good, bad])
    with open("/tmp/seo_agent_smoke_test/pages.csv") as f:
        assert "example.com/good" in f.read()
    print("[PASS] HTML report and both CSVs generate correctly with valid content")
    checks += 1

    print(f"\n=== ALL {checks} CHECKS PASSED ===")
    print("Verified: on-page analysis (good + broken pages), scoring (page and")
    print("site level), AI crawler visibility scoring, llms.txt quick-validation,")
    print("LLM provider auto-detection, mocked executive summary generation, and")
    print("full report output (HTML + CSVs).")
    print("\nNote: live network fetching and the real Anthropic API request format")
    print("were verified separately against real domains during development —")
    print("this smoke test covers the pure logic so it runs offline/in CI.")


if __name__ == "__main__":
    main()
