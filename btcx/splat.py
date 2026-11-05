"""File 62's unmasked payload read as 3D Gaussian splat records of 27 float32.

Field layout (inferred by players in btcx-files #5/#12, not given by the author):
0-2 position, 3-5 log scale, 6-9 rotation quaternion, 10 opacity logit,
11 DC colour (one channel), 12-26 SH rest (one channel, degree 3).
"""

import numpy as np

FIELDS = 27


def rows(payload: np.ndarray) -> np.ndarray:
    f = np.frombuffer(payload.tobytes(), "<f4")
    if len(f) % FIELDS:
        raise ValueError(f"{len(f)} floats is not a multiple of {FIELDS}")
    return f.reshape(-1, FIELDS)


def quaternion_error(r: np.ndarray) -> np.ndarray:
    return np.abs((r[:, 6:10].astype(np.float64) ** 2).sum(1) - 1)


def save_ply(path, r: np.ndarray):
    names = (["x", "y", "z", "nx", "ny", "nz"] + [f"f_dc_{i}" for i in range(3)]
             + [f"f_rest_{i}" for i in range(45)] + ["opacity"]
             + [f"scale_{i}" for i in range(3)] + [f"rot_{i}" for i in range(4)])
    p = np.zeros((len(r), len(names)), "<f4")
    p[:, 0:3] = r[:, 0:3]
    p[:, 6:9] = r[:, 11:12]  # one gray channel copied to RGB
    for c in range(3):
        p[:, 9 + 15 * c:24 + 15 * c] = r[:, 12:27]
    p[:, 54] = r[:, 10]
    p[:, 55:58] = r[:, 3:6]
    p[:, 58:62] = r[:, 6:10]
    header = ("ply\nformat binary_little_endian 1.0\n"
              "comment btcx file 62, monochrome splat; RGB copied from one channel, zero normals\n"
              f"element vertex {len(r)}\n" + "".join(f"property float {n}\n" for n in names)
              + "end_header\n")
    with open(path, "wb") as out:
        out.write(header.encode())
        out.write(p.tobytes())
