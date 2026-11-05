# Style

The code is minimal and good to look at. These rules apply under
[PRINCIPLES.md](PRINCIPLES.md). When a rule here conflicts with a rule in
PRINCIPLES.md, PRINCIPLES.md wins. `ruff format` has the last word on
whitespace.

## Names

1. **Short names.** The length of a name grows with its scope. A local
   name can have two characters (`lo`, `hi`). A module-level
   name is one word if it can be.
   > Length is not a virtue in a name; clarity of expression is.
   > (Rob Pike, *Notes on Programming in C*)

   | Scope | Good | Too long |
   |---|---|---|
   | loop, comprehension | `w`, `r`, `lo, hi` | `word_index` |
   | function | `key`, `runs`, `edges`, `flags` | `separator_values` |
   | module | `SYNC`, `TAPS`, `PERIOD`, `unmask` | `LFSR_TAP_MASK` |

2. **The glossary's words.** A thing that [GLOSSARY.md](GLOSSARY.md)
   names keeps that name, whole, at every scope: `container`, `separator`,
   `lane`, `word`. Do not shorten it and do not invent a second word for
   it. A short name is for a thing the glossary does not name.
3. **No noise in a name.** No type (`payload_arr`), no `data`, `info`,
   `value`, `num_` or `_list`. A plural is a collection: `runs`, `states`.
4. **Two characters or more.** A one-letter name lives only in a loop or
   a comprehension (PRINCIPLES rule 4).
5. **A legend for abbreviations.** When a module uses an abbreviation in
   many places, its docstring lists it once, as Norvig's `sudoku.py`
   does. A glossary term is never abbreviated (rule 2).

   ```python
   ## Throughout this program we have:
   ##   r is a row,    e.g. 'A'
   ##   c is a column, e.g. '3'
   ```

## Shape

6. **Arrays, not loops.** A numpy expression shows the shape of the
   operation. A loop over words is for a step that depends on the step
   before it, as in `lfsr._cycle`.
7. **Short functions.** A function does one job in a few lines. Its
   docstring is one line that says what it returns, as in Norvig's
   `spell.py`: `"Most probable spelling correction for word."`
8. **Flat.** Return early. No `else` after `return`. No more than two
   levels of indent inside a function.
9. **Parallel things look parallel.** Code that does the same job for
   different cases has the same shape, line for line, as the operators in
   micrograd's `Value`. Put related lines in the same order each time.
10. **No defence the pinned files do not need.** CPython's
   `wave._read_fmt_chunk` wraps each `struct.unpack` in its own `try`,
   because it reads any file. This toolkit reads files pinned by SHA-256.
   One check at the boundary is enough (PRINCIPLES rule 11).
11. **Tables stay tables.** `ruff format` removes the spaces that align
   columns. A table of format fields can keep its alignment inside
   `# fmt: off` and `# fmt: on`. Do this only for data, never for logic.

## Comments

12. **A comment gives what the code cannot:** a field meaning, a reason, a
    source. It never says what the next line does.

    ```python
    # bad (minbpe/basic.py)
    # save the merge
    merges[pair] = idx

    # good
    if self.tail == 4:  # a final word with no separator after it
    ```

13. **Give the shape of an array** where a reshape or a slice makes it, as
    nanoGPT does with `# (B, nh, T, hs)`.

    ```python
    self.payload = payload  # (words, lanes)
    ```

## Example

`Container.anomalies` and `Container.base60_regions`. Each method had its
own loop to find runs; now one helper, `_runs`, finds runs for both (rule 5
of PRINCIPLES.md: one way to do each thing).

Before (`1152959`):

```python
def anomalies(self):
    """Runs of records whose separator is not A5: [(start, bytes)]."""
    idx = np.nonzero(self.separators != SEP)[0]
    runs = []
    for i in idx:
        if runs and runs[-1][0] + len(runs[-1][1]) == i:
            runs[-1][1].append(int(self.separators[i]))
        else:
            runs.append((int(i), [int(self.separators[i])]))
    return [(start, bytes(b)) for start, b in runs]

def base60_regions(self, lanes=(0, 1), min_words=32):
    """Word ranges where the given payload lanes hold only values 0-59."""
    ok = np.all(self.payload[:, list(lanes)] < 60, axis=1)
    regions, start = [], None
    for i, flag in enumerate(np.append(ok, False)):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            if i - start >= min_words:
                regions.append((start, i))
            start = None
    return regions
```

After (`main`, `btcx/container.py`):

```python
def anomalies(self) -> list[tuple[int, bytes]]:
    """Runs of records whose separator is not A5, as (first record, separator bytes)."""
    return [
        (start, self.separators[start:stop].tobytes())
        for start, stop in _runs(self.separators != SEPARATOR)
    ]

def base60_regions(self) -> list[tuple[int, int]]:
    """Inclusive word ranges of 32 or more words where lanes 0 and 1 hold only 0-59."""
    flags = np.all(self.payload[:, :2] < BASE, axis=1)
    return [(start, stop - 1) for start, stop in _runs(flags) if stop - start >= BASE60_MIN_WORDS]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Half-open index ranges of consecutive True values."""
    edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist(), strict=True))
```

## Read these

| Code | What to take |
|---|---|
| [Norvig, `spell.py`](https://github.com/norvig/pytudes/blob/main/py/spell.py) | One-line docstrings, functions of one to three lines, names from the domain (`P`, `known`, `edits1`). |
| [Norvig, `sudoku.py`](https://github.com/norvig/pytudes/blob/main/py/sudoku.py) | A legend of short names at the top (rule 5); the whole board built from one `cross` function. |
| [Norvig, `lis.py`](https://github.com/norvig/pytudes/blob/main/py/lis.py) | A whole interpreter in 130 lines; type aliases that name the domain. |
| [Karpathy, micrograd `engine.py`](https://github.com/karpathy/micrograd/blob/master/micrograd/engine.py) | One shape repeated for each operator; a small surface. |
| [Karpathy, nanoGPT `model.py`](https://github.com/karpathy/nanoGPT/blob/master/model.py) | Array shapes in comments (rule 13); the model reads top to bottom in one file. |
| [Rhodes, contingent `graphlib.py`](https://github.com/aosabook/500lines/blob/master/contingent/code/contingent/graphlib.py) | Most methods are one to three lines over two dicts. The names (`consequence_task`) are longer than rule 1 permits. |
| [CPython `colorsys.py`](https://github.com/python/cpython/blob/main/Lib/colorsys.py) | The notation of the math as names (`y, i, q`). Here, outside a loop or a comprehension, a name has two characters or more. |

## Avoid these

| Code | What goes wrong |
|---|---|
| [Karpathy, minbpe `basic.py`](https://github.com/karpathy/minbpe/blob/master/minbpe/basic.py) | The algorithm is clean; most comments repeat the code (rule 12). |
| [Batchelder, templite `CodeBuilder.get_globals`](https://github.com/aosabook/500lines/blob/master/template-engine/code/templite.py) | A comment above each line says what the line does (rule 12). The rest of the file is good. |
| [CPython `wave._read_fmt_chunk`](https://github.com/python/cpython/blob/main/Lib/wave.py) | A `try` around each read and lines over 120 characters (rule 10). |

More candidates come from [500 Lines or Less](https://github.com/aosabook/500lines) and [Ask HN: Good Python codebases to read?](https://news.ycombinator.com/item?id=9896369).
