import pytest

from btcx.findings import FINDINGS


@pytest.mark.parametrize("finding", FINDINGS, ids=[f.id for f in FINDINGS])
def test_finding_reproduces(finding):
    result = finding.check()
    assert result["pass"], result
