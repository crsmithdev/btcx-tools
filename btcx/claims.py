"""Claims about the published files that no finding in findings.py checks.

Each claim names its first poster, links the post and quotes the poster's own grade. A person
sets the status. A status of reproduced, partly or does not hold names the check that ran in
the note; any other claim is not checked.
"""

from dataclasses import dataclass

from . import data

ALL = "All five files"
FILE62 = f"File 62, {data.F62}"
SAMPLES = f"The 8k samples, {' and '.join(data.SAMPLES_8K)}"
STATE003 = data.F003
STATE306 = data.F306
RELEASES = "The release archives, 162 and 213"
FILES = [ALL, FILE62, SAMPLES, STATE003, STATE306, RELEASES]

STATUSES = ["reproduced", "partly", "does not hold", "not checked"]

ISSUES = "https://github.com/suebtwist/btcx-files/issues"
NOTES = "https://suebtwist.github.io/btcx-files/"
I5, I12, I15 = f"{ISSUES}/5", f"{ISSUES}/12", f"{ISSUES}/15"
NL1 = f"{I5}#issuecomment-6137385178"
NL2 = f"{I5}#issuecomment-6185551572"
BENVAN = f"{I12}#issuecomment-6546941735"
HELO_CODE = f"{I12}#issuecomment-6623406095"
HELO_ANSWERS = f"{I15}#issuecomment-6624309176"


@dataclass(frozen=True)
class Claim:
    file: str
    claim: str
    credit: str
    link: str
    grade: str
    status: str
    note: str


# fmt: off
CLAIMS = [
    Claim(ALL, "Every file starts with the same 16 bytes: F5 A5 05 5A 5F three times, then 05.",
          "suebtwist", NOTES, "", "partly",
          "True of file 62 and both 8k samples; 306_state.bin ends the 16 bytes with 07 "
          "(container-versions), and 003_state.bin starts with 00."),
    Claim(ALL, "The body is 5-byte records of 4 payload bytes and a separator, normally A5, and the "
               "payload is about 8.00 bits per byte except where the post notes structure.",
          "anthony-lang09", I5, "", "reproduced",
          "btcx info: lane entropy 8.000 in file 62, 7.999-8.000 in 306_state.bin, 7.84-7.89 in the "
          "8k samples (1,635 bytes a lane)."),
    Claim(ALL, "The files are 6,900 bytes (003_state.bin), 8,192 (each 8k sample), 24,859,995 (file 62) "
               "and 31,457,296 (306_state.bin).",
          "suebtwist", NOTES, "", "reproduced", "Sizes of the pinned files."),
    Claim(ALL, "The four-lane mask of file 62, at the tested phase and alignment, gives no other verified "
               "model in the other framed files.",
          "NameLucky2205", NL2, "", "not checked", ""),

    Claim(FILE62, "The only separators in file 62 that are not A5 are records 2048-2055: "
                  "80 BA 77 A7 2C C5 C4 14.",
          "anthony-lang09", I5, "", "reproduced", "btcx info: one run, at record 2048."),
    Claim(FILE62, "All 4,971,996 decoded float32 values are finite, and the largest error of a "
                  "quaternion's squared norm from 1 is 5.849794558e-7.",
          "NameLucky2205", NL2, "", "reproduced",
          "Scratch check on the unmasked rows: 4,971,996 finite; largest error 5.8497945576e-7."),
    Claim(FILE62, "Across the 26 wrong 27-word alignments, at most four records pass a squared-norm "
                  "tolerance of 1e-5.",
          "NameLucky2205", NL2, "", "not checked", ""),
    Claim(FILE62, "Fields 12-26 hold all-zero groups of sizes 3, 5 and 7 (SH degrees 1-3) in 8,315, 8,796 "
                  "and 9,275 rows, and no group is partly zero.",
          "NameLucky2205", NL2, "", "reproduced",
          "Scratch check on the unmasked rows: the same counts; 0 partly zero."),
    Claim(FILE62, "The 27 fields are position (0-2), log scale (3-5), a unit quaternion (6-9), opacity "
                  "logit (10), a grey SH DC coefficient (11) and 15 grey SH coefficients of degrees 1-3 "
                  "(12-26), as in 3D Gaussian splatting.",
          "NameLucky2205", NL2, "inferred", "not checked", ""),
    Claim(FILE62, "File 62 is a single-view 3D Gaussian splat capture: quaternions in w x y z order, the "
                  "camera at the origin, +y down.",
          "Helo3301", I12, "confirmed", "not checked", ""),
    Claim(FILE62, "From the capture camera the scene shows a dark near frame, a tall carved block structure "
                  "55-115 units away, bright fog and a small dark upright shape at about 22 units.",
          "Helo3301", I12, "confirmed", "not checked", ""),
    Claim(FILE62, "No field of file 62 carries a hidden payload in its low bits.",
          "Helo3301", I12, "confirmed", "not checked", ""),
    Claim(FILE62, "A recessed slot about 10 x 3.4 units is cut into the structure's panel, and its "
                  "carvings do not match the type-50 strokes of 003_state.bin.",
          "Helo3301", I12, "leads", "not checked", ""),
    Claim(FILE62, "In the opacity and scale fields, an upright rectangle at about 46 units, beside the "
                  "small shape, is hidden in a normal render by a fog sheet at 20-25 units.",
          "Helo3301", I12, "leads", "not checked",
          f"Repeated as a pale column 48-68 units away, graded guess: {I15}"),
    Claim(FILE62, "A search found no other hidden information in file 62, and the structure on the right "
                  "of the point cloud is not coherent: a gap in the clouds.",
          "benvan", BENVAN, "", "not checked", ""),
    Claim(FILE62, "The splats fill one viewing cone of about 64 x 44 degrees from the origin, flat splats "
                  "face the origin, and splat size grows with distance from it.",
          "Helo3301", HELO_CODE, "inferred", "not checked", ""),
    Claim(FILE62, "Of the nonzero values, mantissa bits 0, 1 and 2 are set in 66.6%, 36.9% and 47.3% for "
                  "fields 11-26, and in 49.5%, 50.0% and 50.0% for fields 0-10.",
          "Helo3301", HELO_CODE, "", "reproduced",
          "Scratch check on the unmasked rows: the same shares to 0.1%."),
    Claim(FILE62, "1,414 records lie in the box 6 < x < 7.9, -4.6 < y < -1, 21 < z < 24; 23,758 others "
                  "have 15 < z < 32 and atan2(x, z) > 2 degrees; 25,111 lie at camera depth 15-32 right of "
                  "0.47 W in the 1200 x 840, 40-degree view.",
          "Helo3301", HELO_CODE, "", "partly",
          "The first two counts reproduce in a scratch check; the third needs the projection."),
    Claim(FILE62, "Nothing in file 62 could carry sound.",
          "Helo3301", HELO_ANSWERS, "", "not checked", ""),

    Claim(SAMPLES, "The first structured region of the 8k samples starts at byte 4,101, just past the "
                   "4 KB samples' end.",
          "anthony-lang09", I5, "", "reproduced",
          "Record 817 (base60-8k) starts at byte 16 + 5 x 817 = 4,101."),
    Claim(SAMPLES, "At records 817-864, lanes 0 and 1 of each 8k sample repeat a 16-record label three "
                   "times, with the values in the post, and lanes 2 and 3 stay random.",
          "anthony-lang09", I5, "", "reproduced",
          "Scratch check: both labels match the post and repeat at 833 and 849; lanes 2-3 hold "
          "5.3-5.5 bits a byte over the 48 records."),
    Claim(SAMPLES, "The upstream parse_btcx.py flags streams 1 and 2 of the 8k samples as low entropy at "
                   "offsets 4016-4497.",
          "anthony-lang09", I5, "", "not checked",
          "Needs the upstream parse_btcx.py, which btcx-tools does not run."),
    Claim(SAMPLES, "The 4 KB samples are the first 4,096 bytes of the 8 KB samples.",
          "Helo3301", I15, "solid", "reproduced",
          "cmp against 20180213_0417.bin and 20180219_2258.bin fetched at 2d55483, not pinned."),
    Claim(SAMPLES, "A second difference of 72 shows up twice in the label.",
          "Helo3301", I15, "", "reproduced",
          "Lane 0 of label records 4-6 (38;24;0 and 38;25;12) and lane 1 of records 13-14 (0;0 and "
          "1;12) differ by 72 between the samples."),
    Claim(SAMPLES, "The rest of the samples is at the random ceiling: file 62's LFSR with any of the 2,048 "
                   "full-period 16-bit tap sets does not open it, and no key built from the label does.",
          "Helo3301", I15, "likely", "not checked", ""),
    Claim(SAMPLES, "The samples end at record 1634, before records 2048-2055 where file 62 keeps its key; "
                   "if the files follow file 62, their key is in the missing part.",
          "Helo3301", I15, "guess", "partly",
          "btcx info: records 0-1634 and 1 trailing byte; where their key is, is not checked."),

    Claim(STATE003, "003_state.bin is 6,900 bytes, every byte is 0-59 with all 60 values present, and it "
                    "lays out as 23 rows of 300 with the same 3-part structure in each row.",
          "anthony-lang09", I5, "", "partly",
          "Size and values reproduce in a scratch check; the 3-part structure is not checked."),
    Claim(STATE003, "The last row breaks down: 53 bytes of 3B from offset 6608, then runs of zeros to the "
                    "end.",
          "anthony-lang09", I5, "", "reproduced",
          "Scratch check: 3B at 6608-6660 (6660 is a block header); each later block ends in 52 zeros."),
    Claim(STATE003, "Each row is five 60-byte blocks that start with 0, 59, 0, 59 and the row index; the "
                    "rest, joined by lane, is five 1,357-byte streams of 1,305 used and 52 padding bytes.",
          "NameLucky2205", NL1, "", "reproduced",
          "Scratch check: block starts match in all 23 rows; 1,305 bytes used; padding is 3B in lane 0 "
          "and 00 in lanes 1-4."),
    Claim(STATE003, "In each record, the first and last bytes of lanes 1 and 2 sum to 59, and lane 3 is "
                    "framed as n, n values, 59 - n.",
          "NameLucky2205", NL1, "", "reproduced", "Scratch check over all 239 records."),
    Claim(STATE003, "In each of the 53 type-50 records, the running sums of the lane 0 and lane 1 steps "
                    "(value - 30) span exactly the width in lane 2 and the height in lane 3.",
          "NameLucky2205", NL1, "", "reproduced", "Scratch check: 53 of 53."),
    Claim(STATE003, "Each point of a type-50 stroke is a dx/dy step and a pen-up/pen-down flag (53 of 53).",
          "Helo3301", I15, "solid", "partly",
          "The flag is 0 or 1 in every point of all 53 strokes (scratch check); its meaning is not "
          "checked."),
    Claim(STATE003, "Each of the 89 type-52 placements names one sign by ID (89 of 89), with a row (7 rows) "
                    "and a baseline.",
          "Helo3301", I15, "solid", "partly",
          "All 89 sign IDs resolve and the row field takes 7 values, 0-6 (scratch check); the baseline "
          "is not checked."),
    Claim(STATE003, "The 8 type-49 records are rulers: each runs 7 to 28 in even steps, 60 marks in all.",
          "Helo3301", I15, "solid", "reproduced",
          "Scratch check: each runs 7 to 28, its steps differ by at most 1, 60 marks in all."),
    Claim(STATE003, "Assembled, the signs match the 60 signs of the fan mail key page far better than "
                    "shuffled strokes: 12 of 88 signs beat 99% of shuffles, against at most 6 by chance.",
          "Helo3301", I15, "likely", "not checked", ""),
    Claim(STATE003, "85 of 88 signs are placed exactly once, built from a shared stroke library, so each "
                    "sign is one written instance, like handwriting.",
          "Helo3301", I15, "likely", "partly",
          "85 of 88 signs have exactly one placement (scratch check); the handwriting reading is not "
          "checked."),
    Claim(STATE003, "12 of 25 identified placements sit in the same row as on the key page, against 3.7 by "
                    "chance.",
          "Helo3301", I15, "likely", "not checked", ""),
    Claim(STATE003, "The records are in random order, and no field gives the left-to-right position.",
          "Helo3301", I15, "likely", "not checked", ""),
    Claim(STATE003, "About 75% of the digits are accounted for; most of the rest looks like bounded filler.",
          "Helo3301", I15, "", "not checked", ""),

    Claim(STATE306, "Payload byte 0 of records 0-11 is 0, 57 six times, then 0, 7, 0, 7.",
          "anthony-lang09", I5, "", "reproduced", "Scratch check on lane 0 of records 0-15."),
    Claim(STATE306, "Payload byte 0 is zero from record 477 to 16383, and the zeros end at 16384 (2^14).",
          "anthony-lang09", I5, "", "reproduced",
          "Scratch check: lane 0 is 0 at records 477-16383, not 0 at 476 and 16384."),
    Claim(STATE306, "306_state.bin holds exactly 6,291,456 records (6 x 2^20) and no trailing bytes.",
          "anthony-lang09", I5, "", "reproduced", "btcx info: 6,291,456 records, +0 trailing bytes."),
    Claim(STATE306, "The SHA-256 of 306_state.bin matches the upstream README.",
          "anthony-lang09", I5, "", "reproduced",
          "The README at 2d55483 gives d5c379bc...46e9, the pinned SHA-256."),
    Claim(STATE306, "Other little-endian fields hold 613 and 306.",
          "NameLucky2205", NL1, "", "reproduced",
          "Scratch check: lane 0 uint32 number 5 is 306 and number 90 is 613."),
    Claim(STATE306, "The section lengths are media-sized: 59 x 59 x 1,024, 8 x 1,024 x 1,024 and "
                    "607 x 1,024 two-byte values; section 58 fits 8 frames of 1024 x 1024 at 16 bits.",
          "Helo3301", I15, "likely", "partly",
          "The lengths factor as stated; that they hold media is not checked."),
    Claim(STATE306, "Unlike file 62, 306_state.bin stores its payload lane by lane.",
          "Helo3301", I15, "solid", "not checked", ""),
    Claim(STATE306, "The contents are encrypted: about a million cipher trials keyed from material in the "
                    "files decrypted nothing.",
          "Helo3301", I15, "solid for what we tried", "not checked", ""),
    Claim(STATE306, "The 224-byte block in the header is not a SHA-256, SHA3 or BLAKE2 hash of any file or "
                    "clue the poster holds.",
          "Helo3301", I15, "solid for what we tried", "not checked", ""),
    Claim(STATE306, "A search of 1,687 bit sequences from the three sections for linear recurrences of "
                    "degree up to 128 found no validated candidate.",
          "NameLucky2205", NL2, "", "not checked", ""),

    Claim(RELEASES, "All 11 release archives are complete, standalone 7z files with AES-256, 2^19 key "
                    "rounds and encrypted headers; none is a split volume.",
          "Helo3301", I15, "solid", "not checked",
          "GitHub lists 11 assets; only 162.6.4 was downloaded, and it starts with the 7z signature."),
    Claim(RELEASES, "213 probably holds two files: its encrypted header is 32 bytes longer than the others.",
          "Helo3301", I15, "likely", "not checked", ""),
    Claim(RELEASES, "The SHA-256 in the 162.6.4 release note does not match its file.",
          "Helo3301", I15, "solid", "reproduced",
          "The asset hashes to db500f5c369b07e9d56e44de389ac1f4bf3c4e625b3163bc3130a16294f4ba7b, not the "
          "note's ba234d5a4645d50e1c5803199b8e932eda1f07862599830e201aab8a00291abb."),
    Claim(RELEASES, "Release 162.6 has no file attached.",
          "Helo3301", I15, "solid", "reproduced", "The GitHub API lists no asset for release 162.6."),
    Claim(RELEASES, "Neither the 162.6 nor the 162.6.4 note hash matches anything else the poster holds.",
          "Helo3301", I15, "solid", "partly",
          "Neither matches the SHA-256 of an asset in the GitHub API or of a pinned file; other files "
          "are not checked."),
    Claim(RELEASES, "333 clue-based passwords against the 162 and 213 archives all failed.",
          "Helo3301", I15, "solid", "not checked", ""),
]
# fmt: on
