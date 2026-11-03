---
name: clause-wrap
description: "Use when writing, editing or reviewing prose in Markdown, docs, code comments, docstrings or templates, or when text looks hard-wrapped, breaks mid-sentence, or a rewrap is asked for. Sets how to wrap: break at clause ends and never inside brackets, backticks or quotes, join a paragraph before rewrapping, no semicolons, one line per paragraph in text that a template writes for viewers. Includes a script that rewraps Markdown and proves only whitespace moved."
user-invocable: true
argument-hint: "[--width N] [file to rewrap | review]"
---

# Wrap prose at clause ends

Hard-wrapped text goes wrong in three ways. A viewer that treats a single newline as a line break
(GitLab comments and issues, chat, some previewers) shows the wrap as broken sentences.
A wrap in the middle of a clause reads badly even in an editor. And a wrapped word that starts with
three backticks or a list marker can change the structure of the whole file.

## Where the text lives decides the rule

| The text is... | Rule |
|---|---|
| Prose in a source file people read in an editor or a diff (docs, comments, docstrings) | Wrap at about 100 columns, **at clause ends** |
| Text a template or program **writes** for a viewer (a generated Markdown report, a message) | **One line per paragraph**, however long |
| HTML | The source wrap does not matter, the browser joins it. For a deliberate line break use `<br>` between sentences or clauses. For the browser's own wrapping use CSS (below) |
| Code, tables, fences, YAML data, commands | Never wrap. They are structure |

If you cannot tell which it is, ask where the text ends up. A report that is pasted into tickets is
the second kind.

## The rule for source prose

1. **Join the paragraph into one run first**, then wrap. A paragraph must never keep the breaks of an
   older wrap, or you end up with ragged lines in the middle of a sentence.
2. **Width is about 100 columns.** Break only where a clause ends.
3. **Cut a paragraph that is too long at its strongest boundary first**: a sentence end, then a colon,
   then a comma or a closing bracket, and only then at a plain word. Pack the pieces into lines.
   So a short clause such as `newest first, each marked as a fix.` stays together.
4. **Never break inside** `(short brackets)`, `` `backticks` ``, "quotes" or `**bold**`.
   A bracketed span longer than about 60 characters may break at its own commas.
5. **A line never starts with something Markdown reads as structure**: three backticks, a list marker,
   `#`, `>` or `|`. Keep that word on the previous line. A wrapped word that started with three
   backticks once turned the rest of a file into one code block, and a whitespace-insensitive
   comparison did not notice.
6. **No semicolons in prose.** Write two sentences, or a comma and a conjunction, or a comma inside
   brackets. Semicolons inside code, backticks, quotes and HTML entities stay.
7. **Leave structure lines as they are**: list markers, tables, code blocks, front matter, commented-out
   code, `key: value` documentation lines, and anything a checker expects in a fixed shape (a stamp
   line at the top of a stylesheet).
8. A hard line break that someone wrote on purpose (two trailing spaces or a backslash) is kept.

## HTML text in the browser

- Cap the measure of prose at about 75ch (`max-width: 75ch`).
- `text-wrap: pretty` for body paragraphs avoids a short last line. It does **not** stop a one-letter
  word being left alone at a line end or the lines from being ragged.
- `text-wrap: balance` for headings and for short paragraphs (a few lines) evens the lines out. The
  browser applies it only up to a few lines and wraps longer text as usual, so it is safe to set on
  prose generally.
- For lines that must break at a sentence or clause, put `<br>` there. Or drop the paragraph if the
  headings already say it.

## The script

`scripts/clausewrap.py` in this skill's folder rewraps **Markdown** (paragraphs, list items, block
quotes) by the rules above, refuses to write a file when anything beyond whitespace changed, and
lists the semicolons in prose. It does not touch code comments or docstrings: wrap those by hand with
the same rules.

```sh
python3 -I <skill dir>/scripts/clausewrap.py FILE.md            # show what it would do, write nothing
python3 -I <skill dir>/scripts/clausewrap.py --write FILE.md    # rewrap in place
python3 -I <skill dir>/scripts/clausewrap.py --width 80 FILE.md
python3 -I <skill dir>/scripts/clausewrap.py --check OLD.md NEW.md   # prove only whitespace moved
```

When the user asks for a custom width in natural language (for example "wrap at 80 columns",
"use 120 width", or "make it narrower"), pass the number as `--width N` to the script.
The default is 100.

Fix the semicolons it reports by hand. It is idempotent: a second run changes nothing.

## Rewriting a whole file

Rewrapping touches every paragraph, so treat it as its own change.

1. Copy the original first, since the diff will be large.
2. Run the script, or wrap by hand. Never mix a rewrap with content changes.
3. **Prove it.** `--check ORIGINAL NEW` must say only whitespace moved and the structure is unchanged
   (same number of fences, headings, list items and table rows, and no fence left open). For code
   files compare the syntax tree (`ast.dump` for Python), and for YAML compare the loaded data.
4. Prove the check can fail: change one word in a copy and expect it to complain.
5. Commit the rewrap on its own, with a message like `docs: rewrap the guide at clause ends`.
6. Ask before rewrapping text that is not yours or that the task did not touch.

## Check your work

- No paragraph is broken mid-clause, and none is longer than the width unless it is one unbreakable
  span (a long URL or a code span).
- No line starts with a fence, list marker, `#`, `>` or `|`.
- No semicolons in prose.
- Generated Markdown has one line per paragraph, and tables and fences are intact.
- After a rewrap, `--check` is clean and the file renders the same.
