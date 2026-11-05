# Principles

These rules decide design, review and code changes in btcx-tools. When two
rules conflict, the earlier rule wins. Each rule has a test that decides a
case. A rule that decides no case in a month is removed.

Rules 5, 8, 9 and 10-13 come from aleph's PRINCIPLES.md. The others exist because
the toolkit is public, it is used inside a game, and its readers find
LLM-written padding quickly and do not trust it.

## The toolkit

1. **A claim has a check or a grade.** Each finding in the README, the
   ledger or command output is reproduced by `btcx verify` from the pinned
   files, or it has the grade `likely` or `guess` where it is written. A
   field meaning that the creator did not state is marked as inferred.
   Test: a change fails this rule when it adds a statement of fact that no
   check reproduces and no grade qualifies.

2. **Credit is exact.** Each finding names the player who found it and links
   the issue, comment or PR where it first appeared.
   Test: a change fails this rule when it adds a finding with no name or no
   link.

3. **No slop.** Prose gives facts: what a command does, what it found, what
   it did not find. It has no praise words ("powerful", "comprehensive"), no
   summary of what the reader just read, and no hedge that a check could
   remove. Command output gives numbers and a pass or fail, not commentary.
   Code has no comment that repeats the code and no branch for a case that
   cannot happen.
   Test: delete the sentence, comment or line. If the reader loses no fact
   and no behaviour, it fails this rule.

4. **Professional code.** The code reads as a maintained library, not a
   notebook dump:
   - A user error (wrong file, missing input, bad value) prints one line
     that says what to do and exits non-zero. A traceback is a bug.
   - Paths do not depend on the current directory.
   - `ruff check` and `ruff format --check` pass. Each function that another
     module calls has type hints.
   - Each decoder has a test at its interface, run on the pinned files, and
     CI runs the tests on each push.
   - A name says what the thing is. An unknown field is named for its place
     (`lane4_col2`), not given a letter. A one-letter name lives only inside
     a loop or a comprehension.
   - Each format constant (`0xA5`, `0xB400`, 27, 60) has one name, in the
     module that owns the format.
   - Nothing is unused: no parameter, field, return value, import or stored
     attribute that no caller reads.
   Test: CI runs ruff, the tests and the user-error cases. A change fails
   this rule when one of them fails, or when review finds an item above.

5. **One way to do each thing.** Remove before you add. One module parses
   the container, one module owns the LFSR, one path fetches the inputs.
   Test: a change fails this rule when it adds a second path for a job that
   a path already does.

6. **Inputs are pinned.** Each input file is fetched at a pinned commit and
   checked by SHA-256. A result that uses an unpinned input says so in its
   output.
   Test: a change fails this rule when a result depends on an input that is
   neither pinned nor named as unpinned.

7. **Out of character.** The toolkit speaks as a player's tool, not as a
   voice inside the game. It does not try to identify the people who made
   the game.
   Test: a change fails this rule when it writes in-world text in the
   toolkit's own voice, or collects data about the creators as people.

8. **Structured over text.** A command that produces findings can emit JSON.
   `verify` and the ledger read that JSON; nothing parses printed output.
   Test: a change fails this rule when one module parses free text that
   another module printed.

9. **Nothing grows without bound.** Commands, checks and docs have a reason
   to exist that can expire. A check that guards a finding the community no
   longer holds is removed with the finding.
   Test: a change fails this rule when it adds something that nothing ever
   removes.

## Code changes

10. **Decide, and state the assumption.** When a request has more than one
   reading, pick the reading that the repo and the issues support, state it,
   and go on. Ask only when the readings lead to work that is materially
   different.
   Test: a change fails this rule when it picks a reading silently.

11. **Minimum code.** Write the least code that meets the goal. Add no
    feature, abstraction, option or error handling that the goal does not
    need.
    Test: a change fails this rule when a line serves a case that cannot
    happen.

12. **Surgical changes.** Touch only what the goal needs. Match the style of
    the file. Remove only what your change made unused; report other dead
    code as a follow-up.
    Test: each changed line traces to the goal.

13. **Done means verified.** Define the check before the change: a test that
    fails first, or a command and its expected output. A claim of done
    traces to a run of that check after the last edit.
    Test: a change fails this rule when its claim of done has no run behind
    it.
