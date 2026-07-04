"""
bot_database.py
----------------
Reference of AI crawler user-agent strings, current as of mid-2026.
See the sister project (ai-crawler-access-toolkit) for the full writeup
on categories and sourcing — this is the same data, kept here too so this
tool has zero dependency on that other repo.
"""

AI_CRAWLERS = [
    {"name": "GPTBot", "operator": "OpenAI", "category": "training"},
    {"name": "OAI-SearchBot", "operator": "OpenAI", "category": "search_retrieval"},
    {"name": "ChatGPT-User", "operator": "OpenAI", "category": "on_demand"},
    {"name": "ClaudeBot", "operator": "Anthropic", "category": "training"},
    {"name": "anthropic-ai", "operator": "Anthropic", "category": "training"},
    {"name": "Claude-SearchBot", "operator": "Anthropic", "category": "search_retrieval"},
    {"name": "Claude-User", "operator": "Anthropic", "category": "on_demand"},
    {"name": "PerplexityBot", "operator": "Perplexity", "category": "search_retrieval"},
    {"name": "Perplexity-User", "operator": "Perplexity", "category": "on_demand"},
    {"name": "Googlebot", "operator": "Google", "category": "search_retrieval"},
    {"name": "Google-Extended", "operator": "Google", "category": "opt_out_token"},
    {"name": "Bingbot", "operator": "Microsoft", "category": "search_retrieval"},
    {"name": "Amazonbot", "operator": "Amazon", "category": "training"},
    {"name": "Applebot-Extended", "operator": "Apple", "category": "opt_out_token"},
    {"name": "FacebookBot", "operator": "Meta", "category": "training"},
    {"name": "meta-externalagent", "operator": "Meta", "category": "training"},
    {"name": "Bytespider", "operator": "ByteDance", "category": "training"},
    {"name": "CCBot", "operator": "Common Crawl", "category": "training"},
    {"name": "DuckAssistBot", "operator": "DuckDuckGo", "category": "search_retrieval"},
]
