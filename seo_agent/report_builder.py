"""
report_builder.py
-------------------
Builds the final deliverables:
  - report.html      : a single-file, no-dependency HTML dashboard —
                        score gauges, per-page table, issue breakdown,
                        and the LLM executive summary if one was generated
  - pages.csv          : one row per crawled page with all metrics
  - issues.csv          : one row per individual issue found
"""

import csv
import html as html_module


def _score_color(score: float) -> str:
    if score >= 80:
        return "#22c55e"
    elif score >= 50:
        return "#f59e0b"
    return "#ef4444"


def _score_card(label: str, score) -> str:
    if score is None:
        return f'<div class="score-card"><div class="score-label">{label}</div><div class="score-value" style="color:#9ca3af">N/A</div></div>'
    color = _score_color(score)
    return f'''<div class="score-card">
        <div class="score-label">{label}</div>
        <div class="score-value" style="color:{color}">{score}</div>
    </div>'''


def build_html_report(domain: str, site_summary: dict, page_findings: list, page_scores: list,
                       ai_crawler_results: list = None, llms_txt_status: dict = None,
                       executive_summary: str = None, content_gap_notes: dict = None) -> str:
    """Returns the full HTML report as a string."""
    content_gap_notes = content_gap_notes or {}

    score_cards = "".join([
        _score_card("Overall", site_summary.get("overall_score")),
        _score_card("Technical", site_summary.get("technical_score")),
        _score_card("Content", site_summary.get("content_score")),
        _score_card("GEO / AI Visibility", site_summary.get("geo_score")),
    ])

    if executive_summary:
        formatted = html_module.escape(executive_summary).replace("\n", "<br>")
        exec_summary_html = f'''<section class="section">
            <h2>Executive Summary</h2>
            <div class="exec-summary">{formatted}</div>
        </section>'''
    else:
        exec_summary_html = '''<section class="section">
            <h2>Executive Summary</h2>
            <p class="muted">No LLM API key was configured for this run, so the narrative summary was skipped. Set OPENAI_API_KEY or ANTHROPIC_API_KEY to enable it — every other section below is fully deterministic and doesn't require one.</p>
        </section>'''

    page_rows = ""
    for finding, score in zip(page_findings, page_scores):
        url = html_module.escape(finding["url"])
        gap_note = content_gap_notes.get(finding["url"], "")
        gap_html = f'<div class="gap-note">{html_module.escape(gap_note)}</div>' if gap_note else ""
        page_rows += f'''<tr>
            <td><a href="{url}" target="_blank">{url}</a>{gap_html}</td>
            <td>{finding.get("word_count", "-")}</td>
            <td>{finding.get("title_length", "-")}</td>
            <td>{"Yes" if finding.get("has_structured_data") else "No"}</td>
            <td style="color:{_score_color(score['overall_score'])}">{score['overall_score']}</td>
        </tr>'''

    issues_by_severity = {"error": [], "warning": []}
    for finding in page_findings:
        for issue in finding["issues"]:
            issues_by_severity.setdefault(issue["severity"], []).append({**issue, "url": finding["url"]})

    issues_html = ""
    for severity in ["error", "warning"]:
        items = issues_by_severity.get(severity, [])
        if not items:
            continue
        badge_color = "#ef4444" if severity == "error" else "#f59e0b"
        issues_html += f'<h3><span class="badge" style="background:{badge_color}">{severity.upper()}</span> ({len(items)})</h3><ul class="issue-list">'
        for item in items[:50]:
            issues_html += f'<li><strong>{html_module.escape(item["check"])}</strong> — {html_module.escape(item["message"])} <span class="muted">({html_module.escape(item["url"])})</span></li>'
        issues_html += "</ul>"

    ai_crawler_html = ""
    if ai_crawler_results is not None:
        blocked = [b for b in ai_crawler_results if not b["allowed"] and b["category"] in ("search_retrieval", "on_demand")]
        rows = "".join(
            f'<tr><td>{b["name"]}</td><td>{b["operator"]}</td><td>{b["category"]}</td><td>{"✅ Allowed" if b["allowed"] else "🚫 Blocked"}</td></tr>'
            for b in ai_crawler_results
        )
        blocked_note = f'<p class="muted">{len(blocked)} search/retrieval or on-demand bot(s) currently blocked — this has an immediate effect on AI-answer citation eligibility.</p>' if blocked else '<p class="muted">All search/retrieval and on-demand AI bots are currently allowed.</p>'
        ai_crawler_html = f'''<section class="section">
            <h2>AI Crawler Access</h2>
            {blocked_note}
            <table><thead><tr><th>Bot</th><th>Operator</th><th>Category</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
        </section>'''

    llms_txt_html = ""
    if llms_txt_status is not None:
        status_text = f"Found at {llms_txt_status['url']}" if llms_txt_status.get("exists") else "Not found"
        llms_txt_html = f'<section class="section"><h2>llms.txt</h2><p>{status_text}</p></section>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SEO Audit Report — {html_module.escape(domain)}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f8fafc; color:#1e293b; margin:0; padding:40px 20px; }}
  .container {{ max-width: 960px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  .subtitle {{ color:#64748b; margin-bottom: 32px; }}
  .score-grid {{ display:flex; gap:16px; margin-bottom: 40px; flex-wrap: wrap; }}
  .score-card {{ background:white; border-radius:12px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); flex:1; min-width:140px; text-align:center; }}
  .score-label {{ font-size:13px; color:#64748b; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.05em; }}
  .score-value {{ font-size:36px; font-weight:700; }}
  .section {{ background:white; border-radius:12px; padding:28px; margin-bottom:24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
  .section h2 {{ margin-top:0; font-size:20px; }}
  table {{ width:100%; border-collapse: collapse; margin-top:16px; }}
  th, td {{ text-align:left; padding:10px 12px; border-bottom:1px solid #e2e8f0; font-size:14px; }}
  th {{ color:#64748b; font-weight:600; font-size:12px; text-transform:uppercase; }}
  .exec-summary {{ line-height:1.7; font-size:15px; }}
  .muted {{ color:#64748b; font-size:14px; }}
  .badge {{ color:white; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:600; }}
  .issue-list {{ font-size:14px; line-height:1.9; padding-left:20px; }}
  .gap-note {{ font-size:12px; color:#7c3aed; margin-top:4px; }}
  a {{ color:#2563eb; text-decoration:none; }}
</style>
</head>
<body>
<div class="container">
  <h1>SEO Audit Report</h1>
  <div class="subtitle">{html_module.escape(domain)} — {len(page_findings)} page(s) audited</div>

  <div class="score-grid">{score_cards}</div>

  {exec_summary_html}

  <section class="section">
    <h2>Page-by-Page Breakdown</h2>
    <table>
      <thead><tr><th>URL</th><th>Words</th><th>Title Length</th><th>Structured Data</th><th>Score</th></tr></thead>
      <tbody>{page_rows}</tbody>
    </table>
  </section>

  <section class="section">
    <h2>Issues Found</h2>
    {issues_html if issues_html else '<p class="muted">No issues found.</p>'}
  </section>

  {ai_crawler_html}
  {llms_txt_html}
</div>
</body>
</html>"""


def write_pages_csv(path: str, page_findings: list, page_scores: list):
    fieldnames = ["url", "title", "title_length", "meta_description_length", "word_count",
                  "readability_flesch_score", "h1_count", "images_missing_alt", "internal_links",
                  "external_links", "has_structured_data", "noindex", "overall_score",
                  "technical_score", "content_score", "geo_score"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for finding, score in zip(page_findings, page_scores):
            row = {k: finding.get(k, "") for k in fieldnames if k in finding}
            row["url"] = finding["url"]
            row.update({
                "overall_score": score["overall_score"],
                "technical_score": score["technical_score"],
                "content_score": score["content_score"],
                "geo_score": score["geo_score"],
            })
            writer.writerow(row)


def write_issues_csv(path: str, page_findings: list):
    fieldnames = ["url", "severity", "check", "message"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for finding in page_findings:
            for issue in finding["issues"]:
                writer.writerow({"url": finding["url"], "severity": issue["severity"], "check": issue["check"], "message": issue["message"]})
