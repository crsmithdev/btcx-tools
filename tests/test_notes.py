from btcx import notes

PAGE = (
    '<article class="passage" data-key="348" data-time="2:24">'
    '<a class="ref" href="https://youtu.be/a?t=144">2:24</a><span class="speaker">the narrator</span>'
    '<p class="passage-text">Gently extracted. Nothing wasted. '
    "The Master sends forth the Seraphim.</p></article>"
    '<article class="passage" data-key="370-short" data-time="0:45">'
    '<a class="ref" href="https://youtu.be/b?t=45">0:45</a><span class="speaker">a voice</span>'
    '<p class="passage-text">Hands open. Nothing wasted. Even the Master &amp; his hands.</p></article>'
    '<figure class="line" data-passage="348:2:24">'
)


def test_build_search_pairs(tmp_path):
    db = tmp_path / "notes.sqlite"
    assert notes.build(PAGE, db) == 2
    assert [row[:4] for row in notes.search(db, "Master")] == [
        (
            "348",
            "2:24",
            "the narrator",
            "Gently extracted. Nothing wasted. The Master sends forth the Seraphim.",
        ),
        ("370-short", "0:45", "a voice", "Hands open. Nothing wasted. Even the Master & his hands."),
    ]
    terms = {term: files for term, files, _ in notes.pairs(db, 3)}
    assert terms == {"Master": ["348", "370"]}  # not "Nothing": it starts a sentence
