#!/usr/bin/env python3
"""Verify the fixed paper-source corpus or inventory its TeX without executing it."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

from audit_tex_style import audit_text, uncomment

MAX_FILE = 16 * 1024 * 1024
EXPECTED_PAPERS = 20
EXPECTED_TEX = 27
SOURCE_SUFFIXES = {'.tex', '.cls', '.sty', '.bib', '.bbl', '.jpg', '.jpeg', '.png', '.json'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def checked(root: Path, name: str) -> Path:
    """Resolve a normal relative path without accepting symlinks or traversal."""
    rel = PurePosixPath(name)
    if not name or name == '.' or rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name or rel.as_posix() != name:
        raise ValueError(f'Unsafe relative path: {name!r}')
    root = root.resolve(strict=True)
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f'Symbolic link rejected: {name}')
    if not current.resolve().is_relative_to(root):
        raise ValueError(f'Path outside corpus: {name}')
    return current


def read_text(path: Path) -> str:
    if path.stat().st_size > MAX_FILE:
        raise ValueError(f'Source exceeds size limit: {path.name}')
    return path.read_bytes().decode('utf-8', errors='replace')


def records(root: Path) -> list[dict]:
    data = json.loads(read_text(checked(root, 'manifest.json')))
    if data.get('schema_version') != 2 or data.get('expected_papers') != EXPECTED_PAPERS:
        raise ValueError('Unrecognized corpus manifest')
    papers = data.get('papers')
    if not isinstance(papers, list) or len(papers) != EXPECTED_PAPERS:
        raise ValueError('Expected exactly 20 paper records')
    return papers


def verify(root: Path) -> dict:
    """Check membership and byte integrity; never make an authenticity claim."""
    errors, results, listed, ids = [], [], set(), set()
    try:
        papers = records(root)
        for r in papers:
            errs = []
            ident = r['id']
            if not re.fullmatch(r'\d{4}\.\d{4,5}v[1-9]\d*', ident) or ident in ids:
                errs.append('Invalid or duplicate paper identifier')
            ids.add(ident)
            if not r.get('title') or not r.get('authors') or not r.get('source_url'):
                errs.append('Missing source attribution')
            members = set()
            for item in r['files']:
                name = item['path']
                if name in listed:
                    errs.append('Duplicate source member: ' + name)
                listed.add(name)
                members.add(name)
                path = checked(root, name)
                if not name.startswith('papers/') or path.suffix.lower() not in SOURCE_SUFFIXES:
                    errs.append('Unexpected source member: ' + name)
                if not path.is_file():
                    errs.append('Missing source member: ' + name)
                    continue
                if path.stat().st_size > MAX_FILE:
                    errs.append('Source size limit: ' + name)
                    continue
                data = path.read_bytes()
                if len(data) != item['bytes'] or digest(data) != item['sha256']:
                    errs.append('Source digest/size mismatch: ' + name)
            tex = {name for name in members if name.endswith('.tex')}
            if tex != set(r['tex_files']) or len(r['tex_files']) != len(tex):
                errs.append('TeX membership mismatch')
            main = r['main']
            if main not in tex:
                errs.append('Main source is not a TeX member')
            else:
                clean = uncomment(read_text(checked(root, main)))
                if '\\documentclass' not in clean or '\\begin{document}' not in clean:
                    errs.append('Main source requires manual entry-point review')
            results.append({'id': ident, 'ok': not errs, 'tex_files': len(tex), 'errors': errs})
        actual = set()
        for path in root.rglob('*'):
            if path.is_symlink():
                errors.append('Symbolic link: ' + path.relative_to(root).as_posix())
            elif path.is_file():
                actual.add(path.relative_to(root).as_posix())
        if actual != listed | {'manifest.json'}:
            errors.append({'unexpected_or_missing_files': sorted(actual ^ (listed | {'manifest.json'}))})
        tex_count = sum(r['tex_files'] for r in results)
        if tex_count != EXPECTED_TEX:
            errors.append('Expected exactly 27 original TeX files')
        return {'ok': not errors and all(r['ok'] for r in results),
                'papers': results, 'paper_count': len(results), 'tex_files': tex_count,
                'source_files': len(listed), 'errors': errors,
                'limits': ['Byte identity against the fixed supplied source manifest',
                           'Not independent arXiv authenticity, current ranking or permission verification',
                           'No source execution, compilation or proof certification']}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {'ok': False, 'errors': errors + [str(exc)], 'papers': results}


def file_audit(path: Path, relative: str) -> dict:
    text = read_text(path)
    audit = audit_text(text)
    clean = uncomment(text)
    split = clean.find('\\begin{document}')
    offset = clean[:split].count('\n') if split >= 0 else 0
    body = clean[split:] if split >= 0 else clean
    audit.update(source=relative, sha256=digest(path.read_bytes()),
                 utf8_replacement_characters=text.count('\ufffd'), is_fragment=split < 0)
    final = {}
    for item in audit['macros']:
        if item['in_preamble'] or split < 0:
            final[item['name']] = dict(item)
    for name, item in final.items():
        calls = list(re.finditer(re.escape(name) + (r'(?![A-Za-z@])' if name[-1:].isalpha() else ''), body))
        item['body_occurrences'] = len(calls)
        item['first_use_line'] = offset + body[:calls[0].start()].count('\n') + 1 if calls else None
    audit['last_lexical_definitions'] = list(final.values())
    deps = []
    for match in re.finditer(r'\\(input|include)\s*(?:\{([^}]+)\}|([^\s%{}]+))', clean):
        name = match[2] or match[3]
        status = 'dynamic-unresolved'
        if '\\' not in name and '#' not in name:
            target = name if Path(name).suffix else name + '.tex'
            try:
                status = 'present' if checked(path.parent, target).is_file() else 'missing'
            except ValueError:
                status = 'unsafe'
        deps.append({'kind': match[1], 'name': name, 'status': status,
                     'line': clean[:match.start()].count('\n') + 1})
    audit['literal_inputs'] = deps
    return audit


def inventory(root: Path) -> dict:
    result = verify(root)
    if not result['ok']:
        raise ValueError('Corpus integrity check failed: ' + json.dumps(result['errors']))
    papers, files = [], {}
    for record in records(root):
        names = record['tex_files'] + [x['path'] for x in record['files'] if Path(x['path']).suffix in {'.cls', '.sty'}]
        for name in names:
            files[name] = file_audit(checked(root, name), name)
        main = files[record['main']]
        body = '\n'.join(uncomment(read_text(checked(root, n))).split('\\begin{document}', 1)[-1]
                         for n in record['tex_files'])
        macros = []
        for item in main['last_lexical_definitions']:
            item = dict(item)
            name = item['name']
            item['paper_lexical_occurrences'] = len(re.findall(re.escape(name) + (r'(?![A-Za-z@])' if name[-1:].isalpha() else ''), body))
            macros.append(item)
        papers.append({'id': record['id'], 'title': record['title'], 'main': record['main'],
                       'tex_files': record['tex_files'], 'class_and_packages': main['class_and_packages'],
                       'macros': macros, 'inputs': main['literal_inputs']})
    counts = collections.defaultdict(lambda: {'defined_papers': 0, 'used_papers': 0, 'occurrences': 0, 'variants': collections.Counter()})
    for paper in papers:
        for macro in paper['macros']:
            item = counts[macro['name']]
            count = macro['paper_lexical_occurrences']
            item['defined_papers'] += 1
            item['used_papers'] += bool(count)
            item['occurrences'] += count
            item['variants'][macro['definition']] += 1
    return {'schema_version': 2, 'corpus_check': result, 'papers': papers, 'files': files,
            'macro_counts': dict(sorted(counts.items())),
            'limits': ['Lexical inventory, not TeX expansion or effective-scope resolution',
                       'All supplied fragments are inventoried, including inactive appendices',
                       'A declared but unused macro is not evidence of habitual invocation',
                       'Class and package scopes, indirect uses and build dependencies need manual review']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['verify', 'audit'])
    parser.add_argument('corpus', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.corpus) if args.command == 'verify' else inventory(args.corpus)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            if args.output.resolve().is_relative_to(args.corpus.resolve()):
                raise ValueError('Reports must be written outside the read-only corpus')
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding='utf-8')
        else:
            print(text, end='')
        return 0 if result.get('ok', True) else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
