"""The claim ledger: one static HTML page with a row per claim about the published files.

A finding's status comes from its check, run at build time; a claim's status is set in claims.py.
"""

import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from . import data
from .claims import CLAIMS, FILES, STATUSES, Claim
from .findings import FINDINGS, Finding

REPO = "https://github.com/crsmithdev/btcx-tools"
UPSTREAM = "https://github.com/suebtwist/btcx-files"
FAILS = "check fails"
URL = re.compile(r"https://\S+?(?=[.,;)]?(?:\s|$))")
COMMENT = re.compile(r"/issues/(\d+)(#issuecomment-\d+)?$")

CSS = """
:root { color-scheme: light dark; --fg: #1a1a1a; --bg: #fdfdfc; --dim: #666; --rule: #ddd;
  --ok: #1d6b2f; --part: #8a5a00; --no: #a3201b; --none: #666; }
@media (prefers-color-scheme: dark) {
  :root { --fg: #e6e6e3; --bg: #161616; --dim: #9a9a96; --rule: #333;
    --ok: #6fcf86; --part: #e3b04b; --no: #f0817b; --none: #9a9a96; } }
body { margin: 0 auto; max-width: 72rem; padding: 1rem; font: 15px/1.45 system-ui, sans-serif;
  color: var(--fg); background: var(--bg); }
a { color: inherit; }
header p, h2 { margin: 0.4rem 0; }
h2 { margin-top: 2rem; font-size: 1.1rem; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
th, td { padding: 0.45rem 0.5rem; border-top: 1px solid var(--rule); text-align: left;
  vertical-align: top; overflow-wrap: break-word; }
th { color: var(--dim); font-weight: normal; }
th:nth-child(1) { width: 38%; } th:nth-child(2) { width: 13%; } th:nth-child(3) { width: 10%; }
th:nth-child(4) { width: 9%; }
.dim { color: var(--dim); }
.reproduced { color: var(--ok); } .partly { color: var(--part); }
.does-not-hold, .check-fails { color: var(--no); font-weight: bold; } .not-checked { color: var(--none); }
@media (max-width: 40rem) {
  thead { display: none; }
  table, tr, td { display: block; width: auto !important; }
  tr { border-top: 1px solid var(--rule); padding: 0.4rem 0; }
  td { border: 0; padding: 0.15rem 0; }
  td[data-label]::before { content: attr(data-label) ": "; color: var(--dim); } }
"""

COLUMNS = ["Claim", "First poster", "Their grade", "Status", "Check"]


def _checked(finding: Finding) -> Claim:
    """The finding as a ledger row, with the status of its check run now."""
    status = "reproduced" if finding.check()["pass"] else FAILS
    return Claim(
        finding.file,
        finding.claim,
        finding.credit,
        finding.link,
        finding.grade,
        status,
        f"btcx verify {finding.id}. {finding.note}" if finding.note else f"btcx verify {finding.id}",
    )


def rows(findings: list[Finding], claims: list[Claim]) -> list[Claim]:
    """Ledger rows: each finding, checked now, then each claim."""
    return [_checked(f) for f in findings] + claims


def summary(ledger: list[Claim]) -> str:
    """The row count per status, e.g. "60 claims: 30 reproduced, 30 not checked"."""
    counts = Counter(r.status for r in ledger)
    return f"{len(ledger)} claims: " + ", ".join(f"{counts[s]} {s}" for s in [*STATUSES, FAILS] if counts[s])


def _label(url: str) -> str:
    """Short link text: #15, #15 comment, or the URL."""
    match = COMMENT.search(url)
    if not match or not url.startswith(UPSTREAM):
        return url
    return f"#{match[1]}{' comment' if match[2] else ''}"


def _linked(text: str) -> str:
    return URL.sub(lambda m: f'<a href="{m[0]}">{_label(m[0])}</a>', escape(text, quote=False))


def _row(row: Claim) -> str:
    cells = [
        escape(row.claim),
        f'<a href="{escape(row.link)}">{escape(row.credit)}</a>',
        f"“{escape(row.grade)}”" if row.grade else "",
        f'<span class="{row.status.replace(" ", "-")}">{row.status}</span>',
        _linked(row.note),
    ]
    tds = "".join(
        f'<td data-label="{name}">{cell}</td>' if cell else "<td></td>"
        for name, cell in zip(COLUMNS, cells, strict=True)
    )
    return f"<tr>{tds}</tr>\n"


def _group(name: str, group: list[Claim]) -> str:
    head = "".join(f"<th>{c}</th>" for c in COLUMNS)
    body = "".join(_row(r) for r in group)
    return (
        f"<h2>{escape(name)}</h2>\n<table>\n<thead><tr>{head}</tr></thead>\n"
        f"<tbody>\n{body}</tbody>\n</table>\n"
    )


def page(ledger: list[Claim], commit: str, date: str) -> str:
    groups = "".join(_group(f, [r for r in ledger if r.file == f]) for f in FILES)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>btcx claim ledger</title>
<style>{CSS}</style>
</head>
<body>
<header>
<h1>btcx claim ledger</h1>
<p>One row per claim about the btcx files posted in <a href="{UPSTREAM}/issues/5">#5</a>,
<a href="{UPSTREAM}/issues/12">#12</a> and <a href="{UPSTREAM}/issues/15">#15</a> of
<a href="{UPSTREAM}">suebtwist/btcx-files</a> or on the <a href="https://suebtwist.github.io/btcx-files/">notes
page</a>, with its first poster. A row with a <code>btcx verify</code> finding reruns from the pinned files at
each build; the other rows give the check that ran, or are not checked.</p>
<p>{summary(ledger)}.</p>
<p class="dim">Built {date} by <a href="{REPO}">btcx-tools</a> at
<a href="{REPO}/commit/{commit}">{commit[:7]}</a>.</p>
</header>
{groups}</body>
</html>
"""


def write(out: Path) -> tuple[Path, list[Claim]]:
    """Build the ledger and write out/index.html; return the path and the rows."""
    commit = subprocess.run(
        ["git", "-C", str(data.ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    ledger = rows(FINDINGS, CLAIMS)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "index.html"
    path.write_text(page(ledger, commit, datetime.now(UTC).date().isoformat()))
    return path, ledger
