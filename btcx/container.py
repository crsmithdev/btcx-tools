"""The BTCX container: 16-byte header, then 5-byte records (4 payload bytes + separator)."""

import numpy as np

SYNC = bytes.fromhex("F5A5055A5F") * 3
SEP = 0xA5


class Container:
    def __init__(self, raw: bytes):
        if raw[:15] != SYNC:
            raise ValueError("no BTCX header")
        self.raw = raw
        self.version = raw[15]
        body = np.frombuffer(raw[16:], np.uint8)
        self.count, self.tail = divmod(len(body), 5)
        records = body[: self.count * 5].reshape(self.count, 5)
        self.separators = records[:, 4]
        payload = records[:, :4]
        if self.tail == 4:  # a final word with no separator after it
            payload = np.vstack((payload, body[self.count * 5:]))
        self.payload = payload  # shape (words, 4)

    def anomalies(self):
        """Runs of records whose separator is not A5: [(start, bytes)]."""
        idx = np.nonzero(self.separators != SEP)[0]
        runs = []
        for i in idx:
            if runs and runs[-1][0] + len(runs[-1][1]) == i:
                runs[-1][1].append(int(self.separators[i]))
            else:
                runs.append((int(i), [int(self.separators[i])]))
        return [(start, bytes(b)) for start, b in runs]

    def base60_regions(self, lanes=(0, 1), min_words=32):
        """Word ranges where the given payload lanes hold only values 0-59."""
        ok = np.all(self.payload[:, list(lanes)] < 60, axis=1)
        regions, start = [], None
        for i, flag in enumerate(np.append(ok, False)):
            if flag and start is None:
                start = i
            elif not flag and start is not None:
                if i - start >= min_words:
                    regions.append((start, i))
                start = None
        return regions


def entropy(values) -> float:
    counts = np.bincount(np.asarray(values, np.uint8).ravel(), minlength=256)
    p = counts[counts > 0] / counts.sum()
    return float(-(p * np.log2(p)).sum())
