"""
ai_crawler_audit.py
--------------------
Site-level check: parses robots.txt with Python's own urllib.robotparser
(standards-compliant group-matching, not hand-rolled regex) and scores
how visible the site is to AI search/retrieval bots specifically —
distinct from training-bot access, which is a separate strategic decision.
"""

from urllib.robotparser import RobotFileParser
from seo_agent.bot_database import AI_CRAWLERS


def audit_robots_txt(robots_txt_text: str, path: str = "/") -> list:
    parser = RobotFileParser()
    parser.parse(robots_txt_text.splitlines())

    results = []
    for bot in AI_CRAWLERS:
        allowed = parser.can_fetch(bot["name"], path)
        results.append({"name": bot["name"], "operator": bot["operator"], "category": bot["category"], "allowed": allowed})
    return results


def compute_visibility_score(audit_results: list) -> float:
    def pct_allowed(category):
        rows = [r for r in audit_results if r["category"] == category]
        if not rows:
            return 0
        return (sum(1 for r in rows if r["allowed"]) / len(rows)) * 100

    retrieval_pct = pct_allowed("search_retrieval")
    on_demand_pct = pct_allowed("on_demand")
    return round((retrieval_pct * 0.7) + (on_demand_pct * 0.3), 1)
