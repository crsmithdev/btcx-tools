"""Blind phase search: for each payload lane, try every phase of the B400 LFSR and score the
unmasked window by entropy. A real key is a low-entropy outlier among the 65,535 phases."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from . import Error, lfsr

WINDOW = 4096
OUTLIER_Z = 8.0
CHUNK_BYTES = 16 << 20  # int32 bins per numpy pass and lane; peak memory is about 400 MB at any window
MAD_TO_SIGMA = 1.4826


@dataclass(frozen=True)
class Lane:
    state: int  # the start state at word 0 that the best phase implies
    entropy: float
    median: float
    z: float  # robust z of the best phase: (median - entropy) / scaled MAD
    outlier: bool


def search(payload: np.ndarray, start: int, words: int = WINDOW) -> tuple[int, list[Lane]]:
    """Score every phase on words start..start+words-1 of each lane, in parallel.

    Returns the number of words scored (fewer at the end of the payload) and one Lane per lane.
    """
    if start < 0:
        raise Error(f"start word {start:,} is negative")
    if start >= len(payload):
        raise Error(f"start word {start:,} is past the last payload word, {len(payload) - 1:,}")
    if not 0 < words <= lfsr.PERIOD:
        raise Error(f"the window must be 1 to {lfsr.PERIOD:,} words, not {words:,}")
    window = payload[start : start + words]

    def lane(column: np.ndarray) -> Lane:
        scores = _scores(column)
        best = int(np.argmin(scores))
        median = float(np.median(scores))
        spread = float(np.median(np.abs(scores - median))) * MAD_TO_SIGMA
        if spread == 0:
            raise Error(f"a {len(column):,}-word window scores every phase the same; use a longer one")
        robust_z = (median - float(scores[best])) / spread
        return Lane(lfsr.state_at(best - start), float(scores[best]), median, robust_z, robust_z > OUTLIER_Z)

    with ThreadPoolExecutor() as pool:  # numpy releases the GIL in the scoring
        return len(window), list(pool.map(lane, window.T))


def _scores(lane: np.ndarray) -> np.ndarray:
    """Entropy of the lane XOR the mask stream at each phase."""
    windows = lfsr.mask_windows(len(lane))
    chunk = max(1, CHUNK_BYTES // (4 * len(lane)))
    offsets = np.arange(chunk, dtype=np.int32)[:, None] * 256
    scores = np.empty(lfsr.PERIOD)
    for p0 in range(0, lfsr.PERIOD, chunk):
        p1 = min(p0 + chunk, lfsr.PERIOD)
        bins = ((windows[p0:p1] ^ lane) + offsets[: p1 - p0]).ravel()
        counts = np.bincount(bins, minlength=(p1 - p0) * 256).reshape(p1 - p0, 256)
        scores[p0:p1] = entropy(counts)
    return scores


def entropy(counts: np.ndarray) -> np.ndarray:
    """Shannon entropy in bits per byte, over the last axis of an array of byte counts."""
    with np.errstate(divide="ignore", invalid="ignore"):  # empty counts and log2(0)
        p = counts / counts.sum(axis=-1, keepdims=True)
        return np.where(p > 0, -p * np.log2(p), 0).sum(axis=-1)


def byte_entropy(values: np.ndarray) -> float:
    return float(entropy(np.bincount(values.ravel(), minlength=256)))
