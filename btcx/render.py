"""Draw file 62's splat rows to a grey image with the 3DGS reference rasterizer, in numpy.

The camera conventions come from Helo3301, https://github.com/suebtwist/btcx-files/issues/12
(comment of 2026-11-04): OpenCV axes (x right, y down, z forward, up = -y), a pinhole camera with
square pixels and the principal point at the image centre, near plane 0.2, and the capture view
960 x 720 with a vertical FOV of 38 degrees from the origin to the aim (-0.105, 0.015, 1).
The reference tests each pixel of each 16 x 16 tile that a Gaussian's box touches; this module
tests only the pixels in the box, so a few faint edge pixels can differ.

Throughout this module we have:
  cam    a position in camera coordinates (x right, y down, z forward)
  px, py pixel coordinates; pixel (0, 0) has its centre at the top-left integer point
  conic  the inverse [[a, b], [b, c]] of the 2D covariance, kept as (a, b, c)
"""

import struct
import zlib
from typing import NamedTuple

import numpy as np

from .splat import DC, OPACITY, POSITION, ROTATION, SCALE, SH_REST

SIZE = (960, 720)
FOV = 38.0
EYE = (0.0, 0.0, 0.0)
AIM = (-0.105, 0.015, 1.0)
UP = np.array([0.0, -1.0, 0.0])
NEAR = 0.2

# The constants of the 3DGS reference (diff-gaussian-rasterization, forward.cu)
DILATION = 0.3  # added to the 2D covariance diagonal, a low-pass filter of about one pixel
FRUSTUM = 1.3  # x/z and y/z are clamped to 1.3 times the half FOV tangent in the Jacobian
ALPHA_MIN, ALPHA_MAX = 1 / 255, 0.99
LOG_T_MIN = np.log(1e-4)  # a pixel stops blending before its transmittance goes below 1e-4
CHUNK = 1 << 22  # pixel tests per blend step, to bound memory
SH_C0 = 0.28209479177387814
SH_C1 = 0.4886025119029199
SH_C2 = (
    1.0925484305920792,
    -1.0925484305920792,
    0.31539156525252005,
    -1.0925484305920792,
    0.5462742152960396,
)
SH_C3 = (
    -0.5900435899266435,
    2.890611442640554,
    -0.4570457994644658,
    0.3731763325901154,
    -0.4570457994644658,
    1.445305721320277,
    -0.5900435899266435,
)


def look(eye: np.ndarray, aim: np.ndarray) -> np.ndarray:
    """World-to-camera rotation whose rows are the camera's right, down and forward axes."""
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(-UP, forward)
    right /= np.linalg.norm(right)
    return np.stack([right, np.cross(forward, right), forward])


def basis(dirs: np.ndarray) -> np.ndarray:
    """The 16 real SH basis values of degree 0-3 at unit directions, with the 3DGS signs."""
    dx, dy, dz = dirs.T
    xx, yy, zz = dx * dx, dy * dy, dz * dz
    return np.stack(
        [
            np.full_like(dx, SH_C0),
            -SH_C1 * dy,
            SH_C1 * dz,
            -SH_C1 * dx,
            SH_C2[0] * dx * dy,
            SH_C2[1] * dy * dz,
            SH_C2[2] * (2 * zz - xx - yy),
            SH_C2[3] * dx * dz,
            SH_C2[4] * (xx - yy),
            SH_C3[0] * dy * (3 * xx - yy),
            SH_C3[1] * dx * dy * dz,
            SH_C3[2] * dy * (4 * zz - xx - yy),
            SH_C3[3] * dz * (2 * zz - 3 * xx - 3 * yy),
            SH_C3[4] * dx * (4 * zz - xx - yy),
            SH_C3[5] * dz * (xx - yy),
            SH_C3[6] * dx * (xx - 3 * yy),
        ],
        axis=1,
    )


def grey(rows: np.ndarray, eye: np.ndarray) -> np.ndarray:
    """The grey level of each splat row seen from the eye: SH + 0.5, clamped at 0."""
    dirs = rows[:, POSITION] - eye
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    coefficients = np.hstack([rows[:, DC], rows[:, SH_REST]])  # (rows, 16)
    return np.maximum((basis(dirs) * coefficients).sum(axis=1) + 0.5, 0)


def covariances(rows: np.ndarray) -> np.ndarray:
    """The 3D covariance R S S^T R^T of each splat row."""
    qw, qx, qy, qz = (rows[:, ROTATION] / np.linalg.norm(rows[:, ROTATION], axis=1, keepdims=True)).T
    rot = np.stack(
        [
            [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qw * qz), 2 * (qx * qz + qw * qy)],
            [2 * (qx * qy + qw * qz), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qw * qx)],
            [2 * (qx * qz - qw * qy), 2 * (qy * qz + qw * qx), 1 - 2 * (qx * qx + qy * qy)],
        ]
    ).transpose(2, 0, 1)  # (rows, 3, 3)
    rs = rot * np.exp(rows[:, SCALE])[:, None, :]
    return rs @ rs.transpose(0, 2, 1)


class Splats(NamedTuple):
    """The splat rows in front of the near plane, in depth order, projected to the image."""

    centre: np.ndarray  # (rows, 2) px, py
    conic: np.ndarray  # (rows, 3)
    opacity: np.ndarray
    colour: np.ndarray
    lo: np.ndarray  # (rows, 2) first px, py of the box of three standard deviations, clipped to the image
    span: np.ndarray  # (rows, 2) width and height of that box


def project(
    rows: np.ndarray, size: tuple[int, int], fov: float, eye: tuple[float, ...], aim: tuple[float, ...]
) -> Splats:
    """EWA projection of each row to a 2D Gaussian on the image."""
    rows = rows.astype(np.float64)
    eye, aim = np.array(eye), np.array(aim)
    view = look(eye, aim)
    cam = (rows[:, POSITION] - eye) @ view.T
    rows, cam = rows[cam[:, 2] > NEAR], cam[cam[:, 2] > NEAR]
    order = np.argsort(cam[:, 2], kind="stable")
    rows, cam = rows[order], cam[order]

    tan_y = np.tan(np.radians(fov) / 2)
    tan_x = tan_y * size[0] / size[1]
    focal = size[1] / 2 / tan_y
    depth = cam[:, 2]
    tx = np.clip(cam[:, 0] / depth, -FRUSTUM * tan_x, FRUSTUM * tan_x) * depth
    ty = np.clip(cam[:, 1] / depth, -FRUSTUM * tan_y, FRUSTUM * tan_y) * depth
    jac = np.zeros((len(cam), 2, 3))
    jac[:, 0, 0] = jac[:, 1, 1] = focal / depth
    jac[:, 0, 2] = -focal * tx / depth**2
    jac[:, 1, 2] = -focal * ty / depth**2
    tm = jac @ view
    cov = tm @ covariances(rows) @ tm.transpose(0, 2, 1)  # (rows, 2, 2)
    xx, xy, yy = cov[:, 0, 0] + DILATION, cov[:, 0, 1], cov[:, 1, 1] + DILATION
    det = xx * yy - xy * xy
    mid = (xx + yy) / 2
    radius = np.ceil(3 * np.sqrt(mid + np.sqrt(np.maximum(0.1, mid * mid - det))))[:, None]
    centre = focal * cam[:, :2] / depth[:, None] + (np.array(size) - 1) / 2
    lo = np.maximum(np.ceil(centre - radius), 0).astype(np.int64)
    hi = np.minimum(np.floor(centre + radius) + 1, size).astype(np.int64)
    return Splats(
        centre,
        np.stack([yy, -xy, xx], 1) / det[:, None],
        1 / (1 + np.exp(-rows[:, OPACITY][:, 0])),
        grey(rows, eye),
        lo,
        np.maximum(hi - lo, 0),
    )


def render(
    rows: np.ndarray, size: tuple[int, int], fov: float, eye: tuple[float, ...], aim: tuple[float, ...]
) -> np.ndarray:
    """A (height, width) grey image of the splat rows on black, front-to-back alpha blended."""
    splats = project(rows, size, fov, eye, aim)
    counts = np.cumsum(splats.span[:, 0] * splats.span[:, 1])
    parts = np.split(
        np.arange(len(counts)), np.searchsorted(counts, np.arange(CHUNK, counts.max(initial=0), CHUNK))
    )
    image, log_t = np.zeros(size[0] * size[1]), np.zeros(size[0] * size[1])
    for part in parts:
        blend(splats, part, size[0], image, log_t)
    return image.reshape(size[1], size[0])


def blend(splats: Splats, part: np.ndarray, width: int, image: np.ndarray, log_t: np.ndarray) -> None:
    """Blend a depth-ordered run of rows into the image behind the rows before it, and update log_t."""
    lo, span = splats.lo[part], splats.span[part]
    counts = span[:, 0] * span[:, 1]
    at = np.repeat(np.arange(len(part)), counts)
    offset = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    px, py = lo[at, 0] + offset % span[at, 0], lo[at, 1] + offset // span[at, 0]
    pixel = py * width + px
    live = log_t[pixel] >= LOG_T_MIN
    gid, px, py, pixel = part[at[live]], px[live], py[live], pixel[live]

    dx, dy = px - splats.centre[gid, 0], py - splats.centre[gid, 1]
    conic = splats.conic[gid]
    power = -0.5 * (conic[:, 0] * dx * dx + conic[:, 2] * dy * dy) - conic[:, 1] * dx * dy
    alpha = np.minimum(ALPHA_MAX, splats.opacity[gid] * np.exp(power))
    keep = alpha >= ALPHA_MIN
    order = np.argsort(pixel[keep] * len(splats.colour) + gid[keep])  # by pixel, then by depth
    gid, alpha, pixel = gid[keep][order], alpha[keep][order], pixel[keep][order]

    step = np.log1p(-alpha)
    total = np.cumsum(step)
    first = np.diff(pixel, prepend=-1) != 0
    start = np.maximum.accumulate(np.where(first, np.arange(len(pixel)), 0))
    after = log_t[pixel] + total - (total - step)[start]  # log transmittance after each row
    weight = alpha * np.exp(after - step) * (after >= LOG_T_MIN)
    image += np.bincount(pixel, weights=weight * splats.colour[gid], minlength=len(image))
    last = np.diff(pixel, append=-1) != 0
    log_t[pixel[last]] = after[last]


def png(image: np.ndarray) -> bytes:
    """An 8-bit greyscale PNG of a (height, width) image in 0-1."""
    height, width = image.shape
    grey8 = np.round(np.clip(image, 0, 1) * 255).astype(np.uint8)
    raw = np.hstack([np.zeros((height, 1), np.uint8), grey8]).tobytes()  # filter type 0 on each line

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)  # 8-bit greyscale
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
