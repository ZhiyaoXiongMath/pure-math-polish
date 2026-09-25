#!/usr/bin/env python3
"""Read-only, standard-library diagnostics for literal TeX links and bibliography keys.

This is not a TeX interpreter, a compiler, or an assessment of manuscript quality.
Exit 1 means static errors were detected; exit 0 means only that none were detected.
Every report includes the limits of the analysis. No TeX or network commands run.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


COMMAND = re.compile(r"\\([A-Za-z@]+|.)", re.DOTALL)
REFS = {"ref", "eqref", "pageref", "autoref", "cref", "Cref", "vref", "Vref"}
CITES = {
    "cite", "Cite", "citep", "Citep", "citet", "Citet", "citealp", "citealt",
    "citeauthor", "Citeauthor", "citeyear", "citeyearpar", "citenum", "nocite",
    "textcite", "Textcite", "parencite", "Parencite", "autocite", "Autocite",
    "footcite", "footcitetext", "smartcite", "supercite", "fullcite", "footfullcite",
}
DEFINITIONS = {
    "newcommand", "renewcommand", "providecommand", "DeclareRobustCommand",
    "newenvironment", "renewenvironment", "NewDocumentCommand",
    "RenewDocumentCommand", "ProvideDocumentCommand", "DeclareDocumentCommand",
    "def", "gdef", "edef", "xdef",
}
VERBATIM_ENVS = {"verbatim", "verbatim*", "Verbatim", "lstlisting", "minted", "comment"}


def skip_space(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def group(text: str, pos: int, opening: str = "{", quotes: bool = False) -> tuple[str, int] | None:
    """Read balanced literal delimiters; do not expand tokens or alter catcodes."""
    pos = skip_space(text, pos)
    if pos >= len(text) or text[pos] != opening:
        return None
    closing = {"{": "}", "[": "]", "(": ")"}[opening]
    start, depth, brace_depth = pos + 1, 1, 0
    in_quote = False
    pos += 1
    while pos < len(text):
        ch = text[pos]
        if ch == "\\":
            pos += 2
            continue
        if quotes and ch == '"' and (in_quote or (depth == 1 and not brace_depth)):
            in_quote = not in_quote
            pos += 1
            continue
        if in_quote:
            pos += 1
            continue
        if opening != "{" and ch == "{":
            brace_depth += 1
        elif opening != "{" and ch == "}" and brace_depth:
            brace_depth -= 1
        elif not brace_depth and ch == opening:
            depth += 1
        elif not brace_depth and ch == closing:
            depth -= 1
            if depth == 0:
                return text[start:pos], pos + 1
        pos += 1
    return None


def clean_tex(text: str) -> str:
    """Mask ordinary comments and common verbatim forms, preserving line offsets."""
    chars = list(text)
    pos = 0

    def mask(start: int, end: int) -> None:
        for i in range(start, end):
            if chars[i] not in "\r\n":
                chars[i] = " "

    while pos < len(text):
        if text[pos] == "%":
            end = text.find("\n", pos)
            end = len(text) if end < 0 else end
            mask(pos, end)
            pos = end
            continue
        if text[pos] != "\\":
            pos += 1
            continue
        match = COMMAND.match(text, pos)
        if not match:
            pos += 1
            continue
        name, end = match.group(1), match.end()
        if name == "verb":
            if end < len(text) and text[end] == "*":
                end += 1
            if end < len(text) and not text[end].isspace():
                close = text.find(text[end], end + 1)
                newline = text.find("\n", end)
                if close >= 0 and (newline < 0 or close < newline):
                    mask(pos, close + 1)
                    pos = close + 1
                    continue
        if name == "begin":
            arg = group(text, end)
            if arg and arg[0] in VERBATIM_ENVS:
                marker = "\\end{" + arg[0] + "}"
                close = text.find(marker, arg[1])
                end = len(text) if close < 0 else close + len(marker)
                mask(pos, end)
        pos = end
    return "".join(chars)


def literal(value: str) -> bool:
    return bool(value.strip()) and not any(c in value for c in "\\#{}$~^%\n\r")


class Scanner:
    def __init__(self, main: Path, root: Path | None = None):
        self.main = main.resolve()
        self.root = (root or self.main.parent).resolve()
        self.errors: list[dict] = []
        self.limitations: list[dict] = [
            {"code": "static_scope", "message": "Only literal commands and local files are inspected. Macro expansion, package-defined commands, catcode changes, conditionals, includeonly, external aux files, and TeX search paths are not evaluated; findings may include inactive text or omit generated content."},
            {"code": "no_quality_assessment", "message": "These diagnostics do not certify compilation, rendering, mathematics, prose/AI style, standard notation, citation relevance, or historical/bibliographic accuracy."},
            {"code": "path_resolution", "message": f"Relative dependencies are resolved from the declared compilation directory: {self.root}. No TEXINPUTS, package search, remote resources, or generated files are used."},
            {"code": "bibliography_scope", "message": "Bibliography scanning extracts local entry headers and literal bibitem keys, not complete BibTeX/biber syntax, fields, crossref inheritance, sourcemaps, or metadata correctness."},
        ]
        self.diagnostics: list[dict] = []
        self.labels: dict[str, list[dict]] = {}
        self.refs: dict[str, list[dict]] = {}
        self.cites: dict[str, list[dict]] = {}
        self.bib: set[str] = set()
        self.bib_seen: set[Path] = set()
        self.files: set[Path] = set()
        self.inclusions = 0

    def note(self, bucket: str, code: str, message: str, loc: dict | None = None) -> None:
        item = {"code": code, "message": message, **(loc or {})}
        target = getattr(self, bucket)
        if item not in target:
            target.append(item)

    def read(self, path: Path, loc: dict | None = None) -> str | None:
        try:
            return path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            self.note("errors", "unreadable_file", f"Cannot read local UTF-8 file {path}: {exc}", loc)
            return None

    def keys(self, value: str, target: dict[str, list[dict]], loc: dict, command: str, multiple: bool = True) -> None:
        if command == "nocite" and value.strip() == "*":
            self.note("diagnostics", "nocite_all", "\\nocite{*} does not request a literal citation key.", loc)
            return
        for key in value.split(",") if multiple else [value]:
            key = key.strip()
            if not key:
                self.note("errors", "empty_key", f"Empty key in \\{command}.", loc)
            elif not literal(key) or any(c.isspace() for c in key):
                self.note("limitations", "nonliteral_key", f"Key in \\{command} cannot be resolved literally: {key!r}.", loc)
            else:
                target.setdefault(key, []).append(loc)

    def dependency(self, raw: str, suffix: str, loc: dict, kind: str) -> Path | None:
        raw = raw.strip()
        if not raw:
            self.note("errors", "empty_dependency", f"Empty {kind} filename.", loc)
            return None
        if not literal(raw) or "://" in raw:
            self.note("limitations", "nonliteral_dependency", f"Cannot resolve {kind} dependency literally: {raw!r}.", loc)
            return None
        path = self.root / raw
        if not path.suffix:
            path = path.with_suffix(suffix)
        path = path.resolve()
        if not path.is_file():
            self.note("errors", "missing_dependency", f"Missing {kind} file: {path}", loc)
            return None
        return path

    def bibliography(self, path: Path, loc: dict) -> None:
        if path in self.bib_seen:
            return
        self.bib_seen.add(path)
        text = self.read(path, loc)
        if text is None:
            return
        # Consume entire balanced entries so @-strings inside fields are not keys.
        header = re.compile(r"@([A-Za-z]+)\s*([({])")
        pos, count = 0, 0
        while match := header.search(text, pos):
            ignored = match.group(1).lower() in {"comment", "preamble", "string"}
            entry = group(text, match.end() - 1, match.group(2), quotes=not ignored)
            if not entry:
                self.note("limitations", "unparsed_bibliography", f"Unbalanced entry in {path}; remaining entry keys were not inspected.", loc)
                break
            body, pos = entry
            if ignored:
                continue
            key, sep, _ = body.partition(",")
            key = key.strip()
            if sep and literal(key) and not any(c.isspace() for c in key):
                self.bib.add(key)
                count += 1
            else:
                self.note("limitations", "unparsed_bibliography", f"Entry key could not be read literally in {path}.", loc)
        self.diagnostics.append({"code": "bibliography_file", "path": str(path), "entry_headers_detected": count})
        if count == 0:
            self.note("diagnostics", "no_bibliography_keys", f"No entry keys detected in {path}.", loc)

    def skip_definition(self, text: str, pos: int, name: str) -> int:
        if name in {"def", "gdef", "edef", "xdef"}:
            opening = text.find("{", pos)
            body = group(text, opening) if opening >= 0 else None
            return body[1] if body else len(text)
        pos = skip_space(text, pos)
        if pos < len(text) and text[pos] == "*":
            pos += 1
        arg = group(text, pos)
        if arg:
            pos = arg[1]
        else:
            token = COMMAND.match(text, skip_space(text, pos))
            if not token:
                return pos
            pos = token.end()
        while option := group(text, pos, "["):
            pos = option[1]
        bodies = 2 if ("environment" in name or "DocumentCommand" in name) else 1
        for _ in range(bodies):
            body = group(text, pos)
            if not body:
                return pos
            pos = body[1]
        return pos

    def scan_file(self, path: Path, stack: tuple[Path, ...] = ()) -> None:
        if path in stack:
            self.note("errors", "input_cycle", "Recursive input cycle: " + " -> ".join(map(str, (*stack, path))))
            return
        if len(stack) >= 100:
            self.note("limitations", "depth_limit", f"Stopped nested input at {path} after 100 active files.")
            return
        if self.inclusions >= 10000:
            self.note("limitations", "visit_limit", "Stopped after 10000 literal TeX file visits; remaining dependencies were not inspected.")
            return
        raw = self.read(path)
        if raw is None:
            return
        self.files.add(path)
        self.inclusions += 1
        text = clean_tex(raw)
        pos = 0
        while match := COMMAND.search(text, pos):
            name, pos = match.group(1), match.end()
            loc = {"path": str(path), "line": text.count("\n", 0, match.start()) + 1}
            if name == "endinput":
                break
            if name in DEFINITIONS:
                self.note("limitations", "macro_definition", f"\\{name} replacement text is skipped; invocations are not expanded.", loc)
                pos = self.skip_definition(text, pos, name)
                continue
            known = name in REFS | CITES | {"label", "bibitem", "input", "include", "bibliography", "addbibresource"}
            if not known:
                if "cite" in name.lower() or name in {"import", "subimport", "inputfrom", "subfile", "includeonly", "csname", "catcode"}:
                    self.note("limitations", "unsupported_command", f"\\{name} is not interpreted; review its generated keys/dependencies manually.", loc)
                continue
            pos = skip_space(text, pos)
            if pos < len(text) and text[pos] == "*":
                pos += 1
            while option := group(text, pos, "["):
                pos = option[1]
            arg = group(text, pos)
            if not arg:
                self.note("limitations", "unparsed_argument", f"\\{name} needs a balanced braced literal argument for this scanner; remaining tokens are scanned lexically.", loc)
                continue
            value, pos = arg
            if name == "label":
                self.keys(value, self.labels, loc, name, multiple=False)
            elif name in REFS:
                self.keys(value, self.refs, loc, name, multiple=name in {"cref", "Cref"})
            elif name in CITES:
                self.keys(value, self.cites, loc, name)
            elif name == "bibitem":
                temporary: dict[str, list[dict]] = {}
                self.keys(value, temporary, loc, name, multiple=False)
                self.bib.update(temporary)
            elif name in {"input", "include"}:
                child = self.dependency(value, ".tex", loc, "TeX input")
                if child:
                    self.scan_file(child, (*stack, path))
            else:
                resources = value.split(",") if name == "bibliography" else [value]
                for resource in resources:
                    bib = self.dependency(resource, ".bib", loc, "bibliography")
                    if bib:
                        self.bibliography(bib, loc)

    def run(self) -> dict:
        self.scan_file(self.main)
        for key, locations in sorted(self.labels.items()):
            if len(locations) > 1:
                self.errors.append({"code": "duplicate_label", "message": f"Label {key!r} occurs {len(locations)} times in the literal input expansion.", "key": key, "locations": locations})
        for target, definitions, code in [
            (self.refs, self.labels, "unresolved_reference"),
            (self.cites, self.bib, "unresolved_citation"),
        ]:
            for key in sorted(target.keys() - set(definitions)):
                self.errors.append({"code": code, "message": f"No literal definition found for {key!r} in the inspected files; generated/external definitions are outside scope.", "key": key, "locations": target[key]})
        self.diagnostics.insert(0, {
            "code": "inventory", "main": str(self.main), "unique_tex_files": len(self.files),
            "tex_file_visits": self.inclusions, "label_occurrences": sum(map(len, self.labels.values())),
            "distinct_reference_keys": len(self.refs), "distinct_citation_keys": len(self.cites),
            "bibliography_keys_detected": len(self.bib),
        })
        return {"errors": self.errors, "limitations": self.limitations, "diagnostics": self.diagnostics}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tex", type=Path, help="Main UTF-8 TeX file (read only)")
    parser.add_argument("--root", type=Path, help="Compilation directory for literal relative paths; default: main file's directory")
    parser.add_argument("--json", action="store_true", help="Emit errors, limitations, and diagnostics as JSON")
    args = parser.parse_args()
    report = Scanner(args.tex, args.root).run()
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        for bucket, entries in report.items():
            print(f"{bucket}: {len(entries)}")
            for entry in entries:
                print("  " + json.dumps(entry, ensure_ascii=True))
        print("Exit 0 means no static errors detected within the stated scope; it is not manuscript approval.")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
