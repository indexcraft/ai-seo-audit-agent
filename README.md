# AI SEO Audit Agent

Runs the kind of full-site audit a small SEO team would produce — technical SEO, content quality, and GEO/AI-search readiness — in one command. Plug in your own OpenAI or Anthropic API key and it also writes an LLM-generated executive summary and prioritized fix list, the way a senior consultant would frame the findings for a non-technical stakeholder.

**The deterministic core works with zero API keys.** Title/meta/heading/image/link/readability/structured-data checks, AI crawler access auditing, and llms.txt detection all run without any LLM. The API key only unlocks the narrative layer on top — this tool doesn't ask you to trust an LLM's judgment for anything it can measure directly.

Output: one polished **HTML dashboard report** + two CSVs (`pages.csv`, `issues.csv`).

---

## What it checks

**Per page (technical):** title length, meta description length, canonical tag, indexability (noindex), viewport/mobile meta, H1 count and heading hierarchy, image alt-text coverage, internal/external link counts.

**Per page (content):** word count, Flesch reading ease + grade level (via `textstat`), thin-content flagging.

**Per page (GEO):** structured data (JSON-LD) presence and types found.

**Site-level:** robots.txt audited against 19 known AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, and more) — distinguishing *training* bot access (a data-licensing decision) from *search/retrieval* bot access (which has an immediate effect on whether you're cited in AI answers today). Also checks for `llms.txt`.

**With an API key:** an LLM-written executive summary synthesizing patterns across all pages into a prioritized fix list, and (optional) per-page content-gap analysis against a target keyword.

---

## 1. What you need

- **Python 3.10+**
- **Optional:** an OpenAI or Anthropic API key, only needed for the narrative summary layer.

```bash
python3 --version
```

---

## 2. Setup

```bash
cd ai-seo-audit-agent
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Open .env and paste in ONE of: OPENAI_API_KEY or ANTHROPIC_API_KEY
# (both are optional — skip this step entirely to run the deterministic-only audit)
```

---

## 3. Run it

```bash
python run_audit.py --domain https://indexcraft.in --sitemap https://indexcraft.in/sitemap.xml
```

Common options:

| Flag | Purpose |
|---|---|
| `--sitemap` | Auto-discover pages (handles sitemap-index files too) |
| `--urls` | Explicit list of URLs instead of/alongside a sitemap |
| `--max-pages` | Safety cap on how many pages get crawled (default 20) |
| `--target-keyword` | Enables LLM content-gap analysis per page (needs an API key) |
| `--delay` | Seconds between page fetches (default 0.5 — be polite to your own server) |
| `--output-dir` | Where reports land (default `reports/`) |

Example with everything on:

```bash
python run_audit.py \
  --domain https://indexcraft.in \
  --sitemap https://indexcraft.in/sitemap.xml \
  --max-pages 15 \
  --target-keyword "technical SEO audit"
```

---

## 4. Verifying it works

```bash
python smoke_test.py
```

Runs 9 checks (fully mocked, no real network or API calls) covering on-page analysis on both a fully-optimized and a fully-broken fixture page, scoring correctness, AI crawler visibility scoring, llms.txt quick-validation, LLM provider auto-detection, mocked executive summary generation, and full report/CSV output. See `sample_output/` for what a real report looks like.

---

## 5. How scoring works

Three independent 0-100 scores, so a report can say "your technical SEO is solid but you're invisible to AI crawlers" instead of hiding that behind one vague number:

- **Technical** — title/meta/canonical/indexability/mobile/headings/images/links, error issues cost more than warnings
- **Content** — word count + readability (very difficult-to-read text loses points even without a hard error)
- **GEO** — structured data coverage blended with the site-wide AI crawler visibility score (weighted 60/40) at the site level; `llms.txt` presence adds a small bonus

Overall score = 40% technical + 30% content + 30% GEO.

---

## 6. A real bug this caught during development

The on-page analyzer originally stripped `<script>` tags (to get clean body text for readability scoring) *before* extracting JSON-LD structured data — which lives inside `<script type="application/ld+json">` tags. Every page silently reported zero structured data regardless of what was actually on it. Caught by testing against a fixture with real JSON-LD and getting an unexpected `False`; fixed by extracting structured data first, then stripping scripts for the text pass. `smoke_test.py` has a permanent regression comment marking this.

---

## Project structure

```
ai-seo-audit-agent/
├── run_audit.py                    # CLI entry point
├── smoke_test.py                    # 9 automated checks, fully mocked
├── requirements.txt
├── .env.example                     # copy to .env, add an API key (optional)
├── seo_agent/
│   ├── crawler.py                     # page fetching, sitemap + robots.txt discovery
│   ├── onpage_analyzer.py              # per-page technical/content/GEO checks
│   ├── ai_crawler_audit.py             # robots.txt vs 19 known AI bots
│   ├── bot_database.py                 # the AI crawler reference data
│   ├── llms_txt_checker.py             # lightweight llms.txt presence check
│   ├── llm_analyst.py                  # pluggable OpenAI/Anthropic narrative layer
│   ├── scoring.py                       # page + site 0-100 scoring
│   └── report_builder.py                # HTML dashboard + CSV writers
├── reports/                          # your audit outputs land here
└── sample_output/                    # example report + CSVs
```

---

## Notes on running this against sites you don't own

This only reads public pages, `robots.txt`, and `llms.txt` — the same things a search engine or AI crawler would read. It doesn't bypass paywalls, authentication, or robots.txt disallow rules. Still, be a reasonable citizen: use `--max-pages` and `--delay` sensibly, and prefer running it against your own sites or ones you have permission to audit.

---

## For your resume / portfolio

Suggested bullet:
> Built an open-source AI SEO Audit Agent combining technical SEO, content quality, and GEO/AI-crawler-visibility scoring into a single automated report, with an optional LLM layer (bring-your-own OpenAI/Anthropic key) generating consultant-style executive summaries and content-gap analysis.

The natural "flagship" piece alongside the AI Citation Tracker, Structured Data Bulk Auditor, and AI Crawler Access Toolkit — this one is the single-command version that ties all four together.
