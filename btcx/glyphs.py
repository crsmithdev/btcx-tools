"""003_state.bin, "the writing file": a base-60 stroke library, signs and placements.

Layout (found by players in btcx-files #5 and #15; field meanings below are inferred):
23 rows x 5 lanes x 60 bytes. Byte 0 of each 60-byte block is a header; the rest of each
lane, joined over the rows, is one stream. Records run across the 5 streams in parallel.
Each record ID is (lane1[0], lane2[0]).

type 50  stroke     lane0/lane1[2:-1] = dx+30 / dy+30, lane2[2:-1] = pen (0 move, 1 draw),
                    lane3[2:-1] = width (3-8), lane2[1] / lane3[1] = bounding width / height
type 51  sign       column 2 = sign header; columns 3..-2 each place one stroke:
                    (lane0, lane1) = stroke ID, (lane2, lane3) = x, y in a 60 x 60 cell,
                    lane4 = 0-7 (meaning unknown)
type 52  placement  (lane0[1], lane1[1]) = sign ID, lane2[1] = row 0-6, lane2[2] = baseline
type 49  ruler      eight tables, purpose unknown
type 48  one record, purpose unknown
"""

from itertools import accumulate


def records(data: bytes):
    if len(data) != 6900:
        raise ValueError("003_state.bin is 6900 bytes")
    streams = [b"".join(data[r * 300 + l * 60 + 1:r * 300 + l * 60 + 60] for r in range(23))
               for l in range(5)]
    off, out = 0, []
    s0 = streams[0]
    while s0[off] != 59:
        op = s0[off]
        if op == 52:
            n = 4
        elif op in (50, 51):
            n = 3 + s0[off + 1] + (op == 51)
        elif op == 49:
            n = s0.index(58, off + 2) - off + 1
        else:
            n = 5
        rec = [list(s[off:off + n]) for s in streams]
        if rec[4][-1] != sum(sum(l[:-1]) for l in rec) % 60:
            raise ValueError(f"checksum fails at record {len(out)}")
        out.append(rec)
        off += n
    return out


def parse(data: bytes):
    recs = records(data)
    strokes, signs, places = {}, {}, []
    for i, r in enumerate(recs):
        rid = (r[1][0], r[2][0])
        if r[0][0] == 50:
            xs = [0] + list(accumulate(v - 30 for v in r[0][3:-1]))
            ys = [0] + list(accumulate(v - 30 for v in r[1][3:-1]))
            strokes[rid] = dict(rec=i, pts=list(zip(xs, ys, r[2][2:-1], r[3][2:-1])),
                                w=r[2][1], h=r[3][1])
        elif r[0][0] == 51:
            parts = [dict(stroke=(r[0][c], r[1][c]), x=r[2][c], y=r[3][c], k=r[4][c])
                     for c in range(3, len(r[0]) - 1)]
            signs[rid] = dict(rec=i, parts=parts, head=[r[l][2] for l in range(5)])
        elif r[0][0] == 52:
            places.append(dict(rec=i, sign=(r[0][1], r[1][1]), row=r[2][1], base=r[2][2],
                               a=r[0][2], b=r[3][1], c=r[4][1]))
    return strokes, signs, places


def _paths(stroke, ox, oy, scale):
    d, out = "", []
    for x, y, pen, w in stroke["pts"]:
        X, Y = ox + x * scale, oy + y * scale
        if pen == 0 or not d:
            if d:
                out.append(d)
            d = f"M{X:.1f},{Y:.1f}"
        else:
            d += f" L{X:.1f},{Y:.1f}"
    out.append(d)
    width = sum(p[3] for p in stroke["pts"]) / len(stroke["pts"]) * scale * 0.4
    return "".join(f'<path d="{p}" fill="none" stroke="currentColor" stroke-width="{width:.1f}" '
                   'stroke-linecap="round" stroke-linejoin="round"/>' for p in out)


def _sign(signs, strokes, sid, ox, oy, scale):
    return "".join(_paths(strokes[p["stroke"]], ox + p["x"] * scale, oy + p["y"] * scale, scale)
                   for p in signs[sid]["parts"] if p["stroke"] in strokes)


def _svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'style="background:#f4f1ea;color:#222;font:10px monospace">{body}</svg>\n')


def sheet_signs(strokes, signs, cell=90, cols=11):
    body = ""
    for n, (sid, s) in enumerate(sorted(signs.items(), key=lambda kv: kv[1]["rec"])):
        ox, oy = (n % cols) * cell, (n // cols) * cell
        body += f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="none" stroke="#ccc"/>'
        body += _sign(signs, strokes, sid, ox + 10, oy + 8, 1.15)
        body += f'<text x="{ox + 3}" y="{oy + cell - 3}" fill="#999">r{s["rec"]}</text>'
    rows = -(-len(signs) // cols)
    return _svg(cols * cell, rows * cell, body)


def sheet_strokes(strokes, cell=60, cols=11):
    body = ""
    for n, (sid, s) in enumerate(sorted(strokes.items(), key=lambda kv: kv[1]["rec"])):
        ox, oy = (n % cols) * cell, (n // cols) * cell
        xs = [p[0] for p in s["pts"]]
        ys = [p[1] for p in s["pts"]]
        body += f'<rect x="{ox}" y="{oy}" width="{cell}" height="{cell}" fill="none" stroke="#ccc"/>'
        body += _paths(s, ox + 30 - (min(xs) + max(xs)) * 1.5, oy + 26 - (min(ys) + max(ys)) * 1.5, 3)
        body += f'<text x="{ox + 3}" y="{oy + cell - 3}" fill="#999">r{s["rec"]}</text>'
    return _svg(cols * cell, -(-len(strokes) // cols) * cell, body)


def sheet_rows(strokes, signs, places, cell=70):
    """The 7 rows. Order inside a row is file order: no field is known to give x."""
    rows = {}
    for p in places:
        rows.setdefault(p["row"], []).append(p)
    width = max(len(v) for v in rows.values()) * cell + 40
    body = ""
    for r in range(7):
        oy = r * (cell + 14)
        body += f'<text x="4" y="{oy + cell / 2}" fill="#999">{r}</text>'
        for n, p in enumerate(rows.get(r, [])):
            if p["sign"] in signs:
                body += _sign(signs, strokes, p["sign"], 30 + n * cell, oy + 4, 0.95)
    return _svg(width, 7 * (cell + 14), body)
