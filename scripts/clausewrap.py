#!/usr/bin/env python3
"""Wrap Markdown prose at clause ends, and check that a rewrap changed nothing but whitespace.

usage:
    clausewrap.py [--width 100] [--write] FILE.md...     show (or write) a rewrap of the prose
    clausewrap.py --check ORIGINAL.md REWRAPPED.md       prove that only whitespace moved

Scope: paragraphs, list items and block quotes. Code fences, tables, headings, HTML, front matter,
indented code and any paragraph with a hard break (two trailing spaces or a backslash) are left alone.
Each paragraph is joined into one run first, so a paragraph never keeps the breaks of an older wrap.
A run that is too long is cut at its strongest boundary first (sentence end, then colon, then comma
or closing bracket, then a word) and the pieces are packed into lines.
Nothing is ever broken inside (brackets), `backticks`, "quotes" or **bold**,
unless a bracketed span is longer than MAX_SPAN, which may then break at its own commas.
A line never starts with something Markdown reads as structure (a fence, list marker, #, > or |).
Semicolons in prose are reported, not changed: rewrite each by hand as two sentences.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WIDTH = 100
MAX_SPAN = 60
BLOCK_START = re.compile(r"^(?:[-*+>#|]+|\d+[.)]|```\S*|~~~\S*)$")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])(\s+)(.*)$")
QUOTE = re.compile(r"^(\s*>[ >]*)(.*)$")
ABBREVIATIONS = ("e.g.", "i.e.", "etc.", "vs.", "cf.")


def words_of(text: str) -> list[str]:
    """Split at the spaces that are outside (...), [...], `...`, **...** and short "..." spans."""
    words: list[str] = []
    current: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        end = -1
        if text.startswith("```", i):
            j = i
            while j < n and text[j] == "`":
                j += 1
            current.append(text[i:j])
            i = j
            continue
        if text.startswith("``", i):
            found = text.find("``", i + 2)
            end = found + 1 if found != -1 else -1
        elif ch == "`":
            end = text.find("`", i + 1)
        elif text.startswith("**", i):
            found = text.find("**", i + 2)
            end = found + 1 if found != -1 else -1
        elif ch in "([":
            closer, depth = (")" if ch == "(" else "]"), 0
            for j in range(i, n):
                depth += text[j] == ch
                depth -= text[j] == closer
                if depth == 0:
                    end = j
                    break
        elif ch == '"':
            end = text.find('"', i + 1)
            if end != -1 and end - i > 80:
                end = -1
        # A short span stays in one piece. A bracketed one longer than MAX_SPAN breaks at its commas.
        if end != -1 and ch in "([" and end - i > MAX_SPAN:
            end = -1
        if end != -1:
            current.append(text[i:end + 1])
            i = end + 1
            continue
        if ch == " ":
            if current:
                words.append("".join(current))
                current = []
        else:
            current.append(ch)
        i += 1
    if current:
        words.append("".join(current))
    return words


def strength(word: str) -> int:
    """How hard a break after ``word`` is: 3 sentence end, 2 colon or semicolon, 1 comma or bracket."""
    core = word.rstrip("'\"`*")
    if core.endswith((".", "!", "?")) and core.lower() not in ABBREVIATIONS and len(core) > 2:
        return 3
    if core.endswith((":", ";")):
        return 2
    if core.endswith((",", ")", "]")):
        return 1
    return 0


def wrap_words(words: list[str], first: str, rest: str, width: int) -> list[str]:
    """Lines of ``words``, broken at the strongest boundaries that make them fit."""
    merged: list[str] = []
    for word in words:                      # a line must not start with Markdown syntax
        if merged and BLOCK_START.match(word.split(" ", 1)[0]):
            merged[-1] = f"{merged[-1]} {word}"
        else:
            merged.append(word)
    words = merged
    lines: list[str] = []
    current = ""

    def room() -> int:
        return width - len(first if not lines else rest)

    def flush() -> None:
        nonlocal current
        if current:
            lines.append((first if not lines else rest) + current)
            current = ""

    def place(span: list[str], limit: int) -> None:
        nonlocal current
        piece = " ".join(span)
        if current and len(current) + 1 + len(piece) <= room():
            current = f"{current} {piece}"
            return
        flush()
        if len(piece) <= room():
            current = piece
            return
        level = min(max((strength(w) for w in span[:-1]), default=0), limit)
        if level == 0:                      # nothing to break at but words
            for word in span:
                if current and len(current) + 1 + len(word) > room():
                    flush()
                current = f"{current} {word}".strip()
            return
        pieces: list[list[str]] = [[]]
        for word in span:
            pieces[-1].append(word)
            if strength(word) >= level:
                pieces.append([])
        for part in pieces:
            if part:
                place(part, level - 1)

    place(words, 3)
    flush()
    return lines


def rewrap(text: str, width: int = WIDTH) -> str:
    out: list[str] = []
    lines = text.split("\n")
    i, in_fence = 0, False
    if lines and lines[0] == "---":         # front matter
        j = next((k for k in range(1, len(lines)) if lines[k] == "---"), None)
        if j is not None:
            out.extend(lines[:j + 1])
            i = j + 1
    while i < len(lines):
        line = lines[i]
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        plain = (not in_fence and line.strip() and not line.lstrip().startswith(("#", "|", "<", "!["))
                 and not line.startswith("    ") and not re.match(r"^\s*(-{3,}|\*{3,}|={3,})\s*$", line))
        if not plain:
            out.append(line)
            i += 1
            continue
        # one block: a paragraph, a list item (with its continuation lines) or a quote
        item = LIST_ITEM.match(line)
        quote = None if item else QUOTE.match(line)
        if (quote and not quote.group(2).strip()) or (item and not item.group(4).strip()):
            out.append(line)                # an empty quote line or list marker separates paragraphs
            i += 1
            continue
        if item:
            first = f"{item.group(1)}{item.group(2)}{item.group(3)}"
            rest, body = " " * len(first), [item.group(4)]
        elif quote:
            first = rest = quote.group(1)
            body = [quote.group(2)]
        else:
            first = rest = re.match(r"^\s*", line).group(0)
            body = [line.strip()]
        j = i + 1
        while j < len(lines) and lines[j].strip() and not re.match(r"^\s*(```|~~~|#|\|)", lines[j]) \
                and not LIST_ITEM.match(lines[j]) and not lines[j].startswith("    ") \
                and (not item or lines[j].startswith(rest)) \
                and (not quote or (QUOTE.match(lines[j]) and QUOTE.match(lines[j]).group(2).strip())):
            body.append((QUOTE.match(lines[j]).group(2) if quote else lines[j].strip()))
            j += 1
        block = lines[i:j]
        if any(b.endswith(("  ", "\\")) for b in block):        # a hard break is deliberate
            out.extend(block)
        else:
            out.extend(wrap_words(words_of(" ".join(body)), first, rest, width))
        i = j
    return "\n".join(out)


def structure(text: str) -> dict:
    fences = headings = items = rows = 0
    in_fence = False
    for line in text.split("\n"):
        if re.match(r"^\s*(```|~~~)", line):
            fences += 1
            in_fence = not in_fence
        elif in_fence:
            continue
        elif re.match(r"^#{1,6}\s", line):
            headings += 1
        elif LIST_ITEM.match(line):
            items += 1
        elif line.lstrip().startswith("|"):
            rows += 1
    return {"fences": fences, "headings": headings, "list_items": items, "table_rows": rows, "open_fence": in_fence}


def check(original: str, rewrapped: str) -> list[str]:
    """Problems with a rewrap: any change beyond whitespace, or in the Markdown structure."""
    problems = []
    if re.sub(r"\s+", "", original) != re.sub(r"\s+", "", rewrapped):
        problems.append("the text differs beyond whitespace")
    if structure(original) != structure(rewrapped):
        problems.append(f"the structure changed: {structure(original)} -> {structure(rewrapped)}")
    return problems


def semicolons(text: str) -> list[tuple[int, str]]:
    """Lines whose prose has a semicolon (not in code spans, fences or tables)."""
    found, in_fence = [], False
    for number, line in enumerate(text.split("\n"), 1):
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
        elif not in_fence and not line.lstrip().startswith("|"):
            stripped = re.sub(r"`[^`]*`|\"[^\"]*\"|&\w+;", "", line)
            if ";" in stripped:
                found.append((number, line.strip()[:90]))
    return found


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"] and len(argv) == 3:
        problems = check(Path(argv[1]).read_text(), Path(argv[2]).read_text())
        print("\n".join(problems) if problems else "only whitespace moved, structure unchanged")
        return 1 if problems else 0
    width, write = WIDTH, False
    args = list(argv)
    if "--width" in args:
        k = args.index("--width")
        width = int(args[k + 1])
        del args[k:k + 2]
    if "--write" in args:
        args.remove("--write")
        write = True
    status = 0
    for name in args:
        old = Path(name).read_text()
        new = rewrap(old, width)
        problems = check(old, new)
        if problems:
            print(f"{name}: NOT written, {'; '.join(problems)}")
            status = 1
            continue
        long_lines = sum(len(line) > width for line in new.split("\n") if not line.lstrip().startswith("|"))
        print(f"{name}: {'rewrapped' if new != old else 'already wrapped'}, {long_lines} line(s) over {width}")
        for number, text in semicolons(new):
            print(f"  semicolon at {number}: {text}")
        if write and new != old:
            Path(name).write_text(new)
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
