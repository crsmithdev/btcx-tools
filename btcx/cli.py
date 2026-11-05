import argparse
from pathlib import Path

import numpy as np

from . import data, glyphs, keysearch, lfsr, notes, splat
from .container import Container, entropy

OUT = Path("out")


def cmd_fetch(a):
    data.fetch(a.files or None)


def cmd_info(a):
    c = Container(Path(a.file).read_bytes())
    print(f"version     0x{c.version:02X}")
    print(f"records     {c.count} (+{c.tail} trailing bytes)")
    print("lane entropy " + "  ".join(f"{entropy(c.payload[:, l]):.3f}" for l in range(4))
          + "  bits/byte")
    an = c.anomalies()
    print(f"separators  {sum(len(b) for _, b in an)} not A5, in {len(an)} runs")
    for start, b in an[:12]:
        print(f"  record {start:>9}  {b.hex(' ').upper()}")
    if len(an) == 1 and len(an[0][1]) == 8:
        s = lfsr.states_from_anomaly(an[0][1])
        print("  as LFSR states (XOR A5, LE pairs): " + " ".join(f"{x:04X}" for x in s))
    for lo, hi in c.base60_regions():
        print(f"base-60     words {lo}..{hi} (lanes 0-1 all < 60)")


def cmd_unmask(a):
    c = Container(Path(a.file).read_bytes())
    if a.states:
        states = tuple(int(s, 16) for s in a.states.split(","))
    else:
        an = c.anomalies()
        if len(an) != 1 or len(an[0][1]) != 8:
            raise SystemExit("no single 8-byte separator anomaly to read a key from; pass --states")
        states = lfsr.states_from_anomaly(an[0][1])
    plain = lfsr.unmask(c.payload, states)
    print("states", " ".join(f"{s:04X}" for s in states), f"| entropy {entropy(plain):.3f}")
    OUT.mkdir(exist_ok=True)
    stem = OUT / Path(a.file).stem
    Path(f"{stem}.unmasked.bin").write_bytes(plain.tobytes())
    try:
        r = splat.rows(plain)
    except ValueError as e:
        print(f"not splat-shaped: {e}")
        return
    err = splat.quaternion_error(r)
    ok = int((err < 1e-5).sum())
    print(f"splat rows  {len(r)} x 27 float32, unit quaternions {ok}/{len(r)}, "
          f"finite {np.isfinite(r).all()}")
    if a.ply and ok == len(r):
        splat.save_ply(f"{stem}.ply", r)
        print(f"wrote {stem}.ply")


def cmd_glyphs(a):
    st, sg, pl = glyphs.parse(Path(a.file).read_bytes())
    refs = [p["stroke"] for s in sg.values() for p in s["parts"]]
    print(f"strokes {len(st)}  signs {len(sg)}  placements {len(pl)}  "
          f"stroke refs resolved {sum(r in st for r in refs)}/{len(refs)}  "
          f"sign refs resolved {sum(p['sign'] in sg for p in pl)}/{len(pl)}")
    OUT.mkdir(exist_ok=True)
    for name, svg in (("strokes", glyphs.sheet_strokes(st)), ("signs", glyphs.sheet_signs(st, sg)),
                      ("rows", glyphs.sheet_rows(st, sg, pl))):
        (OUT / f"003_{name}.svg").write_text(svg)
        print(f"wrote {OUT / f'003_{name}.svg'}")


def cmd_keysearch(a):
    c = Container(Path(a.file).read_bytes())
    start = a.start
    ct = c.payload[start:start + a.sample]
    print(f"words {start}..{start + len(ct)}, {a.sample} sampled, B400 LFSR, all 65535 phases")
    for lane in range(4):
        scores = keysearch.scan_lane(ct[:, lane], len(ct))
        top, med = keysearch.best(scores)
        p, e, z = top[0]
        state = keysearch.state_at(p, start)
        flag = "  <-- outlier" if z > a.z else ""
        print(f"lane {lane}: best entropy {e:.3f} vs median {med:.3f}, z {z:.1f}, "
              f"state at word 0 {state:04X}{flag}")


def cmd_notes(a):
    db = str(OUT / "notes.sqlite")
    OUT.mkdir(exist_ok=True)
    if a.action == "build":
        n = notes.build(data.path("index.html").read_text(encoding="utf8"), db)
        print(f"{n} passages -> {db}")
    elif a.action == "search":
        for k, t, s, x, u in notes.search(db, a.term):
            print(f"{k}:{t:<6} {s[:28]:<28} {x}\n{'':>8}{u}")
    elif a.action == "pairs":
        for w, files, lines in notes.pairs(db, a.max_files)[: a.limit]:
            print(f"\n{w}  ({', '.join(files)})")
            for k, t, x, u, cited in lines:
                print(f"  {'cited ' if cited else 'NEW   '}{k}:{t:<6} {x[:90]}")


def main():
    p = argparse.ArgumentParser(prog="btcx", description=__doc__)
    sub = p.add_subparsers(required=True)
    s = sub.add_parser("fetch", help="download the published files at the pinned commit")
    s.add_argument("files", nargs="*")
    s.set_defaults(fn=cmd_fetch)
    s = sub.add_parser("info", help="header, framing, separator anomalies, entropy")
    s.add_argument("file")
    s.set_defaults(fn=cmd_info)
    s = sub.add_parser("unmask", help="XOR the payload with the B400 LFSR; export a splat")
    s.add_argument("file")
    s.add_argument("--states", help="four hex states, e.g. 1F25,02D2,6089,B161")
    s.add_argument("--ply", action="store_true")
    s.set_defaults(fn=cmd_unmask)
    s = sub.add_parser("glyphs", help="render 003_state.bin strokes, signs and rows as SVG")
    s.add_argument("file")
    s.set_defaults(fn=cmd_glyphs)
    s = sub.add_parser("keysearch", help="blind search of every LFSR phase per lane")
    s.add_argument("file")
    s.add_argument("--start", type=int, default=0, help="first payload word")
    s.add_argument("--sample", type=int, default=4096)
    s.add_argument("--z", type=float, default=8.0, help="outlier threshold")
    s.set_defaults(fn=cmd_keysearch)
    s = sub.add_parser("notes", help="index and query the creator's notes page")
    s.add_argument("action", choices=["build", "search", "pairs"])
    s.add_argument("term", nargs="?")
    s.add_argument("--max-files", type=int, default=3)
    s.add_argument("--limit", type=int, default=40)
    s.set_defaults(fn=cmd_notes)
    a = p.parse_args()
    a.fn(a)
