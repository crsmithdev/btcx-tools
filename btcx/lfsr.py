"""The 16-bit Galois LFSR (taps B400) whose bit stream XOR-masks each payload lane of file 62.

One mask byte is 8 steps: before each step the low bit of the state is taken, and the 8 bits
are packed MSB first. 8 and the period 65,535 have no common factor, so the byte sequence
from any state visits every state once per period.
"""

from collections.abc import Iterable
from functools import cache

import numpy as np

from . import Error

TAPS = 0xB400
PERIOD = 65535  # also the largest state: every state but 0 is on the cycle


@cache
def _cycle() -> tuple[np.ndarray, list[int], dict[int, int]]:
    """Mask bytes for two periods from state 1, the state at each phase, and its inverse."""
    seq = np.empty(PERIOD, np.uint8)
    states, state = [], 1
    for phase in range(PERIOD):
        states.append(state)
        byte = 0
        for _ in range(8):
            byte = (byte << 1) | (state & 1)
            state = (state >> 1) ^ (TAPS if state & 1 else 0)
        seq[phase] = byte
    return np.tile(seq, 2), states, {s: p for p, s in enumerate(states)}


def state_at(phase: int) -> int:
    return _cycle()[1][phase % PERIOD]


def mask_windows(words: int) -> np.ndarray:
    """A read-only (PERIOD, words) view: row p is the mask stream from phase p."""
    return np.lib.stride_tricks.sliding_window_view(_cycle()[0], words)[:PERIOD]


def hex_states(states: Iterable[int]) -> list[str]:
    return [f"{s:04X}" for s in states]


def unmask(payload: np.ndarray, states: tuple[int, ...]) -> np.ndarray:
    """XOR each lane with the mask stream from its start state."""
    lanes = payload.shape[1]
    if len(states) != lanes or not all(0 < s <= PERIOD for s in states):
        raise Error(f"give {lanes} start states from 0001 to {PERIOD:04X}, one per lane")
    seq, _, phase_of = _cycle()
    out = payload.copy()
    for lane, state in enumerate(states):
        out[:, lane] ^= seq[(phase_of[state] + np.arange(len(payload))) % PERIOD]
    return out
