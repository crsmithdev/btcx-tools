# btcx-tools

Analysis tools for the btcx-files ARG
([repo](https://github.com/suebtwist/btcx-files), [channel](https://www.youtube.com/@siebfothers)).
Every input file is pinned to commit `2d55483` by SHA-256, so each result reproduces.

```sh
uv run btcx fetch                              # download the published files to data/
uv run btcx info data/306_state.bin            # header, framing, separator anomalies, entropy
uv run btcx unmask data/20180208_1142.bin --ply  # file 62 -> 184,148 splat records -> out/*.ply
uv run btcx keysearch data/20180208_1142.bin --start 100000   # blind LFSR key search
uv run btcx glyphs data/003_state.bin          # 003 strokes, signs and rows -> out/*.svg
uv run btcx notes build && uv run btcx notes pairs   # creator's notes page -> SQLite
```

## Commands

| Command | Does |
|---|---|
| `info` | Sync header and version, 5-byte record framing, separator runs that are not `A5`, entropy per payload lane, base-60 regions. |
| `unmask` | XORs each payload lane with the 16-bit Galois LFSR (mask `B400`). It reads the start states from an 8-byte separator anomaly or takes `--states`. Checks the 27-float splat shape and the unit quaternions, and writes a PLY for SuperSplat. |
| `keysearch` | Tries all 65,535 LFSR phases per lane on a window of words and scores each by entropy. A real key is a large outlier. It needs no embedded key. |
| `glyphs` | Parses `003_state.bin` into 53 strokes, 88 signs and 89 placements and renders them as SVG. Field meanings are in `btcx/glyphs.py`. |
| `notes` | Loads the 370 transcript lines from the creator's notes page into `out/notes.sqlite`. `search TERM` lists every use. `pairs` lists proper nouns and three-word phrases shared by 2-3 files, and marks lines the notes do not cite yet. |

## Results so far

- File 62: `keysearch` finds all four start states (`1F25 02D2 6089 B161`) blind, from any
  window of 4,096 words, at z = 52 to 985.
- `306_state.bin`: no lane has an outlier at any phase in 7 windows across the three
  sections (best z about 5, which is the noise floor for 65,535 tries). The file 62
  masking is not used there.

## Credits

The format work is by players in the btcx-files issues: anthony-lang09 (framing,
base-60 layers, 306 countdown, #5), NameLucky2205 (003 record framing and checksum,
306 section table, file 62 LFSR decode, #5), Helo3301 (key in the separators, splat
scene, 003 sign and row analysis, #12 and #15) and benvan (PLY export, PR #13).
