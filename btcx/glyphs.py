"""003_state.bin, "the writing file": a base-60 stroke library, signs and placements.

Layout (found by players in btcx-files #5 and #15; field meanings are inferred):
23 rows x 5 lanes x 60 bytes. Byte 0 of each 60-byte block is a header; the rest of each
lane, joined over the rows, is one stream. A record runs across the 5 streams in parallel
and ends with a checksum: the sum of every other byte of the record, mod 60.
A record ID is (lane1[0], lane2[0]).

type 50  stroke     lane0/lane1[2:-1] = dx+30 / dy+30, lane2[2:-1] = pen (0 move, 1 draw),
                    lane3[2:-1] = width (3-8)
type 51  sign       columns 3..-2 each place one stroke: (lane0, lane1) = stroke ID,
                    (lane2, lane3) = x, y in a 60 x 60 cell, lane4 = 0-7 (meaning unknown)
type 52  placement  (lane0[1], lane1[1]) = sign ID, lane2[1] = row
type 49  ruler      ends at the first 58 in lane 0; purpose unknown
type 48  one record, purpose unknown
59       end of the records
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from itertools import accumulate

import numpy as np

from . import Error

ROWS, LANES, BLOCK = 23, 5, 60
SIZE = ROWS * LANES * BLOCK
STROKE, SIGN, PLACEMENT, RULER, END = 50, 51, 52, 49, 59
RULER_END = 58
CHECKSUM_MOD = 60
DELTA = 30  # stroke steps are stored as d + 30
SHEET_COLS = 11
STROKE_CELL, STROKE_SCALE = 60, 3
SIGN_CELL, SIGN_SCALE = 90, 1.15
ROW_CELL, ROW_SCALE, ROW_GAP = 70, 0.95, 14

Id = tuple[int, int]


@dataclass(frozen=True)
class Stroke:
    rec: int
    points: list[tuple[int, int, int, int]]  # x, y, pen, width


@dataclass(frozen=True)
class Part:
    stroke: Id
    x: int
    y: int


@dataclass(frozen=True)
class Sign:
    rec: int
    parts: list[Part]


@dataclass(frozen=True)
class Placement:
    sign: Id
    row: int


@dataclass(frozen=True)
class Glyphs:
    types: dict[int, int]  # record type -> count
    strokes: dict[Id, Stroke]
    signs: dict[Id, Sign]
    placements: list[Placement]

    def stroke_references(self) -> list[Id]:
        return [part.stroke for sign in self.signs.values() for part in sign.parts]

    def unresolved(self) -> tuple[int, int]:
        """Stroke references in signs, and sign references in placements, that match no record."""
        strokes = sum(ref not in self.strokes for ref in self.stroke_references())
        signs = sum(p.sign not in self.signs for p in self.placements)
        return strokes, signs


def _records(data: bytes) -> list[list[list[int]]]:
    if len(data) != SIZE:
        raise Error(f"not 003_state.bin: expected {SIZE} bytes, got {len(data):,}")
    blocks = np.frombuffer(data, np.uint8).reshape(ROWS, LANES, BLOCK)[:, :, 1:]  # drop block headers
    streams = [blocks[:, lane].tobytes() for lane in range(LANES)]
    lane0, off, out = streams[0], 0, []
    while lane0[off] != END:
        kind = lane0[off]
        if kind == PLACEMENT:
            n = 4
        elif kind in (STROKE, SIGN):
            n = 3 + lane0[off + 1] + (kind == SIGN)
        elif kind == RULER:
            n = lane0.find(RULER_END, off + 2) - off + 1
        else:
            n = 5
        if n < 1 or off + n >= len(lane0):
            raise Error(f"not 003_state.bin: record {len(out)} runs past the end of the stream")
        rec = [list(s[off : off + n]) for s in streams]
        if rec[4][-1] != sum(sum(lane[:-1]) for lane in rec) % CHECKSUM_MOD:
            raise Error(f"not 003_state.bin: checksum fails at record {len(out)}")
        out.append(rec)
        off += n
    return out


def parse(data: bytes) -> Glyphs:
    recs = _records(data)
    if not recs:
        raise Error("not 003_state.bin: it holds no records")
    strokes, signs, placements = {}, {}, []
    for i, r in enumerate(recs):
        rid = (r[1][0], r[2][0])
        if r[0][0] == STROKE:
            xs = accumulate(v - DELTA for v in r[0][2:-1])
            ys = accumulate(v - DELTA for v in r[1][2:-1])
            strokes[rid] = Stroke(i, list(zip(xs, ys, r[2][2:-1], r[3][2:-1], strict=True)))
        elif r[0][0] == SIGN:
            parts = [Part((r[0][c], r[1][c]), r[2][c], r[3][c]) for c in range(3, len(r[0]) - 1)]
            signs[rid] = Sign(i, parts)
        elif r[0][0] == PLACEMENT:
            placements.append(Placement((r[0][1], r[1][1]), r[2][1]))
    return Glyphs(dict(Counter(r[0][0] for r in recs)), strokes, signs, placements)


def _paths(stroke: Stroke, ox: float, oy: float, scale: float) -> str:
    path, out = "", []
    for x, y, pen, _ in stroke.points:
        point = f"{ox + x * scale:.1f},{oy + y * scale:.1f}"
        if pen == 0 or not path:
            if path:
                out.append(path)
            path = f"M{point}"
        else:
            path += f" L{point}"
    out.append(path)
    width = sum(p[3] for p in stroke.points) / len(stroke.points) * scale * 0.4
    return "".join(
        f'<path d="{p}" fill="none" stroke="currentColor" stroke-width="{width:.1f}" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        for p in out
    )


def _sign(glyphs: Glyphs, sign: Sign, ox: float, oy: float, scale: float) -> str:
    return "".join(
        _paths(glyphs.strokes[part.stroke], ox + part.x * scale, oy + part.y * scale, scale)
        for part in sign.parts
        if part.stroke in glyphs.strokes
    )


def _svg(width: float, height: float, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="background:#f4f1ea;color:#222;font:10px monospace">{body}</svg>\n'
    )


def _grid(items: list, cell: int, draw: Callable[[object, int, int], str]) -> str:
    """One labelled cell per item, SHEET_COLS to a row, in record order."""
    body = ""
    for n, item in enumerate(sorted(items, key=lambda item: item.rec)):
        ox, oy = (n % SHEET_COLS) * cell, (n // SHEET_COLS) * cell
        body += (
            f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="none" stroke="#ccc"/>'
            f'<text x="{ox + 3}" y="{oy + cell - 3}" fill="#999">r{item.rec}</text>'
        )
        body += draw(item, ox, oy)
    return _svg(SHEET_COLS * cell, -(-len(items) // SHEET_COLS) * cell, body)


def sheet_strokes(glyphs: Glyphs) -> str:
    cell, scale = STROKE_CELL, STROKE_SCALE

    def draw(stroke: Stroke, ox: int, oy: int) -> str:
        xs, ys = [p[0] for p in stroke.points], [p[1] for p in stroke.points]
        mid_x, mid_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        return _paths(stroke, ox + cell / 2 - mid_x * scale, oy + cell / 2 - 4 - mid_y * scale, scale)

    return _grid(list(glyphs.strokes.values()), cell, draw)


def sheet_signs(glyphs: Glyphs) -> str:
    return _grid(
        list(glyphs.signs.values()),
        SIGN_CELL,
        lambda sign, ox, oy: _sign(glyphs, sign, ox + 10, oy + 8, SIGN_SCALE),
    )


def sheet_rows(glyphs: Glyphs) -> str:
    """The placements by row. Order inside a row is file order: no known field gives x."""
    cell = ROW_CELL
    rows: dict[int, list[Placement]] = {}
    for p in glyphs.placements:
        rows.setdefault(p.row, []).append(p)
    count = max(rows, default=-1) + 1
    body = ""
    for r in range(count):
        oy = r * (cell + ROW_GAP)
        body += f'<text x="4" y="{oy + cell / 2}" fill="#999">{r}</text>'
        for n, p in enumerate(rows.get(r, [])):
            if p.sign in glyphs.signs:
                body += _sign(glyphs, glyphs.signs[p.sign], 30 + n * cell, oy + 4, ROW_SCALE)
    width = max((len(v) for v in rows.values()), default=0) * cell + 40
    return _svg(width, count * (cell + ROW_GAP), body)
