#!/usr/bin/env python3
"""Rewrap Markdown prose to a fixed column width (120 by default, matching .clang-format).

Only prose is rewrapped: paragraphs and list items. Everything whose layout carries meaning is
copied through unchanged -- fenced and indented code blocks, tables, headings, HTML blocks,
blockquotes, link reference definitions, YAML front matter and hard line breaks.

    mdwrap.py FILE...          rewrap in place
    mdwrap.py --check FILE...  list files that need rewrapping; exit 1 if any do
    mdwrap.py --staged         rewrap staged Markdown and re-stage it (used by the pre-commit hook)
"""

import argparse
import os
import re
import subprocess
import sys

DEFAULT_WIDTH = 120

_FENCE = re.compile(r"^(\s*)(`{3,}|~{3,})")
_HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
_BULLET = re.compile(r"^(\s*)([-*+]\s+|\d{1,9}[.)]\s+)")
_TABLE_ROW = re.compile(r"^\s{0,3}\|")
_TABLE_DELIM = re.compile(r"^\s{0,3}\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_THEMATIC = re.compile(r"^\s{0,3}(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$")
_SETEXT = re.compile(r"^\s{0,3}(=+|-+)\s*$")
_LINKDEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")
_HTML = re.compile(r"^\s{0,3}<")
_QUOTE = re.compile(r"^\s{0,3}>")
_HARD_BREAK = re.compile(r"(?:  +|\\)$")
_INDENTED_CODE = re.compile(r"^(?:\t| {4,})")

# A wrapped line must never *begin* with a token Markdown would read as a block marker:
# breaking "... a buffer + a system" so that "+ a system" starts a line invents a list item.
_BLOCK_MARKER = re.compile(r"^(?:[-*+|]|#{1,6}|\d{1,9}[.)]|={2,}|-{2,}|_{2,}|`{3,}|~{3,})$|^>")

# Inline spans that must not be split across a break: `code`, [text](url), <autolink>.
_ATOM = re.compile(r"`[^`]*`|!?\[[^\]]*\]\([^)]*\)|<[^\s>]+>")
_NBSP = "\x00"


def _fill(text, first_indent, cont_indent, width):
    """Greedily wrap `text`, keeping inline atoms intact and block markers off line starts."""
    words = [w for w in _ATOM.sub(lambda m: m.group(0).replace(" ", _NBSP), text).split(" ") if w]
    lines = []
    i = 0
    while i < len(words):
        indent = first_indent if not lines else cont_indent
        limit = max(width - len(indent), 1)
        line = [words[i]]
        j = i + 1
        while j < len(words) and len(" ".join(line + [words[j]])) <= limit:
            line.append(words[j])
            j += 1
        while j < len(words) and len(line) > 1 and _BLOCK_MARKER.match(words[j]):
            j -= 1
            line.pop()
        lines.append((indent + " ".join(line)).rstrip())
        i = j
    return [line.replace(_NBSP, " ") for line in lines]


def rewrap(text, width=DEFAULT_WIDTH):
    newline = "\r\n" if "\r\n" in text else "\n"
    ends_with_newline = text.endswith("\n")
    lines = text.replace("\r\n", "\n").split("\n")
    if ends_with_newline:
        lines.pop()

    out = []
    block = None  # [first_indent, cont_indent, joined_text]

    def flush():
        nonlocal block
        if block is not None:
            out.extend(_fill(block[2], block[0], block[1], width))
            block = None

    n = len(lines)
    i = 0

    if n and lines[0].strip() == "---":  # YAML front matter
        for k in range(1, n):
            if lines[k].strip() in ("---", "..."):
                out.extend(lines[: k + 1])
                i = k + 1
                break

    while i < n:
        line = lines[i]
        stripped = line.strip()

        fence = _FENCE.match(line)
        if fence:
            flush()
            marker = fence.group(2)
            out.append(line)
            i += 1
            while i < n:
                out.append(lines[i])  # verbatim: trailing space can be significant in code
                closing = _FENCE.match(lines[i])
                i += 1
                if closing and closing.group(2)[0] == marker[0] and len(closing.group(2)) >= len(marker):
                    break
            continue

        if not stripped:
            flush()
            out.append("")
            i += 1
            continue

        # A setext underline turns the paragraph above it into a heading, so that paragraph
        # has to stay on one line. Checked before _THEMATIC, which also matches "---".
        if _SETEXT.match(line) and block is not None:
            out.append(block[0] + block[2])
            block = None
            out.append(line.rstrip())
            i += 1
            continue

        if (_HEADING.match(line) or _THEMATIC.match(line) or _TABLE_ROW.match(line)
                or _TABLE_DELIM.match(line) or _LINKDEF.match(line)):
            flush()
            out.append(line.rstrip())
            i += 1
            continue

        if _HTML.match(line) or _QUOTE.match(line):  # copied verbatim up to the next blank line
            flush()
            while i < n and lines[i].strip():
                out.append(lines[i].rstrip())
                i += 1
            continue

        if _INDENTED_CODE.match(line) and block is None:
            flush()
            while i < n and (_INDENTED_CODE.match(lines[i]) or not lines[i].strip()):
                out.append(lines[i])
                i += 1
            continue

        if _HARD_BREAK.search(line):  # trailing "  " or "\" is a <br>; leave the line be
            flush()
            out.append(line)
            i += 1
            continue

        bullet = _BULLET.match(line)
        if bullet:
            flush()
            marker = bullet.group(0)
            block = [marker, " " * len(marker.expandtabs(4)), line[bullet.end():].strip()]
            i += 1
            continue

        if block is not None:
            block[2] += " " + stripped  # lazy continuation of the paragraph or list item
        else:
            indent = line[: len(line) - len(line.lstrip())]  # leading only: trailing space is not indent
            block = [indent, indent, stripped]
        i += 1

    flush()
    result = newline.join(out)
    return result + newline if ends_with_newline else result


def process(paths, width, check):
    changed = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as handle:
                original = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            print("mdwrap: skipping %s: %s" % (path, exc), file=sys.stderr)
            continue
        wrapped = rewrap(original, width)
        if wrapped == original:
            continue
        if rewrap(wrapped, width) != wrapped:
            print("mdwrap: %s would not converge; leaving it untouched (please report)" % path, file=sys.stderr)
            continue
        changed.append(path)
        if not check:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(wrapped)
    return changed


_EXCLUDES = (
    ":(exclude)ThirdParty/**",
    ":(exclude)cmake-build-*/**",
    ":(exclude)**/_deps/**",
    ":(exclude)node_modules/**",
)


def _git(*args):
    return subprocess.run(("git",) + args, check=True, capture_output=True, text=True).stdout


def _markdown_paths(*diff_args):
    out = _git("diff", *diff_args, "--name-only", "-z", "--", "*.md", "*.markdown", *_EXCLUDES)
    return [p for p in out.split("\0") if p]


def _staged_blob(path):
    """The content git would commit for `path`, which is not always the worktree file."""
    result = subprocess.run(("git", "show", ":" + path), check=True, capture_output=True)
    return result.stdout.decode("utf-8")


def _stage_blob(path, text):
    """Replace the staged content of `path` with `text`, leaving the worktree file alone."""
    written = subprocess.run(("git", "hash-object", "-w", "--stdin"),
                             input=text.encode("utf-8"), check=True, capture_output=True)
    mode = _git("ls-files", "-s", "--", path).split()[0]
    _git("update-index", "--cacheinfo", "%s,%s,%s" % (mode, written.stdout.decode().strip(), path))


def _report(lines):
    for line in lines:
        print(line, file=sys.stderr)


def run_staged(width):
    os.chdir(_git("rev-parse", "--show-toplevel").strip())
    staged = _markdown_paths("--cached", "--diff-filter=ACMR")
    if not staged:
        return 0

    # Work on the staged content, not the worktree file: a file can legitimately have
    # unstaged edits that must not be swept into the commit.
    dirty = set(_markdown_paths())
    rewrapped, index_only, already_ok = [], [], 0

    for path in staged:
        try:
            original = _staged_blob(path)
        except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
            _report(["mdwrap: cannot read staged %s: %s" % (path, exc)])
            continue

        wrapped = rewrap(original, width)
        if wrapped == original:
            already_ok += 1
            continue
        if rewrap(wrapped, width) != wrapped:
            _report(["mdwrap: %s would not converge; left untouched (please report)" % path])
            continue

        _stage_blob(path, wrapped)
        if path in dirty:
            index_only.append(path)
        else:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(wrapped)
            rewrapped.append(path)

    if rewrapped:
        _report(["mdwrap: rewrapped to %d columns and re-staged:" % width]
                + ["  %s" % p for p in rewrapped])
    if index_only:
        _report(["mdwrap: rewrapped the staged copy only, your unstaged edits are untouched:"]
                + ["  %s" % p for p in index_only]
                + ["  (run mdwrap.py on the file yourself to rewrap the working copy too)"])
    if not rewrapped and not index_only:
        _report(["mdwrap: %d staged Markdown file(s) already at %d columns" % (already_ok, width)])
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", metavar="FILE")
    parser.add_argument("--check", action="store_true", help="report instead of rewriting; exit 1 if any file differs")
    parser.add_argument("--staged", action="store_true", help="rewrap staged Markdown and re-stage it")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="column limit (default: %d)" % DEFAULT_WIDTH)
    args = parser.parse_args(argv)

    if args.staged:
        if args.paths:
            parser.error("--staged takes no FILE arguments")
        return run_staged(args.width)
    if not args.paths:
        parser.error("no input files")

    changed = process(args.paths, args.width, args.check)
    if args.check and changed:
        print("mdwrap: needs rewrapping to %d columns:" % args.width, file=sys.stderr)
        for path in changed:
            print("  %s" % path, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
