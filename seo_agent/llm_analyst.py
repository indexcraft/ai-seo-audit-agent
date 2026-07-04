"""
llm_analyst.py
---------------
The "senior SEO strategist" layer. Everything else in this tool is
deterministic (title length, word count, robots.txt parsing). This module
is the one part that uses an LLM (your own API key — OpenAI or Anthropic)
to turn a pile of numbers into the kind of narrative summary and
prioritized recommendations a human analyst would write.

Fully optional: if no API key is configured, run_audit.py skips this layer
entirely and the report just omits the narrative sections. Everything else
still works — this tool doesn't require an LLM to be useful, it's an
enhancement layer on top of a fully deterministic core.
"""

import os
import requests

PROVIDER_ENV_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def get_configured_provider() -> str:
    """Auto-detects which provider to use based on which env var is set.
    Explicit config (SEO_AGENT_LLM_PROVIDER) wins if both are present."""
    explicit = os.environ.get("SEO_AGENT_LLM_PROVIDER", "").lower()
    if explicit in PROVIDER_ENV_KEYS and os.environ.get(PROVIDER_ENV_KEYS[explicit]):
        return explicit
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return None


def _query_openai(prompt: str, model: str, api_key: str) -> str:
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.4, "max_tokens": 1500},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _query_anthropic(prompt: str, model: str, api_key: str) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
        json={"model": model, "max_tokens": 1500, "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    resp.raise_for_status()
    blocks = [b["text"] for b in resp.json().get("content", []) if b.get("type") == "text"]
    return "\n".join(blocks)


PROVIDER_FUNCTIONS = {"openai": _query_openai, "anthropic": _query_anthropic}
DEFAULT_MODELS = {"openai": "gpt-4o-mini", "anthropic": "claude-3-5-haiku-20241022"}


def call_llm(prompt: str, provider: str = None, model: str = None) -> str:
    provider = provider or get_configured_provider()
    if not provider:
        raise RuntimeError("No LLM API key configured (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")
    api_key = os.environ.get(PROVIDER_ENV_KEYS[provider])
    model = model or DEFAULT_MODELS[provider]
    return PROVIDER_FUNCTIONS[provider](prompt, model, api_key)


def build_executive_summary_prompt(site_summary: dict, top_issues: list, target_keyword: str = "") -> str:
    keyword_line = f"The site's target keyword/topic focus is: {target_keyword}\n" if target_keyword else ""
    issues_text = "\n".join(f"- [{i['severity']}] {i['check']} on {i['url']}: {i['message']}" for i in top_issues[:25])

    return f"""You are a senior technical SEO consultant writing the executive summary section of an audit report for a client.

Site-level scores (0-100 scale):
- Technical SEO score: {site_summary['technical_score']}
- Content quality score: {site_summary['content_score']}
- GEO / AI-search-visibility score: {site_summary['geo_score']}
- Overall score: {site_summary['overall_score']}
- AI crawler visibility score: {site_summary.get('ai_visibility_score', 'not assessed')}
- llms.txt present: {site_summary.get('llms_txt_exists', False)}
{keyword_line}
Top issues found across the crawled pages:
{issues_text}

Write a concise executive summary (250-350 words) in plain business English, followed by a numbered list of the 5 highest-priority fixes ranked by likely impact. Do not repeat every issue verbatim — synthesize patterns (e.g. "12 of 15 pages are missing structured data" rather than listing each page). Write as if this will be read by a marketing director who is not a technical SEO expert, but keep it substantive and specific to what was actually found — do not give generic SEO advice unrelated to these findings."""


def build_content_gap_prompt(page_text: str, target_keyword: str) -> str:
    truncated = page_text[:3000]
    return f"""You are a content strategist. A page is targeting the keyword/topic: "{target_keyword}".

Here is the page's visible text content (truncated to first ~3000 characters):
---
{truncated}
---

In under 200 words: identify 3-5 specific subtopics or questions a thorough article on this keyword would be expected to cover that appear to be MISSING or under-addressed in this content. Be specific to this content, not generic. If the content already covers the topic thoroughly, say so briefly instead of inventing gaps."""


def generate_executive_summary(site_summary: dict, top_issues: list, target_keyword: str = "", provider: str = None) -> str:
    prompt = build_executive_summary_prompt(site_summary, top_issues, target_keyword)
    return call_llm(prompt, provider=provider)


def analyze_content_gap(page_text: str, target_keyword: str, provider: str = None) -> str:
    prompt = build_content_gap_prompt(page_text, target_keyword)
    return call_llm(prompt, provider=provider)
