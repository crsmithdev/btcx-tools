# Glossary

The names the code and docs use. One thing has one name.

| Term | Meaning |
|---|---|
| container | A BTCX file: a 16-byte header (a 15-byte sync word and a version byte), then records. `003_state.bin` is not a container. |
| record | 5 bytes of a container's body: one payload word and one separator. |
| word | The 4 payload bytes of a record. A container can end with one word that has no separator. |
| lane | One byte position (0-3) in each word, read down the file as one stream. |
| separator | The fifth byte of a record. It is `A5` except in an anomaly. |
| anomaly | A run of records whose separator is not `A5`. |
| embedded key | An anomaly of 8 separators that, XOR `A5`, gives the 4 start states of file 62's mask. |
| start state | The 16-bit state of one lane's LFSR before the first word. |
| phase | A position in the 65,535-byte LFSR mask sequence that starts at state 1. |
| file 62 | `20180208_1142.bin`. |
| splat row | 27 float32 of file 62's plaintext, read as one 3D Gaussian. |
| stroke, sign, placement | `003_state.bin` record types 50, 51 and 52: a pen path, a set of placed strokes, a sign in a row. |
| finding | A claim from a contributor's post, with credit, a link and a check that `btcx verify` runs. |
| pinned input | A published file fetched at the pinned commit and checked by SHA-256. |
