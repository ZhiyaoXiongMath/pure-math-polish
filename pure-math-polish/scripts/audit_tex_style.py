#!/usr/bin/env python3
"""Read-only, bounded static TeX style inventory. Not a TeX interpreter."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path


def uncomment(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        end = len(line)
        for i, char in enumerate(line):
            if char == "%":
                j = i - 1
                while j >= 0 and line[j] == "\\":
                    j -= 1
                if (i - 1 - j) % 2 == 0:
                    end = i
                    break
        out.append(line[:end] + ("\n" if end < len(line) and line.endswith("\n") else ""))
    return "".join(out)


def group(text: str, start: int, opening: str = "{", closing: str = "}") -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != opening:
        raise ValueError("Expected balanced group")
    depth, i = 1, start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return text[start+1:i], i + 1
        i += 1
    raise ValueError("Unbalanced group")


def audit_text(original: str) -> dict:
    text = uncomment(original)
    split = text.find("\\begin{document}")
    body = text[split:] if split >= 0 else ""
    defs, warnings = [], []
    pattern = re.compile(r"\\(newcommand|renewcommand|providecommand|DeclareMathOperator)(\*)?\s*")
    for match in pattern.finditer(text):
        i = match.end()
        try:
            if i < len(text) and text[i] == "{":
                name, i = group(text, i)
            else:
                m = re.match(r"\\(?:[A-Za-z@]+|.)", text[i:])
                if not m:
                    raise ValueError("Unrecognized macro name")
                name, i = m.group(), i + len(m.group())
            opts = []
            for _ in range(2):
                while i < len(text) and text[i].isspace():
                    i += 1
                if i < len(text) and text[i] == "[":
                    value, i = group(text, i, "[", "]")
                    opts.append(value)
            definition, _ = group(text, i)
            uses = len(re.findall(re.escape(name) + (r"(?![A-Za-z@])" if name[-1:].isalpha() else ""), body))
            defs.append(dict(kind=match.group(1), name=name, options=opts, definition=definition,
                             line=text.count("\n", 0, match.start()) + 1, body_occurrences=uses,
                             in_preamble=split >= 0 and match.start() < split))
        except ValueError as exc:
            warnings.append(dict(line=text.count("\n", 0, match.start())+1, reason=str(exc)))
    packages = []
    for m in re.finditer(r"\\(documentclass|usepackage|RequirePackage)\s*(\[[^\]]*\])?\s*\{([^}]*)\}", text):
        packages.append(dict(kind=m.group(1), options=m.group(2) or "", names=m.group(3), line=text.count("\n",0,m.start())+1))
    raw_defs = [dict(line=text.count("\n",0,m.start())+1, preview=text[m.start():m.start()+100])
                for m in re.finditer(r"\\(?:gdef|xdef|edef|def)\b", text)]
    dependencies = [m.group(0) for m in re.finditer(r"\\(?:input|include|bibliography|addbibresource)\s*\{[^}]*\}", text)]
    return dict(macros=defs, class_and_packages=packages, primitive_definitions_for_manual_review=raw_defs,
                dependencies=dependencies, parse_warnings=warnings,
                numbered_equation_environments=len(re.findall(r"\\begin\s*\{equation\}", body)),
                starred_equation_environments=len(re.findall(r"\\begin\s*\{equation\*\}", body)),
                limitations=["Not macro expansion: conditionals, scope, verbatim, catcodes and dynamic inputs require manual review",
                             "Occurrences inside body definitions may be counted; use is not proof of effective execution",
                             "A definition with zero body occurrences is not evidence of a frequent author habit",
                             "Packages and documentclass records are lexical, not a fully resolved effective preamble"])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    a = p.parse_args()
    data = a.source.read_bytes()
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("TeX file exceeds audit limit")
    result = audit_text(data.decode("utf-8", errors="replace"))
    result.update(source=str(a.source), sha256=hashlib.sha256(data).hexdigest())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
