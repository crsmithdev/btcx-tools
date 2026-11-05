"""The 16-bit Galois LFSR (mask B400) that XOR-masks each payload lane of file 62."""

import numpy as np

TAPS = 0xB400
PERIOD = 65535


def stream(state: int, words: int) -> np.ndarray:
    """Mask bytes: the low bit before each step, 8 steps per byte, packed MSB first."""
    out = np.empty(words, np.uint8)
    for w in range(words):
        v = 0
        for _ in range(8):
            v = (v << 1) | (state & 1)
            state = (state >> 1) ^ (TAPS if state & 1 else 0)
        out[w] = v
    return out


_cycle = None


def cycle() -> tuple[np.ndarray, dict]:
    """One full period of mask bytes from state 1, and each state's phase in it."""
    global _cycle
    if _cycle is None:
        state, phase_of = 1, {}
        for w in range(PERIOD):
            phase_of[state] = w
            for _ in range(8):
                state = (state >> 1) ^ (TAPS if state & 1 else 0)
        if len(phase_of) != PERIOD:
            raise RuntimeError("the byte-step sequence does not visit every state")
        _cycle = (np.tile(stream(1, PERIOD), 2), phase_of)
    return _cycle


def keystream(state: int, words: int) -> np.ndarray:
    seq, phase_of = cycle()
    idx = (phase_of[state] + np.arange(words)) % PERIOD
    return seq[idx]


def unmask(payload: np.ndarray, states) -> np.ndarray:
    out = payload.copy()
    for lane, s in enumerate(states):
        out[:, lane] ^= keystream(s, len(payload))
    return out


def states_from_anomaly(sep: bytes):
    """Eight separator bytes XOR A5, read as four little-endian 16-bit states."""
    b = bytes(x ^ 0xA5 for x in sep)
    return tuple(b[i] | b[i + 1] << 8 for i in range(0, 8, 2))
