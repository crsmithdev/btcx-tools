"""The published findings that `btcx verify` reproduces from the pinned inputs.

Each finding has a check that observes a JSON value from the inputs and the value the
finding expects. Credit goes to the contributor who first posted the finding, with a link.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache

from . import Error, data, glyphs, keysearch, lfsr, splat
from .container import Container

F62_STATES = (0x1F25, 0x02D2, 0x6089, 0xB161)


@dataclass(frozen=True)
class Finding:
    id: str
    claim: str
    credit: str
    link: str
    expected: object
    observe: Callable[[], object]

    def check(self) -> dict:
        """The result as JSON values. A check that raises a user error fails with its message."""
        try:
            observed = self.observe()
        except Error as e:
            observed = f"error: {e}"
        return {
            "id": self.id,
            "claim": self.claim,
            "credit": self.credit,
            "link": self.link,
            "expected": self.expected,
            "observed": observed,
            "pass": observed == self.expected,
        }


@cache
def _container(name: str) -> Container:
    return Container(data.read(name))


@cache
def _glyphs() -> glyphs.Glyphs:
    return glyphs.parse(data.read(data.F003))  # parse fails on a bad checksum


def _decode() -> dict:
    unmasked = splat.unmask(_container(data.F62), F62_STATES)
    return {
        "rows": len(unmasked.rows),
        "unit_quaternions": unmasked.unit_quaternions,
        "sha256": data.digest(unmasked.plain.tobytes()),
    }


def _key() -> dict:
    container = _container(data.F62)
    return {
        "record": container.anomalies()[0][0],
        "states": lfsr.hex_states(container.embedded_key()),
    }


def _outliers(name: str, starts: list[int]) -> list[list[str]]:
    """For each window, the start states of the lanes whose best phase is an outlier."""
    payload = _container(name).payload
    return [
        lfsr.hex_states(lane.state for lane in keysearch.search(payload, start)[1] if lane.outlier)
        for start in starts
    ]


ISSUE_5 = "https://github.com/suebtwist/btcx-files/issues/5"

FINDINGS = [
    Finding(
        "container-versions",
        "File 62, both 8k samples and 306_state.bin start with the same 15-byte sync word and a "
        "version byte: 05, and 07 on 306_state.bin.",
        "anthony-lang09",
        ISSUE_5,
        [5, 5, 5, 7],
        lambda: [_container(n).version for n in [data.F62, *data.SAMPLES_8K, data.F306]],
    ),
    Finding(
        "base60-8k",
        "In both 8k samples, lanes 0 and 1 hold only base-60 digits at records 817-864.",
        "anthony-lang09",
        ISSUE_5,
        [[817, 864], [817, 864]],
        lambda: [list(r) for n in data.SAMPLES_8K for r in _container(n).base60_regions()],
    ),
    Finding(
        "306-countdown",
        "306_state.bin breaks the A5 separators in 3 identical 12-record runs counting 59, 58, 57.",
        "anthony-lang09",
        ISSUE_5,
        [[start, "00 3B 00 3B 00 3A 00 3A 00 39 00 39"] for start in (306, 59057, 590570)],
        lambda: [[start, run.hex(" ").upper()] for start, run in _container(data.F306).anomalies()],
    ),
    Finding(
        "003-records",
        "003_state.bin holds 239 framed records, each with a mod-60 checksum: 53 of type 50, "
        "88 of type 51, 89 of type 52, 8 of type 49 and 1 of type 48.",
        "NameLucky2205",
        f"{ISSUE_5}#issuecomment-6137385178",
        {"50": 53, "51": 88, "52": 89, "49": 8, "48": 1},
        lambda: {str(kind): n for kind, n in _glyphs().types.items()},
    ),
    Finding(
        "003-signs",
        "In 003, type 50 records are strokes and type 51 records are signs that place them; "
        "all 204 stroke references in the signs resolve.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/15",
        {"stroke_references": 204, "unresolved": 0},
        lambda: {
            "stroke_references": len(_glyphs().stroke_references()),
            "unresolved": _glyphs().unresolved()[0],
        },
    ),
    Finding(
        "f62-decode",
        "File 62 unmasked with four B400 LFSRs is 184,148 rows of 27 float32 with unit quaternions.",
        "NameLucky2205",
        f"{ISSUE_5}#issuecomment-6185551572",
        {
            "rows": 184148,
            "unit_quaternions": 184148,
            "sha256": "c90d15fd2194817fa727c191351cb85a08eabf8b7011a5bfd53527c49150c82d",
        },
        _decode,
    ),
    Finding(
        "f62-key",
        "File 62 holds its key: separators 2048-2055, XOR A5, are the four LFSR start states.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/12",
        {"record": 2048, "states": lfsr.hex_states(F62_STATES)},
        _key,
    ),
    Finding(
        "f62-blind",
        "A blind search of all 65,535 phases on words 100,000-104,095 finds the same four states.",
        "aleph",
        "https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817",
        [lfsr.hex_states(F62_STATES)],
        lambda: _outliers(data.F62, [100_000]),
    ),
    Finding(
        "306-no-b400",
        "306_state.bin shows no B400 mask outlier in the first window after each countdown run.",
        "aleph",
        "https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817",
        [[], [], []],
        lambda: _outliers(data.F306, [318, 59069, 590582]),
    ),
]
