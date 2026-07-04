"""
llms_txt_checker.py
---------------------
Lightweight check: does llms.txt exist, and does it have the two
structurally-important pieces (an H1 title and at least one section)?
For full spec validation (duplicate links, relative URLs, etc.) use the
dedicated ai-crawler-access-toolkit's llms_txt_validator instead — this
version just answers "is there a reasonable one here?" for scoring purposes.
"""

import re

H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
LINK_RE = re.compile(r"^[-*]\s*\[([^\]]+)\]\(([^)]+)\)", re.MULTILINE)


def quick_validate(content: str) -> dict:
    has_h1 = bool(H1_RE.search(content))
    sections = H2_RE.findall(content)
    links = LINK_RE.findall(content)
    return {
        "has_h1": has_h1,
        "section_count": len(sections),
        "link_count": len(links),
        "looks_valid": has_h1 and len(links) > 0,
    }
