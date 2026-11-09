"""The published findings that `btcx verify` reproduces from the pinned inputs.

Each finding has a check that observes a JSON value from the inputs and the value the
finding expects. Credit goes to the contributor who first posted the finding, with a link.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache

import numpy as np

from . import Error, data, glyphs, keysearch, lfsr, splat
from .claims import ALL, FILE62, SAMPLES, STATE003, STATE306
from .container import BASE, Container

F62_STATES = (0x1F25, 0x02D2, 0x6089, 0xB161)
COUNTER = slice(4, 7)  # label records of the minute counter, in lane 1


@dataclass(frozen=True)
class Finding:
    id: str
    file: str  # the ledger group, from claims.FILES
    claim: str
    credit: str
    link: str
    grade: str  # the poster's own grade, quoted, or ""
    expected: object
    observe: Callable[[], object]
    note: str = ""  # context for the ledger row

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


def _sections() -> dict:
    """The section table of 306: (id, offset, length, count) as lane 0 uint32 at bytes 432-479."""
    lane = _container(data.F306).payload[:, 0]
    table = np.frombuffer(lane.tobytes(), "<u4")[108:120].reshape(3, 4).tolist()
    return {"table": table, "end": table[-1][1] + table[-1][2], "payload": lane.size * 4}


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


def _thirds(values: np.ndarray) -> list[int]:
    """How many nonzero float32 values are fl32(s / 3) for a float32 s, and how many there are."""
    values = values[values != 0]
    near = (values.astype(np.float64) * 3).astype(np.float32).view(np.int32)
    hits = np.logical_or.reduce(
        [(near + step).view(np.float32) / np.float32(3) == values for step in (-1, 0, 1)]
    )
    return [int(hits.sum()), len(values)]


def _grey() -> dict:
    rows = splat.unmask(_container(data.F62), F62_STATES).rows
    return {
        "fields_11_26": _thirds(rows[:, splat.DC.start :].ravel()),
        "fields_0_10": _thirds(rows[:, : splat.DC.start].ravel()),
    }


def _counter(name: str) -> int:
    """The minute counter of an 8k sample: lane 1 of label records 4-6, as base-60 digits."""
    container = _container(name)
    start = container.base60_regions()[0][0]
    hi, mid, lo = container.payload[start:][COUNTER, 1].tolist()
    return (hi * BASE + mid) * BASE + lo


def _clock() -> dict:
    minutes = [_counter(n) for n in data.SAMPLES_8K]
    times = [datetime.strptime(n[:13], "%Y%m%d_%H%M") for n in data.SAMPLES_8K]
    return {
        "minutes": minutes,
        "difference": minutes[1] - minutes[0],
        "name_gap": (times[1] - times[0]) // timedelta(minutes=1),
    }


ISSUE_5 = "https://github.com/suebtwist/btcx-files/issues/5"

FINDINGS = [
    Finding(
        "container-versions",
        ALL,
        "File 62, both 8k samples and 306_state.bin start with the same 15-byte sync word and a "
        "version byte: 05, and 07 on 306_state.bin.",
        "anthony-lang09",
        ISSUE_5,
        "",
        [5, 5, 5, 7],
        lambda: [_container(n).version for n in [data.F62, *data.SAMPLES_8K, data.F306]],
    ),
    Finding(
        "base60-8k",
        SAMPLES,
        "In both 8k samples, lanes 0 and 1 hold only base-60 digits at records 817-864.",
        "anthony-lang09",
        ISSUE_5,
        "",
        [[817, 864], [817, 864]],
        lambda: [list(r) for n in data.SAMPLES_8K for r in _container(n).base60_regions()],
    ),
    Finding(
        "label-clock",
        SAMPLES,
        "In the 8k samples, lane 1 of label records 4-6 reads 40;0;0 = 144,000 and 42;42;41 = "
        "153,761 minutes (144,000 min = 100 days); the difference, 9,761, is the gap between the "
        "file-name times.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/15",
        "solid",
        {"minutes": [144000, 153761], "difference": 9761, "name_gap": 9761},
        _clock,
    ),
    Finding(
        "306-countdown",
        STATE306,
        "306_state.bin breaks the A5 separators in 3 identical 12-record runs counting 59, 58, 57.",
        "anthony-lang09",
        ISSUE_5,
        "",
        [[start, "00 3B 00 3B 00 3A 00 3A 00 39 00 39"] for start in (306, 59057, 590570)],
        lambda: [[start, run.hex(" ").upper()] for start, run in _container(data.F306).anomalies()],
    ),
    Finding(
        "306-sections",
        STATE306,
        "Lane 0 of 306_state.bin read as little-endian uint32 at bytes 432, 448 and 464 gives "
        "(59, 16384, 7129088, 1), (58, 7145472, 16777216, 8) and (57, 23922688, 1243136, 1); as "
        "offsets and lengths, the sections are contiguous and end at 25,165,824, the payload size.",
        "NameLucky2205",
        f"{ISSUE_5}#issuecomment-6137385178",
        "plausible",
        {
            "table": [[59, 16384, 7129088, 1], [58, 7145472, 16777216, 8], [57, 23922688, 1243136, 1]],
            "end": 25165824,
            "payload": 25165824,
        },
        _sections,
        "Helo3301 states the same table in https://github.com/suebtwist/btcx-files/issues/15 as a "
        "header; lane 0 opens with its own header, so that holds too. btcx-tools' earlier \"does "
        'not hold" read only the 16-byte container header and was wrong. The field meanings are '
        "not checked.",
    ),
    Finding(
        "003-records",
        STATE003,
        "003_state.bin holds 239 framed records, each with a mod-60 checksum: 53 of type 50, "
        "88 of type 51, 89 of type 52, 8 of type 49 and 1 of type 48.",
        "NameLucky2205",
        f"{ISSUE_5}#issuecomment-6137385178",
        "",
        {"50": 53, "51": 88, "52": 89, "49": 8, "48": 1},
        lambda: {str(kind): n for kind, n in _glyphs().types.items()},
    ),
    Finding(
        "003-signs",
        STATE003,
        "In 003, type 50 records are strokes and type 51 records are signs that place them; "
        "all 204 stroke references in the signs resolve.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/15",
        "solid",
        {"stroke_references": 204, "unresolved": 0},
        lambda: {
            "stroke_references": len(_glyphs().stroke_references()),
            "unresolved": _glyphs().unresolved()[0],
        },
    ),
    Finding(
        "f62-decode",
        FILE62,
        "File 62 unmasked with four B400 LFSRs is 184,148 rows of 27 float32 with unit quaternions.",
        "NameLucky2205",
        f"{ISSUE_5}#issuecomment-6185551572",
        "",
        {
            "rows": 184148,
            "unit_quaternions": 184148,
            "sha256": "c90d15fd2194817fa727c191351cb85a08eabf8b7011a5bfd53527c49150c82d",
        },
        _decode,
    ),
    Finding(
        "f62-key",
        FILE62,
        "File 62 holds its key: separators 2048-2055, XOR A5, are the four LFSR start states.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/12",
        "confirmed",
        {"record": 2048, "states": lfsr.hex_states(F62_STATES)},
        _key,
    ),
    Finding(
        "f62-grey",
        FILE62,
        "In file 62, each of the 2,812,518 nonzero grey lighting coefficients (fields 11-26) is "
        "a float32 quotient by 3, as a float32 average of three values gives; in fields 0-10, "
        "1,729,242 of 2,025,628 are.",
        "Helo3301",
        "https://github.com/suebtwist/btcx-files/issues/12",
        "confirmed",
        {"fields_11_26": [2812518, 2812518], "fields_0_10": [1729242, 2025628]},
        _grey,
    ),
    Finding(
        "f62-blind",
        FILE62,
        "A blind search of all 65,535 phases on words 100,000-104,095 finds the same four states.",
        "aleph",
        "https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817",
        "",
        [lfsr.hex_states(F62_STATES)],
        lambda: _outliers(data.F62, [100_000]),
    ),
    Finding(
        "306-no-b400",
        STATE306,
        "306_state.bin shows no B400 mask outlier in the first window after each countdown run.",
        "aleph",
        "https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817",
        "",
        [[], [], []],
        lambda: _outliers(data.F306, [318, 59069, 590582]),
    ),
]
