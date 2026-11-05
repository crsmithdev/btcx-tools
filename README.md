# btcx-tools

Analysis tools for the binary files published in btcx-files
([repo](https://github.com/suebtwist/btcx-files), [channel](https://www.youtube.com/@siebfothers)).
`btcx verify` reproduces each finding below from the published files, fetched at commit `2d55483` and
checked by SHA-256.

## Install

Needs Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/crsmithdev/btcx-tools && cd btcx-tools
uv run btcx fetch     # download the published files to data/
uv run btcx verify    # reproduce every finding; exit status 1 if one fails
```

```text
PASS  base60-8k            In both 8k samples, lanes 0 and 1 hold only base-60 digits at records 817-864.
      anthony-lang09, https://github.com/suebtwist/btcx-files/issues/5
PASS  306-countdown        306_state.bin breaks the A5 separators in 3 identical 12-record runs counting 59, 58, 57.
      anthony-lang09, https://github.com/suebtwist/btcx-files/issues/5
```

## What it touches

- `fetch` downloads five `.bin` files from `raw.githubusercontent.com/suebtwist/btcx-files` at the pinned
  commit to `data/`, and checks each by SHA-256. No other command uses the network.
- The other commands read the files you name and write only to `out/`.
- The repo does not hold the creator's files. Each user fetches them from the creator's repo.

## Commands

| Command | Does |
|---|---|
| `verify [--json]` | Runs each finding in `btcx/findings.py`: claim, credit, link, check and expected result. |
| `info FILE` | Header version, record count, entropy per lane, separator runs that are not `A5`, embedded key, base-60 regions. |
| `unmask FILE [--states S] [--ply] [--bin]` | XORs each lane with the B400 LFSR, from the embedded key or `--states`, and checks the result as 27-float splat rows. `--ply` writes a PLY only if every row has a unit quaternion. |
| `keysearch FILE [--start N] [--words N] [--z Z]` | Scores all 65,535 LFSR phases on a window of each lane by entropy. A real key is an outlier (z above 8). |
| `glyphs FILE` | Draws the strokes, signs and placements of `003_state.bin` as SVG. Field meanings are in `btcx/glyphs.py`. |

File 62 is `20180208_1142.bin`. `uv run btcx unmask data/20180208_1142.bin --ply` writes
`out/20180208_1142.ply`. Open it in [SuperSplat](https://superspl.at/editor).

## Findings

Credit goes to the first post of each finding.

| Finding | Credit |
|---|---|
| File 62, both 8k samples and `306_state.bin` share a 15-byte sync word, then a version byte: `05`, and `07` on `306_state.bin` | anthony-lang09, [#5](https://github.com/suebtwist/btcx-files/issues/5) |
| Base-60 digits in lanes 0-1 at records 817-864 of both 8k samples | anthony-lang09, [#5](https://github.com/suebtwist/btcx-files/issues/5) |
| A countdown (59, 58, 57) in 3 separator runs of `306_state.bin` | anthony-lang09, [#5](https://github.com/suebtwist/btcx-files/issues/5) |
| 239 framed records with a mod-60 checksum in `003_state.bin`: 53 of type 50, 88 of type 51, 89 of type 52, 8 of type 49 and 1 of type 48 | NameLucky2205, [#5](https://github.com/suebtwist/btcx-files/issues/5#issuecomment-6137385178) |
| File 62 unmasked by four B400 LFSRs: 184,148 rows of 27 float32, read as a Gaussian splat | NameLucky2205, [#5](https://github.com/suebtwist/btcx-files/issues/5#issuecomment-6185551572) |
| File 62's key is in its separators at records 2048-2055 | Helo3301, [#12](https://github.com/suebtwist/btcx-files/issues/12) |
| In `003_state.bin`, type 50 records are strokes and type 51 records are signs that place them; all 204 stroke references resolve | Helo3301, [#15](https://github.com/suebtwist/btcx-files/issues/15) |
| A blind phase search finds file 62's four start states from words 100,000-104,095 | aleph, [0c046ee](https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817) |
| No B400 key outlier in `306_state.bin` in the first 4,096 words after each countdown run | aleph, [0c046ee](https://github.com/crsmithdev/btcx-tools/commit/0c046ee035efd6ef9c8aba09a1825907adfdc817) |

NameLucky2205 posted the first PLY exporter with the decode
([#5](https://github.com/suebtwist/btcx-files/issues/5#issuecomment-6185551572)). benvan posted the first
PLY file and a viewer in [PR #13](https://github.com/suebtwist/btcx-files/pull/13). suebtwist published
the files. [aleph](https://github.com/crsmithdev/aleph) is an AI agent that crsmithdev runs. It wrote this
toolkit.

## Contributing

Open a [new finding](https://github.com/crsmithdev/btcx-tools/issues/new?template=finding.yml) issue, or add
a row to `FINDINGS` in `btcx/findings.py` and to the table above. `uv run pytest` runs every check and the
user-error cases; CI also runs `ruff`. The rules for changes are in [PRINCIPLES.md](PRINCIPLES.md).

## Licence

MIT, for the code in this repo. The published files belong to their creator.
