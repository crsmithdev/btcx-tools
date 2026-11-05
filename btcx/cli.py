"""Analysis tools for the binary files published in btcx-files. Inputs are in data/ and results go to out/."""

import argparse
import json
import sys
from pathlib import Path

from . import Error, data, glyphs, keysearch, lfsr, splat
from .container import LANES, Container
from .findings import FINDINGS

SUPERSPLAT = "https://superspl.at/editor"


def load(path: str) -> bytes:
    """Read an input file and say whether it is a pinned published file."""
    body = Path(path).read_bytes()
    pin = data.pin_of(body)
    print(f"input       {path} ({f'pinned {pin}' if pin else 'not pinned'})")
    return body


def write(name: str, body: bytes | str) -> None:
    data.OUT.mkdir(exist_ok=True)
    path = data.OUT / name
    if isinstance(body, str):
        path.write_text(body)
    else:
        path.write_bytes(body)
    print(f"wrote       {path}")


def cmd_fetch(args: argparse.Namespace) -> None:
    data.fetch(args.names)


def cmd_info(args: argparse.Namespace) -> None:
    container = Container(load(args.file))
    print(f"version     0x{container.version:02X}")
    print(f"records     {container.count:,} (+{container.tail} trailing bytes)")
    lanes = "  ".join(f"{keysearch.byte_entropy(column):.3f}" for column in container.payload.T)
    print(f"entropy     {lanes}  bits/byte, lanes 0-{LANES - 1}")
    runs = container.anomalies()
    print(f"separators  {sum(len(run) for _, run in runs)} not A5, in {len(runs)} runs")
    for start, run in runs[:12]:
        print(f"  record {start:>9,}  {run.hex(' ').upper()}")
    key = container.embedded_key()
    if key:
        print(f"  as LFSR start states (XOR A5, little-endian pairs): {' '.join(lfsr.hex_states(key))}")
    for lo, hi in container.base60_regions():
        print(f"base-60     words {lo}-{hi} (lanes 0-1 all below 60)")


def hex_list(text: str) -> tuple[int, ...]:
    try:
        return tuple(int(s, 16) for s in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a comma-separated list of hex values") from None


def cmd_unmask(args: argparse.Namespace) -> None:
    unmasked = splat.unmask(Container(load(args.file)), args.states)
    source = "given" if args.states else "embedded in the separators"
    print(f"states      {' '.join(lfsr.hex_states(unmasked.states))} ({source})")
    print(f"entropy     {keysearch.byte_entropy(unmasked.plain):.3f} bits/byte")
    if unmasked.rows is None:
        print(f"splat       no: the plaintext is not a whole number of {splat.FIELDS}-float rows")
    else:
        print(
            f"splat       {len(unmasked.rows):,} rows, {unmasked.unit_quaternions:,} unit quaternions, "
            f"{'all' if unmasked.is_splat else 'not all'} finite and unit"
        )
    stem = Path(args.file).stem
    if args.bin:
        write(f"{stem}.unmasked.bin", unmasked.plain.tobytes())
    if args.ply:
        write(f"{stem}.ply", splat.ply(unmasked))
        print(f"next        open it in {SUPERSPLAT}; the colour is one channel copied to RGB")


def cmd_keysearch(args: argparse.Namespace) -> None:
    payload = Container(load(args.file)).payload
    words, lanes = keysearch.search(payload, args.start, args.words, args.z)
    print(
        f"window      words {args.start:,}-{args.start + words - 1:,} ({words:,} words), "
        f"B400 LFSR, all {lfsr.PERIOD:,} phases per lane"
    )
    for i, lane in enumerate(lanes):
        print(
            f"lane {i}      best entropy {lane.entropy:.3f}, median {lane.median:.3f}, z {lane.z:.1f}, "
            f"start state {lane.state:04X}{'  outlier' if lane.outlier else ''}"
        )


def cmd_glyphs(args: argparse.Namespace) -> None:
    parsed = glyphs.parse(load(args.file))
    strokes, signs = parsed.unresolved()
    print(
        f"records     {sum(parsed.types.values())}: {len(parsed.strokes)} strokes, "
        f"{len(parsed.signs)} signs, {len(parsed.placements)} placements"
    )
    print(f"unresolved  {strokes} stroke references, {signs} sign references")
    stem = Path(args.file).stem
    write(f"{stem}.strokes.svg", glyphs.sheet_strokes(parsed))
    write(f"{stem}.signs.svg", glyphs.sheet_signs(parsed))
    write(f"{stem}.rows.svg", glyphs.sheet_rows(parsed))
    print("next        open the SVGs in a browser")


def cmd_verify(args: argparse.Namespace) -> None:
    results = []
    for f in FINDINGS:
        r = f.check()
        results.append(r)
        if not args.json:
            print(f"{'PASS' if r['pass'] else 'FAIL'}  {f.id:<20} {f.claim}")
            print(f"{'':6}{f.credit}, {f.link}")
            if not r["pass"]:
                print(f"{'':6}expected {json.dumps(f.expected)}\n{'':6}observed {json.dumps(r['observed'])}")
    if args.json:
        print(json.dumps(results, indent=2))
    failed = sum(not r["pass"] for r in results)
    if failed:
        raise Error(f"{failed} of {len(results)} findings did not reproduce")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="btcx", description=__doc__)
    sub = root.add_subparsers(required=True, metavar="COMMAND")

    cmd = sub.add_parser("fetch", help="download the published inputs to data/ and check their SHA-256")
    cmd.add_argument("names", nargs="*", metavar="NAME", help="inputs to fetch (default: all)")
    cmd.set_defaults(fn=cmd_fetch)

    cmd = sub.add_parser("verify", help="reproduce each published finding from the pinned inputs")
    cmd.add_argument("--json", action="store_true", help="print the results as JSON")
    cmd.set_defaults(fn=cmd_verify)

    cmd = sub.add_parser("info", help="header, records, separator anomalies, entropy, base-60 regions")
    cmd.add_argument("file", help="a BTCX container, e.g. data/306_state.bin")
    cmd.set_defaults(fn=cmd_info)

    cmd = sub.add_parser("unmask", help="XOR each payload lane with the B400 LFSR; check it as a splat")
    cmd.add_argument("file", help="a BTCX container, e.g. data/20180208_1142.bin (file 62)")
    cmd.add_argument(
        "--states",
        type=hex_list,
        help="one hex start state per lane, e.g. 1F25,02D2,6089,B161 (default: the embedded key)",
    )
    cmd.add_argument("--ply", action="store_true", help="write out/<file>.ply for a splat viewer")
    cmd.add_argument(
        "--bin", action="store_true", help="write the unmasked payload to out/<file>.unmasked.bin"
    )
    cmd.set_defaults(fn=cmd_unmask)

    cmd = sub.add_parser("keysearch", help="try every B400 LFSR phase on each lane; a key is an outlier")
    cmd.add_argument("file", help="a BTCX container")
    cmd.add_argument("--start", type=int, default=0, help="first payload word of the window (default 0)")
    cmd.add_argument(
        "--words",
        type=int,
        default=keysearch.WINDOW,
        help=f"window length, at most {lfsr.PERIOD:,} (default {keysearch.WINDOW:,})",
    )
    cmd.add_argument(
        "--z",
        type=float,
        default=keysearch.OUTLIER_Z,
        help=f"z above which a phase is an outlier (default {keysearch.OUTLIER_Z:g})",
    )
    cmd.set_defaults(fn=cmd_keysearch)

    cmd = sub.add_parser("glyphs", help="parse 003_state.bin and render its strokes, signs and rows as SVG")
    cmd.add_argument("file", help="data/003_state.bin")
    cmd.set_defaults(fn=cmd_glyphs)

    return root


def main() -> None:
    args = parser().parse_args()
    try:
        args.fn(args)
    except Error as e:
        sys.exit(f"btcx: {e}")
    except OSError as e:
        sys.exit(f"btcx: {e.filename}: {e.strerror}" if e.filename else f"btcx: {e}")
