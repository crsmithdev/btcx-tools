"""The published btcx-files inputs, fetched at a pinned commit and checked by SHA-256.

data/ and out/ are in the project directory, whatever the current directory is.
"""

from hashlib import sha256
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from . import Error

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"

F003 = "003_state.bin"
F306 = "306_state.bin"
F62 = "20180208_1142.bin"
SAMPLES_8K = ["20180213_0417_8k.bin", "20180219_2258_8k.bin"]

REPO = "https://raw.githubusercontent.com/suebtwist/btcx-files"
COMMIT = "2d55483e2ad991c4cb9f4dd341d67d0258610b7c"
PINNED = {
    F003: "2d0863b4f8bc9605e012f0ea8782f9bda6da5365465d492dcc27990237e54374",
    F306: "d5c379bc98667f7274a8b87f006ff6ce1425a7d3f500a12373a85def931946e9",
    F62: "c945b02e56ee9ecc649149c854f235cfd305a896d86e38a334a97f6111e57fae",
    SAMPLES_8K[0]: "d5fc3ac52552b7c5f48115481664d562a11c079ba7618aad8d4ddb9fa7ea1f3c",
    SAMPLES_8K[1]: "26973b90ace2f091882bc0300ee62404e5a3329e5e3caf9496933f902b7c1b53",
}


def digest(body: bytes) -> str:
    return sha256(body).hexdigest()


def fetch(names: list[str]) -> None:
    """Download the named inputs, or all of them, to data/, each checked by SHA-256."""
    DATA.mkdir(exist_ok=True)
    for name in names or PINNED:
        if name not in PINNED:
            raise Error(f"{name} is not a published input; known: {', '.join(PINNED)}")
        path = DATA / name
        want = PINNED[name]
        if path.exists() and digest(path.read_bytes()) == want:
            print(f"ok      {name}")
            continue
        try:
            with urlopen(f"{REPO}/{COMMIT}/{name}", timeout=60) as response:
                body = response.read()
        except URLError as e:
            raise Error(
                f"cannot download {name}: {e.reason}; check the network and run btcx fetch again"
            ) from None
        if digest(body) != want:
            raise Error(f"{name}: SHA-256 {digest(body)} does not match the pin {want}")
        path.write_bytes(body)
        print(f"fetched {name} ({len(body):,} bytes)")


def read(name: str) -> bytes:
    """The bytes of a published input in data/. A pinned file must match its SHA-256."""
    path = DATA / name
    if not path.exists():
        raise Error(f"{path} is missing; run: btcx fetch")
    body = path.read_bytes()
    if digest(body) != PINNED[name]:
        raise Error(f"{path} does not match its pinned SHA-256; run: btcx fetch")
    return body


def pin_of(body: bytes) -> str | None:
    """The name of the pinned input with these bytes, or None."""
    body_digest = digest(body)
    return next((name for name, want in PINNED.items() if want == body_digest), None)
