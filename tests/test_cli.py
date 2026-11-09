"""User errors end in one line and a non-zero status, never a traceback."""

import sys

import pytest

from btcx import data, glyphs
from btcx.cli import main
from btcx.container import SYNC

F62 = str(data.DATA / data.F62)

CASES = {
    "missing file": ["info", "no-such-file.bin"],
    "not a container": ["info", str(data.DATA / data.F003)],
    "not the glyph file": ["glyphs", str(data.DATA / data.F306)],
    "unknown input": ["fetch", "foo.bin"],
    "states not hex": ["unmask", F62, "--states", "zz,1,2,3"],
    "two states": ["unmask", F62, "--states", "1F25,02D2"],
    "zero state": ["unmask", F62, "--states", "0,1,2,3"],
    "no embedded key": ["unmask", str(data.DATA / data.F306)],
    "wrong key, ply": ["unmask", F62, "--states", "1F25,02D2,6089,B162", "--ply"],
    "start past end": ["keysearch", F62, "--start", "99999999"],
    "window too long": ["keysearch", F62, "--words", "70000"],
    "window too short": ["keysearch", F62, "--words", "1"],
    "size not WxH": ["render", "--size", "640"],
    "size zero": ["render", "--size", "0x10"],
    "aim not xyz": ["render", "--aim", "1,2"],
    "fov 180": ["render", "--fov", "180"],
    "aim at the eye": ["render", "--aim", "0,0,0"],
    "aim straight up": ["render", "--aim", "0,-1,0"],
}


def assert_user_error(args, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["btcx", *args])
    with pytest.raises(SystemExit) as exit:
        main()
    code = exit.value.code
    if code == 2:  # argparse prints usage and the error
        assert "error:" in capsys.readouterr().err
    else:
        assert isinstance(code, str)
        assert code.startswith("btcx: ")
        assert "\n" not in code


@pytest.mark.parametrize("args", CASES.values(), ids=CASES.keys())
def test_user_error(args, monkeypatch, capsys):
    assert_user_error(args, monkeypatch, capsys)


@pytest.mark.parametrize("first", [0, 49, 59], ids=["zeros", "ruler with no end", "end at once"])
def test_glyph_file_not_003(first, tmp_path, monkeypatch, capsys):
    """A file of the right size that is not 003_state.bin."""
    fake = bytearray(glyphs.SIZE)
    fake[1] = first  # the first record type in lane 0
    path = tmp_path / "fake.bin"
    path.write_bytes(fake)
    assert_user_error(["glyphs", str(path)], monkeypatch, capsys)


def test_header_cut_short(tmp_path, monkeypatch, capsys):
    short = tmp_path / "short.bin"
    short.write_bytes(SYNC)
    assert_user_error(["info", str(short)], monkeypatch, capsys)
