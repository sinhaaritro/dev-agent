#!/usr/bin/env python3
"""auto-router engine - two-stage recall over .agents/MAP.md.

Stage 1 (mechanical, this script): tokenize the prompt (lowercase,
strip non-alphanumerics, drop stopwords) and score every row of
.agents/MAP.md twice - tag hits (prompt tokens overlapping the row's
tags, parsed from the Active Condition column) and description hits
(prompt tokens overlapping the description column, 4-character prefix
matching so "scratch" hits "scratchpad"). Rows print ranked: tag hits
first, then description hits, with a Match: column showing exactly
which tokens hit.

The output is candidates only and can never exclude: the agent must
still re-read the full MAP.md when candidates are thin and may select
a skill with zero literal hits if the prompt relates semantically to
its description (stage 2 is judgment, owned by the agent, not this
script). Zero hits prints an advisory message and exits 0.

Usage:
    python .agents/skills/auto-router/scripts/match_skills.py "<prompt>"

Exit codes: 0 = success (candidates printed, possibly none); 1 = fatal
error (MAP.md missing - run map-generator first).
"""

import re
import sys
from pathlib import Path

STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "during",
    "each",
    "few",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "here",
    "hers",
    "him",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "me",
    "might",
    "more",
    "most",
    "must",
    "my",
    "no",
    "not",
    "of",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "own",
    "please",
    "same",
    "shall",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "to",
    "too",
    "up",
    "us",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
}

ASCII_MAP = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2192": "->",  # right arrow
}


def sanitize_ascii(text: str) -> str:
    """Map common Unicode punctuation to ASCII and drop everything non-ASCII."""
    for src, dst in ASCII_MAP.items():
        text = text.replace(src, dst)
    return "".join(ch for ch in text if ord(ch) < 128)


def find_root() -> Path:
    """Walk up from the script location until AGENTS.md or AGENTS.md is found (repo root marker)."""
    current = Path(__file__).resolve().parent
    while True:
        if (current / "AGENTS.md").is_file() or (current / "AGENTS.md").is_file():
            return current
        parent = current.parent
        if parent == current:
            sys.exit(
                "error: AGENTS.md / AGENTS.md not found above "
                + str(Path(__file__).resolve())
            )
        current = parent


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stopwords.

    Splitting on any non-alphanumeric boundary means "docs/specs" and
    "draft-plan.md" yield ["docs", "specs"] and ["draft", "plan", "md"].
    """
    tokens = [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]
    return [t for t in tokens if t not in STOPWORDS]


def tokens_match(a: str, b: str) -> bool:
    """4-character prefix match; shorter tokens compare whole.

    "scratch" hits "scratchpad", "escalate" hits "escalation",
    "spec" hits "specs", "map" hits "maps". "temp" does not hit
    "timestamp" ("temp" vs "time" differ in the first 4 chars).
    """
    k = min(4, len(a), len(b))
    return k > 0 and a[:k] == b[:k]


def parse_map_rows(text: str) -> list[dict]:
    """Extract skill rows from the MAP.md Skills & Instructions table.

    Returns a list of {"name", "desc", "tags", "source"} - tags parsed
    from the Active Condition column when it uses the *Use when:* form;
    *Always active* rows carry no tags (auto-router's own row included).
    """
    rows: list[dict] = []
    in_skills = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("## ") and "Personas" not in line and "Skills" not in line:
            in_skills = False
        if line.startswith("## Skills & Instructions"):
            in_skills = True
            continue
        if not in_skills or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if (
            len(cells) < 4
            or cells[0].startswith(":---")
            or cells[0].lower().startswith("skill")
        ):
            continue
        name = re.sub(r"^\*\*|\*\*$", "", cells[0])
        desc = cells[1]
        cond = cells[2]
        source = cells[3] if len(cells) > 3 else ""
        tags = re.findall(r"`([^`]+)`", cond) if cond.startswith("*Use when:") else []
        rows.append(
            {
                "name": name,
                "desc": desc,
                "tags": [t for t in tags if t.strip()],
                "source": source,
            }
        )
    return rows


def score_row(row: dict, prompt_tokens: list[str]) -> dict:
    """Compute tag hits and description hits for one row.

    Match direction: each prompt token is tested against every tag
    token and every description token with 4-character prefix matching,
    so both "scratch" -> "scratchpad" and "scratchpad" -> "scratch"
    directions hit. Tokens are de-duplicated per hit set.
    """
    tag_hits: list[str] = []
    desc_hits: list[str] = []
    tag_tokens = [t for tag in row["tags"] for t in tokenize(tag)]
    desc_tokens = tokenize(row["desc"])
    for tok in prompt_tokens:
        if tok not in tag_hits and any(tokens_match(tok, t) for t in tag_tokens):
            tag_hits.append(tok)
        if tok not in desc_hits and any(tokens_match(tok, t) for t in desc_tokens):
            desc_hits.append(tok)
    return {"tag_hits": tag_hits, "desc_hits": desc_hits}


def format_match(tag_hits: list[str], desc_hits: list[str]) -> str:
    parts = []
    if tag_hits:
        parts.append("tag: " + ", ".join(tag_hits))
    if desc_hits:
        parts.append("desc: " + ", ".join(desc_hits))
    return "; ".join(parts)


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print('usage: match_skills.py "<prompt>"', file=sys.stderr)
        return 1
    prompt = " ".join(sys.argv[1:]).strip()

    root = find_root()
    map_file = root / ".agents" / "MAP.md"
    if not map_file.is_file():
        print("run map-generator first", file=sys.stderr)
        return 1

    try:
        map_text = map_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        print("error: cannot read " + str(map_file), file=sys.stderr)
        return 1

    prompt_tokens = tokenize(prompt)
    rows = parse_map_rows(map_text)

    scored = []
    for row in rows:
        hits = score_row(row, prompt_tokens)
        total = len(hits["tag_hits"]) + len(hits["desc_hits"])
        if total:
            scored.append(
                {
                    "name": row["name"],
                    "match": format_match(hits["tag_hits"], hits["desc_hits"]),
                    "has_tag": bool(hits["tag_hits"]),
                    "total": total,
                }
            )

    # Tag hits first, then description hits; ties break by hit count, then name.
    scored.sort(key=lambda s: (not s["has_tag"], -s["total"], s["name"].lower()))

    print("candidates for: " + sanitize_ascii(prompt))
    print("(candidates only - re-read .agents/MAP.md when candidates look thin)")
    if not scored:
        print("no candidates - review full index manually")
        return 0
    for idx, s in enumerate(scored, 1):
        print(f"{idx}. {s['name']:<20s} Match: {sanitize_ascii(s['match'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
