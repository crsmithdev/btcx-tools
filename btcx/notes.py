"""The creator's notes page (suebtwist.github.io/btcx-files) as a SQLite index.

`passages` holds every transcript line: file key, time, speaker, text, link.
`cited` holds the lines the creator already quotes in the topic sections.
"""

import html
import re
import sqlite3
from collections import defaultdict

PASSAGE = re.compile(
    r'<article class="passage"[^>]*data-key="([^"]+)" data-time="([^"]+)">'
    r'<a class="ref" href="([^"]+)"[^>]*>[^<]*</a><span class="speaker">(.*?)</span>'
    r'<p class="passage-text">(.*?)</p></article>', re.S)
CITED = re.compile(r'<figure class="line" data-passage="([^"]+)">')
TAG = re.compile(r"<[^>]+>")

STOP = set("""a about after again all also am an and any are as at be because been before
being but by can could did do does down each even every for from had has have he her here
him his how i if in into is it its just like may me more most must my no not now of off on
once one only or other our out over own same she should so some such than that the their
them then there these they this those through to too under until up us very was we were what
when where which while who whom why will with would you your yet let shall upon thus""".split())


def build(page: str, db_path: str):
    db = sqlite3.connect(db_path)
    db.executescript("""
        drop table if exists passages; drop table if exists cited;
        create table passages (key text, time text, speaker text, text text, url text);
        create table cited (ref text);
    """)
    rows = [(k, t, html.unescape(TAG.sub("", s)), html.unescape(TAG.sub("", x)), html.unescape(u))
            for k, t, u, s, x in PASSAGE.findall(page)]
    db.executemany("insert into passages values (?,?,?,?,?)", rows)
    db.executemany("insert into cited values (?)", [(r,) for r in set(CITED.findall(page))])
    db.commit()
    return len(rows)


def search(db_path: str, term: str):
    db = sqlite3.connect(db_path)
    return db.execute("select key, time, speaker, text, url from passages where text like ? "
                      "order by key, time", (f"%{term}%",)).fetchall()


def _terms(text):
    """Proper nouns (capitalised, not first word) and three-word phrases."""
    words = re.findall(r"[\w'’-]+", text)
    out = {w for i, w in enumerate(words) if i and w[0].isupper() and w.lower() not in STOP}
    low = [w.lower() for w in words]
    out |= {" ".join(low[i:i + 3]) for i in range(len(low) - 2)
            if sum(w not in STOP for w in low[i:i + 3]) >= 2}
    return out


def pairs(db_path: str, max_files: int = 3):
    """Proper nouns and phrases that occur in 2..max_files files: candidate cross-file links.
    Each comes with every line that uses it, and whether the notes already cite that line."""
    db = sqlite3.connect(db_path)
    cited = {r for (r,) in db.execute("select ref from cited")}
    hits = defaultdict(list)
    for key, time, text, url in db.execute("select key, time, text, url from passages"):
        for t in _terms(text):
            hits[t].append((key, time, text, url, f"{key}:{time}" in cited))
    out, seen = [], set()
    for t, lines in hits.items():
        files = {l[0].split("-")[0] for l in lines}  # 370-short and 373-open are cuts of 370 and 373
        refs = frozenset((l[0], l[1]) for l in lines)
        if 2 <= len(files) <= max_files and not all(l[4] for l in lines) and refs not in seen:
            seen.add(refs)
            out.append((t, sorted(files), lines))
    out.sort(key=lambda x: (" " in x[0], len(x[1]), len(x[2])))
    return out
