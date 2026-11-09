"""The claim rows, and the ledger page on a fixture and on the real rows."""

import re
import sys

import pytest

from btcx import ledger
from btcx.claims import CLAIMS, FILE62, FILES, STATUSES, Claim
from btcx.cli import main
from btcx.findings import FINDINGS, Finding

LINK = re.compile(
    r"https://(suebtwist\.github\.io/btcx-files/"
    r"|github\.com/suebtwist/btcx-files/issues/(5|12|15)(#issuecomment-\d+)?)$"
)


@pytest.mark.parametrize("claim", CLAIMS, ids=range(len(CLAIMS)))
def test_claim_fields(claim):
    assert claim.file in FILES
    assert claim.claim and claim.credit
    assert LINK.match(claim.link), claim.link
    assert claim.status in STATUSES
    assert claim.status == "not checked" or claim.note, "a status other than not checked names its check"


def test_findings_have_groups():
    assert all(f.file in FILES for f in FINDINGS)


def row(html, claim):
    """The table row of the page whose first cell is the claim."""
    return next(r for r in re.findall(r"<tr>.*?</tr>", html) if f">{claim}</td>" in r)


def test_fixture_page():
    passing = Finding(
        "ok", FILE62, "A claim that holds.", "anon", "https://example.org/1", "solid", 1, lambda: 1
    )
    failing = Finding("bad", FILE62, "A claim that fails.", "anon", "https://example.org/2", "", 1, lambda: 2)
    claim = Claim(FILE62, "A claim nobody checked.", "anon", "https://example.org/3", "", "not checked", "")
    html = ledger.page(ledger.rows([passing, failing], [claim]), "0" * 40, "2026-11-09")
    assert "reproduced" in row(html, "A claim that holds.")
    assert ledger.FAILS in row(html, "A claim that fails.")
    assert "reproduced" not in row(html, "A claim that fails.")
    assert "not checked" in row(html, "A claim nobody checked.")
    assert "3 claims: 1 reproduced, 1 not checked, 1 check fails." in html
    assert "<script" not in html.lower()


def test_page(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["btcx", "ledger", "--out", str(tmp_path)])
    main()
    html = (tmp_path / "index.html").read_text()
    assert "<title>btcx claim ledger</title>" in html
    assert "<script" not in html.lower()
    assert html.count("<tr><td") == len(FINDINGS) + len(CLAIMS)
    assert ledger.FAILS not in html
