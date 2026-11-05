"""The BTCX container: a 16-byte header, then 5-byte records of 4 payload bytes and a separator."""

import numpy as np

from . import Error

SYNC = bytes.fromhex("F5A5055A5F") * 3
HEADER = 16
RECORD = 5
LANES = RECORD - 1
SEPARATOR = 0xA5
KEY_RUN = 8  # separators that hold an embedded key
BASE = 60
BASE60_MIN_WORDS = 32


class Container:
    def __init__(self, raw: bytes):
        if len(raw) < HEADER or raw[: len(SYNC)] != SYNC:
            raise Error(
                "not a BTCX container (no sync word and version); 003_state.bin is read by: btcx glyphs"
            )
        self.version = raw[len(SYNC)]
        body = np.frombuffer(raw[HEADER:], np.uint8)
        self.count, self.tail = divmod(len(body), RECORD)
        records = body[: self.count * RECORD].reshape(self.count, RECORD)
        self.separators = records[:, LANES]
        payload = records[:, :LANES]
        if self.tail == LANES:  # a last payload word with no separator after it
            payload = np.vstack((payload, body[self.count * RECORD :]))
        self.payload = payload  # (words, lanes)

    def anomalies(self) -> list[tuple[int, bytes]]:
        """Runs of records whose separator is not A5, as (first record, separator bytes)."""
        return [
            (start, self.separators[start:stop].tobytes())
            for start, stop in _runs(self.separators != SEPARATOR)
        ]

    def embedded_key(self) -> tuple[int, ...] | None:
        """One LFSR start state per lane, if the only anomaly is one run of 8 separators.

        The run XOR A5, read as little-endian 16-bit pairs, gives the states.
        """
        runs = self.anomalies()
        if len(runs) != 1 or len(runs[0][1]) != KEY_RUN:
            return None
        key = bytes(b ^ SEPARATOR for b in runs[0][1])
        return tuple(int.from_bytes(key[i : i + 2], "little") for i in range(0, KEY_RUN, 2))

    def base60_regions(self) -> list[tuple[int, int]]:
        """Inclusive word ranges of 32 or more words where lanes 0 and 1 hold only 0-59."""
        flags = np.all(self.payload[:, :2] < BASE, axis=1)
        return [(start, stop - 1) for start, stop in _runs(flags) if stop - start >= BASE60_MIN_WORDS]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Half-open index ranges of consecutive True values."""
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist(), strict=True))
