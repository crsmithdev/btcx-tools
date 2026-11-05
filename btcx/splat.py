"""File 62: an LFSR-masked payload that reads as 3D Gaussian splat rows of 27 float32.

Field layout (inferred by contributors in btcx-files #5 and #12, not given by the creator):
0-2 position, 3-5 log scale, 6-9 rotation quaternion (w x y z), 10 opacity logit,
11 DC colour (one channel), 12-26 SH rest (one channel, degree 3).
"""

from dataclasses import dataclass

import numpy as np

from . import Error, lfsr
from .container import Container

FIELDS = 27
POSITION, SCALE, ROTATION = slice(0, 3), slice(3, 6), slice(6, 10)
OPACITY, DC, SH_REST = slice(10, 11), slice(11, 12), slice(12, FIELDS)
UNIT_TOLERANCE = 1e-5
PLY_PROPERTIES = (
    ["x", "y", "z", "nx", "ny", "nz"]
    + [f"f_dc_{i}" for i in range(3)]
    + [f"f_rest_{i}" for i in range(45)]
    + ["opacity"]
    + [f"scale_{i}" for i in range(3)]
    + [f"rot_{i}" for i in range(4)]
)


@dataclass(frozen=True)
class Unmasked:
    states: tuple[int, ...]
    plain: np.ndarray  # (words, lanes) uint8
    rows: np.ndarray | None  # (rows, 27) float32 when the plaintext is a whole number of rows
    unit_quaternions: int

    @property
    def is_splat(self) -> bool:
        """Every row has a unit quaternion and every value is finite."""
        return (
            self.rows is not None
            and self.unit_quaternions == len(self.rows)
            and bool(np.isfinite(self.rows).all())
        )


def unmask(container: Container, states: tuple[int, ...] | None = None) -> Unmasked:
    """Unmask with the given states, or with the key embedded in the separators."""
    states = states or container.embedded_key()
    if states is None:
        raise Error("no embedded key (one run of 8 separators that are not A5); give the states")
    plain = lfsr.unmask(container.payload, states)
    floats = np.frombuffer(plain.tobytes(), "<f4")
    if len(floats) % FIELDS:
        return Unmasked(states, plain, None, 0)
    rows = floats.reshape(-1, FIELDS)
    with np.errstate(over="ignore", invalid="ignore"):  # a wrong key gives huge or NaN floats
        norm = (rows[:, ROTATION].astype(np.float64) ** 2).sum(axis=1)
    return Unmasked(states, plain, rows, int((np.abs(norm - 1) < UNIT_TOLERANCE).sum()))


def ply(unmasked: Unmasked) -> bytes:
    """A 3DGS PLY: the one colour channel is copied to RGB, and the normals are zero."""
    if not unmasked.is_splat:
        raise Error("not a valid splat, so no PLY was written; check the states")
    rows = unmasked.rows
    body = np.hstack(
        [
            rows[:, POSITION],
            np.zeros((len(rows), 3), "<f4"),  # normals
            np.repeat(rows[:, DC], 3, axis=1),  # f_dc, RGB
            np.tile(rows[:, SH_REST], 3),  # f_rest is channel-major: 15 coefficients per channel
            rows[:, OPACITY],
            rows[:, SCALE],
            rows[:, ROTATION],
        ]
    )
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        "comment btcx file 62, monochrome splat; RGB copied from one channel, zero normals\n"
        f"element vertex {len(rows)}\n"
        + "".join(f"property float {n}\n" for n in PLY_PROPERTIES)
        + "end_header\n"
    )
    return header.encode() + body.astype("<f4").tobytes()
