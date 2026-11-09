"""The renderer on a few Gaussians at known positions, and the render command on file 62."""

import sys
import zlib

import numpy as np

from btcx import data, render, splat
from btcx.cli import main

SIZE = (33, 33)  # odd, so the principal point is the centre of pixel (16, 16)
FOCAL = SIZE[1] / 2 / np.tan(np.radians(render.FOV) / 2)
WHITE, BLACK = 0.5 / render.SH_C0, -0.5 / render.SH_C0  # DC coefficients for grey 1 and grey 0


def row(position, dc=WHITE):
    """A splat row: a round Gaussian of scale 0.05, opaque, rotation 1, grey from the DC term only."""
    fields = np.zeros(splat.FIELDS)
    fields[splat.POSITION] = position
    fields[splat.SCALE] = np.log(0.05)
    fields[splat.ROTATION] = (1, 0, 0, 0)
    fields[splat.OPACITY] = 10
    fields[splat.DC] = dc
    return fields


def draw(*rows):
    return render.render(np.array(rows), SIZE, render.FOV, (0, 0, 0), (0, 0, 1))


def box(image):
    """Inclusive (top, bottom, left, right) of the pixels that are not black."""
    ys, xs = np.nonzero(image)
    return ys.min(), ys.max(), xs.min(), xs.max()


def test_centre():
    image = draw(row((0, 0, 5)))
    assert image[16, 16] == np.float64(render.ALPHA_MAX)
    assert box(image) == (14, 18, 14, 18)


def test_axes():
    """x is right and y is down."""
    shift = round(16 + FOCAL * 0.2)
    assert np.unravel_index(draw(row((1, 0, 5))).argmax(), SIZE) == (16, shift)
    assert np.unravel_index(draw(row((0, 1, 5))).argmax(), SIZE) == (shift, 16)


def test_front_to_back():
    """The near black Gaussian hides the far white one, whatever their order in the rows."""
    near, far = row((0, 0, 4), BLACK), row((0, 0, 6))
    image = draw(far, near)
    assert np.isclose(image[16, 16], (1 - render.ALPHA_MAX) * render.ALPHA_MAX)
    assert np.array_equal(image, draw(near, far))


def test_near_plane():
    assert not draw(row((0, 0, render.NEAR / 2))).any()


def test_sh_sign():
    """The degree-1 x term is -C1 * x * sh3, with x from the eye to the Gaussian."""
    fields = row((3, 0, 4), 0)
    fields[splat.SH_REST.start + 2] = 1
    assert np.isclose(render.grey(fields[None], np.zeros(3))[0], 0.5 - render.SH_C1 * 0.6)


def test_png():
    image = np.linspace(0, 1, 12).reshape(3, 4)
    body = render.png(image)
    assert body.startswith(b"\x89PNG\r\n\x1a\n")
    raw = np.frombuffer(zlib.decompress(body[body.index(b"IDAT") + 4 : -16]), np.uint8).reshape(3, 5)
    assert np.array_equal(raw[:, 1:], np.round(image * 255))


def test_file_62(monkeypatch):
    out = data.OUT / "test-render.png"
    monkeypatch.setattr(sys, "argv", ["btcx", "render", "--size", "64x48", "--out", out.name])
    main()
    assert out.read_bytes().startswith(b"\x89PNG")
    out.unlink()
