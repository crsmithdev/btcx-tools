"""Blind phase search: for one payload lane, try every phase of the B400 LFSR and score
the unmasked bytes by entropy. A real key shows up as a low-entropy outlier."""

import numpy as np

from . import lfsr


def scan_lane(ct_lane: np.ndarray, sample: int = 4096, chunk: int = 2048):
    seq, _ = lfsr.cycle()
    x = ct_lane[:sample].astype(np.int64)
    n = len(x)
    scores = np.empty(lfsr.PERIOD)
    for p0 in range(0, lfsr.PERIOD, chunk):
        ps = np.arange(p0, min(p0 + chunk, lfsr.PERIOD))
        dec = x[None, :] ^ seq[ps[:, None] + np.arange(n)[None, :]]
        counts = np.bincount((np.arange(len(ps))[:, None] * 256 + dec).ravel(),
                             minlength=len(ps) * 256).reshape(len(ps), 256)
        prob = counts / n
        with np.errstate(divide="ignore", invalid="ignore"):
            scores[ps] = -np.nansum(np.where(prob > 0, prob * np.log2(prob), 0), axis=1)
    return scores


def best(scores: np.ndarray, top: int = 3):
    med = np.median(scores)
    mad = np.median(np.abs(scores - med)) * 1.4826
    order = np.argsort(scores)[:top]
    return [(int(p), float(scores[p]), float((med - scores[p]) / mad)) for p in order], med


def state_at(phase: int, word_offset: int) -> int:
    """LFSR state at word 0 of the stream, given the phase found at word_offset."""
    _, phase_of = lfsr.cycle()
    target = (phase - word_offset) % lfsr.PERIOD
    return next(s for s, p in phase_of.items() if p == target)
