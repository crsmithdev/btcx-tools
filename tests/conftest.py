import pytest

from btcx import data


@pytest.fixture(scope="session", autouse=True)
def inputs():
    data.fetch(list(data.PINNED))
