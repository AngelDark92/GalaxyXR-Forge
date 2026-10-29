#!/usr/bin/env python
"""Turn an `add-repo` issue body into the JSON payload tools/add-repo.py reads.

Reads ISSUE_BODY (and ISSUE_NUMBER) from the environment. Prints JSON:
    {"repo": "https://github.com/owner/name", "group": "apps-samples",
     "about": null, "issue": 12}

Accepted body shapes, in order of preference:
    1. the site form / issue template headings:
           ### Repo URL
           https://github.com/owner/name
           ### Group
           apps-samples
           ### About            (optional)
           One short line.
    2. bare `repo:` / `group:` / `about:` lines.

News mode (`--news`), for the `add-news` issue template:
    python tools/issue-payload.py --news

Reads ISSUE_BODY, ISSUE_NUMBER and ISSUE_USER from the environment and prints:
    {"title": "...", "body": ["paragraph", ...], "summary": null,
     "kind": "community", "repo": null,
     "links": [{"label": "Link", "url": "https://..."}], "author": null,
     "date": "YYYY-MM-DD", "issue": 12}

Accepted headings (case-insensitive; a trailing `(optional)` is ignored):
    ### Title (or Headline)     required, max 120 chars
    ### News (or Body / Text)   required, blank line between paragraphs
    ### Summary                 optional, max 200 chars
    ### Category (or Kind)      optional: site, site update, release,
                                community, guide (default community)
    ### Related repo            optional, owner/name or a GitHub URL
    ### Link                    optional, `Label | https://url` or a bare URL
    ### Date                    optional, YYYY-MM-DD (default today)

Exit codes: 0 ok, 1 unparseable or invalid (message on stdout/stderr).
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog.json"

REPO_URL_RE = re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$")


def sections(body):
    """Map '### Heading' blocks to their text."""
    out = {}
    current = None
    for line in body.splitlines():
        m = re.match(r"^\s*#{2,4}\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            out.setdefault(current, [])
            continue
        if current is not None:
            out[current].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def first_url(text):
    m = re.search(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text or "")
    return m.group(0) if m else None


def main():
    body = os.environ.get("ISSUE_BODY", "")
    number = os.environ.get("ISSUE_NUMBER", "0")
    sec = sections(body)

    repo = first_url(sec.get("repo url") or body)
    if not repo:
        print("error: no GitHub repository URL found in the issue body", file=sys.stderr)
        return 1
    repo = repo.rstrip("/")
    if repo.endswith(".git"):
        repo = repo[:-4]
    m = REPO_URL_RE.match(repo)
    if not m:
        print(f"error: not a plain repository URL: {repo}", file=sys.stderr)
        return 1

    group = (sec.get("group") or "").strip().lower()
    if not group:
        for line in body.splitlines():
            hit = re.match(r"^\s*group\s*:\s*(\S+)\s*$", line, re.I)
            if hit:
                group = hit.group(1).lower()
                break

    groups = json.loads(CATALOG.read_text(encoding="utf-8"))["groups"]
    ids = [g["id"] for g in groups]
    if group not in ids:
        print(
            "error: group must be one of: " + ", ".join(ids),
            file=sys.stderr,
        )
        return 1

    about = (sec.get("about") or sec.get("notes") or "").strip()
    if len(about) > 160:
        about = about[:157].rstrip() + "…"
    if about.lower() in ("(optional)", "optional", "-"):
        about = ""

    print(
        json.dumps(
            {
                "repo": f"https://github.com/{m.group(1)}/{m.group(2)}",
                "group": group,
                "about": about or None,
                "issue": int(number or 0),
            }
        )
    )
    return 0


# ---------------------------------------------------------------------------
# news mode
# ---------------------------------------------------------------------------

NEWS_KINDS = ("site", "release", "community", "guide")
NEWS_KIND_ALIASES = {
    "site": "site",
    "site update": "site",
    "release": "release",
    "community": "community",
    "guide": "guide",
}
NEWS_MAX_TITLE = 120
NEWS_MAX_SUMMARY = 200
NEWS_MAX_PARAGRAPHS = 8
NEWS_MAX_PARAGRAPH = 800
NEWS_MAX_LABEL = 60

COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HANDLE_RE = re.compile(r"[A-Za-z0-9-]{1,39}")
REPO_PART_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
BARE_REPO_RE = re.compile(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")

BLANKISH = {"", "(optional)", "optional", "-", "none", "n/a"}


def field(sec, *names):
    """Text of the first heading matching any alias, ignoring `(optional)`."""
    for key, value in sec.items():
        base = re.sub(r"\s*\(.*?\)\s*$", "", key).strip()
        if base in names:
            return value
    return None


def paragraphs(text):
    """Split section text on blank lines; one paragraph per block."""
    blocks = re.split(r"\n\s*\n", text or "")
    return [" ".join(block.split()) for block in blocks if block.strip()]


def news_kind(text):
    value = " ".join((text or "").split()).lower()
    if value in BLANKISH:
        return "community"
    if value not in NEWS_KIND_ALIASES:
        raise ValueError(
            f"unknown category {text.strip()!r}; use one of: "
            + ", ".join(NEWS_KINDS)
        )
    return NEWS_KIND_ALIASES[value]


def news_repo(text):
    raw = (text or "").strip().strip("`").strip()
    if raw.lower() in BLANKISH:
        return None
    m = REPO_PART_RE.search(raw) or BARE_REPO_RE.fullmatch(raw)
    if not m:
        raise ValueError(
            f"cannot read a repository from {raw!r}; use owner/name or a GitHub URL"
        )
    owner, name = m.group(1), m.group(2)
    if name.endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        raise ValueError(f"cannot read a repository from {raw!r}; use owner/name")
    return f"{owner}/{name}"


def news_link(text):
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines or lines[0].lower() in BLANKISH:
        return None
    line = lines[0]
    if "|" in line:
        label, url = line.split("|", 1)
    else:
        label, url = "Link", line
    label = label.strip().strip("`").strip() or "Link"
    url = url.strip().strip("<>").strip().rstrip(").,;")
    if not url.startswith("https://") or " " in url or "." not in url[8:]:
        raise ValueError(f"link must be an absolute https:// URL, got {url!r}")
    if len(label) > NEWS_MAX_LABEL:
        raise ValueError(f"link label is {len(label)} chars (max {NEWS_MAX_LABEL})")
    return {"label": label, "url": url}


def news_main():
    body = os.environ.get("ISSUE_BODY", "")
    number = os.environ.get("ISSUE_NUMBER", "0")
    # Template HTML comments survive in a markdown issue body; they are not content.
    sec = sections(COMMENT_RE.sub("", body))

    try:
        title = " ".join((field(sec, "title", "headline") or "").split())
        if not title:
            raise ValueError("no title found; fill in the `### Title` section")
        if len(title) > NEWS_MAX_TITLE:
            raise ValueError(f"title is {len(title)} chars (max {NEWS_MAX_TITLE})")

        paras = paragraphs(field(sec, "news", "body", "text"))
        if not paras:
            raise ValueError("no post text found; fill in the `### News` section")
        if len(paras) > NEWS_MAX_PARAGRAPHS:
            raise ValueError(
                f"post has {len(paras)} paragraphs (max {NEWS_MAX_PARAGRAPHS})"
            )
        for i, para in enumerate(paras, 1):
            if len(para) > NEWS_MAX_PARAGRAPH:
                raise ValueError(
                    f"paragraph {i} is {len(para)} chars (max {NEWS_MAX_PARAGRAPH})"
                )

        summary = " ".join((field(sec, "summary") or "").split())
        if summary.lower() in BLANKISH:
            summary = ""
        if len(summary) > NEWS_MAX_SUMMARY:
            raise ValueError(
                f"summary is {len(summary)} chars (max {NEWS_MAX_SUMMARY})"
            )

        kind = news_kind(field(sec, "category", "kind"))
        repo = news_repo(field(sec, "related repo", "repo", "repo url"))
        link = news_link(field(sec, "link", "links"))

        raw_date = " ".join((field(sec, "date") or "").split())
        if not raw_date or raw_date.lower() in BLANKISH:
            when = date.today()
        else:
            try:
                when = date.fromisoformat(raw_date)
            except ValueError:
                raise ValueError(f"bad date {raw_date!r}; use YYYY-MM-DD") from None
            if when > date.today():
                raise ValueError(f"date {raw_date} is in the future")
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    author = (os.environ.get("ISSUE_USER") or "").strip().lstrip("@").strip()
    if not HANDLE_RE.fullmatch(author):
        author = ""

    print(
        json.dumps(
            {
                "title": title,
                "body": paras,
                "summary": summary or None,
                "kind": kind,
                "repo": repo,
                "links": [link] if link else [],
                "author": author or None,
                "date": when.isoformat(),
                "issue": int(number or 0),
            }
        )
    )
    return 0


if __name__ == "__main__":
    if "--news" in sys.argv[1:]:
        sys.exit(news_main())
    sys.exit(main())
