# clause-wrap

A Claude Code skill that wraps prose at clause boundaries instead of arbitrary column positions.

## What it does

- Breaks lines at sentence ends, colons, and commas — never mid-clause
- Keeps backticks, brackets, quotes, and bold spans intact
- Prevents Markdown structure markers from appearing at the start of a wrapped line
- Flags semicolons in prose for manual replacement
- Includes a verification mode to prove only whitespace changed

## Usage

Invoke as a Claude Code skill:

```
/clause-wrap file.md
/clause-wrap review
```

Or run the script directly:

```sh
python3 -I scripts/clausewrap.py FILE.md              # dry run
python3 -I scripts/clausewrap.py --write FILE.md      # rewrap in place
python3 -I scripts/clausewrap.py --check OLD.md NEW.md # verify no content changed
```

## Rules

- Source prose wraps at ~100 columns, at clause ends
- Template/generated text uses one line per paragraph
- Code, tables, fences, and YAML are never wrapped
