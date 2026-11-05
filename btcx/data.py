"""Published btcx-files at a pinned commit, checked by SHA-256."""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

COMMIT = "2d55483e2ad991c4cb9f4dd341d67d0258610b7c"
BASE = f"https://raw.githubusercontent.com/suebtwist/btcx-files/{COMMIT}/"
DATA = Path("data")

FILES = {
    "003_state.bin": "2d0863b4f8bc9605e012f0ea8782f9bda6da5365465d492dcc27990237e54374",
    "306_state.bin": "d5c379bc98667f7274a8b87f006ff6ce1425a7d3f500a12373a85def931946e9",
    "20180208_1142.bin": "c945b02e56ee9ecc649149c854f235cfd305a896d86e38a334a97f6111e57fae",
    "20180213_0417_8k.bin": "d5fc3ac52552b7c5f48115481664d562a11c079ba7618aad8d4ddb9fa7ea1f3c",
    "20180219_2258_8k.bin": "26973b90ace2f091882bc0300ee62404e5a3329e5e3caf9496933f902b7c1b53",
    "index.html": None,  # the notes page changes often; no pin
}


def fetch(names=None):
    DATA.mkdir(exist_ok=True)
    for name in names or FILES:
        path = DATA / name
        want = FILES[name]
        if path.exists() and (want is None or sha256(path.read_bytes()).hexdigest() == want):
            print(f"ok      {name}")
            continue
        url = BASE + name if want else f"https://raw.githubusercontent.com/suebtwist/btcx-files/main/{name}"
        body = urlopen(url).read()
        got = sha256(body).hexdigest()
        if want and got != want:
            raise SystemExit(f"{name}: sha256 {got} does not match pinned {want}")
        path.write_bytes(body)
        print(f"fetched {name} ({len(body)} bytes)")


def path(name):
    p = DATA / name
    if not p.exists():
        raise SystemExit(f"{p} missing; run: btcx fetch")
    return p
