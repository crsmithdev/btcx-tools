"""The creator's notes page (suebtwist.github.io/btcx-files) as a SQLite index.

`passages` holds every transcript line: file key, time, speaker, text, link.
`cited` holds the lines the page already quotes in its topic sections.
"""

import html
import re
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from . import Error

PASSAGE = re.compile(
    r'<article class="passage"[^>]*data-key="([^"]+)" data-time="([^"]+)">'
    r'<a class="ref" href="([^"]+)"[^>]*>[^<]*</a><span class="speaker">(.*?)</span>'
    r'<p class="passage-text">(.*?)</p></article>',
    re.S,
)
CITED = re.compile(r'<figure class="line" data-passage="([^"]+)">')
TAG = re.compile(r"<[^>]+>")
WORD = re.compile("[\\w'\u2019-]+")  # \u2019 is the curly apostrophe
SENTENCE_END = re.compile(r"[.!?]+")

STOP = frozenset(
    """
a about after again all also am an and any are as at be because been before being but by
can could did do does down each even every for from had has have he her here him his how
i if in into is it its just like may me more most must my no not now of off on once one
only or other our out over own same she should so some such than that the their them then
there these they this those through to too under until up us very was we were what when
where which while who whom why will with would you your yet let shall upon thus
""".split()
)


def build(page: str, db_path: Path) -> int:
    with closing(sqlite3.connect(db_path)) as db:
        db.executescript("""
            drop table if exists passages; drop table if exists cited;
            create table passages (key text, time text, speaker text, text text, url text);
            create table cited (ref text);
        """)
        rows = [
            (key, time, _text(speaker), _text(text), html.unescape(url))
            for key, time, url, speaker, text in PASSAGE.findall(page)
        ]
        db.executemany("insert into passages values (?,?,?,?,?)", rows)
        db.executemany("insert into cited values (?)", [(r,) for r in set(CITED.findall(page))])
        db.commit()
    return len(rows)


def _text(fragment: str) -> str:
    return html.unescape(TAG.sub("", fragment))


def _open(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise Error(f"{db_path} is missing; run: btcx notes build")
    return sqlite3.connect(db_path)


def search(db_path: Path, term: str) -> list[tuple]:
    with closing(_open(db_path)) as db:
        return db.execute(
            "select key, time, speaker, text, url from passages where text like ? order by key, time",
            (f"%{term}%",),
        ).fetchall()


def _terms(text: str) -> set[str]:
    """Proper nouns (capitalised, not first in a sentence) and three-word phrases in one sentence."""
    out = set()
    for sentence in SENTENCE_END.split(text):
        words = WORD.findall(sentence)
        out |= {w for i, w in enumerate(words) if i and w[0].isupper() and w.lower() not in STOP}
        low = [w.lower() for w in words]
        out |= {
            " ".join(low[i : i + 3])
            for i in range(len(low) - 2)
            if sum(w not in STOP for w in low[i : i + 3]) >= 2
        }
    return out


def pairs(db_path: Path, max_files: int) -> list[tuple]:
    """Proper nouns and phrases used in 2..max_files files: candidate links between files.

    Each comes with every line that uses it and whether the page already cites that line.
    Shorter terms and terms in fewer files come first.
    """
    with closing(_open(db_path)) as db:
        cited = {r for (r,) in db.execute("select ref from cited")}
        passages = db.execute("select key, time, text from passages").fetchall()
    hits = defaultdict(list)
    for key, time, text in passages:
        for t in _terms(text):
            hits[t].append((key, time, text, f"{key}:{time}" in cited))
    out, seen = [], set()
    for t, lines in hits.items():
        files = {line[0].split("-")[0] for line in lines}  # 370-short and 373-open are cuts of 370, 373
        refs = frozenset((line[0], line[1]) for line in lines)
        if 2 <= len(files) <= max_files and not all(line[3] for line in lines) and refs not in seen:
            seen.add(refs)
            out.append((t, sorted(files), lines))
    out.sort(key=lambda x: (" " in x[0], len(x[1]), len(x[2])))
    return out
