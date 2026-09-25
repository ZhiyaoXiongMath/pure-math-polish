#!/usr/bin/env python3
"""Read-only source snapshots and explicit edit-scope comparison; no TeX semantics."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path, PurePosixPath

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe_relative(name: str) -> str:
    p = PurePosixPath(name)
    if not name or p.is_absolute() or '..' in p.parts or '\\' in name or p.as_posix() != name or name == '.' or ':' in name:
        raise ValueError(f'Unsafe relative path: {name!r}')
    return name

def inventory(root: Path) -> dict[str, str]:
    root = root.resolve(strict=True)
    if not root.is_dir(): raise ValueError('Expected a project directory')
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink(): raise ValueError(f'Symbolic link not allowed: {p}')
        if p.is_file(): result[p.relative_to(root).as_posix()] = digest(p)
    return result

def check_snapshot(root: Path, expected: dict[str, str]) -> dict:
    for name in expected: safe_relative(name)
    actual = inventory(root)
    changed = sorted(k for k in set(actual) | set(expected) if actual.get(k) != expected.get(k))
    return {'ok': not changed, 'changed': changed, 'meaning': 'byte identity, not mathematical equivalence'}

def outside_region(data: bytes, start: bytes, end: bytes) -> tuple[bytes, bytes]:
    if not start or not end or start == end: raise ValueError('Distinct nonempty literal markers required')
    if data.count(start) != 1 or data.count(end) != 1:
        raise ValueError('Markers must occur exactly once; dynamic or ambiguous TeX needs manual scope audit')
    a = data.index(start) + len(start); b = data.index(end)
    if b < a: raise ValueError('End marker precedes start')
    return data[:a], data[b:]

def compare(before: Path, after: Path, allowed_files: list[str] | None = None,
            regions: dict[str, dict[str, str]] | None = None) -> dict:
    allowed = {safe_relative(n) for n in (allowed_files or [])}
    regions = regions or {}
    for name in regions: safe_relative(name)
    if allowed & regions.keys(): raise ValueError('Do not give both whole-file and region authorization')
    b, a = inventory(before), inventory(after)
    changed = sorted(n for n in set(b) | set(a) if b.get(n) != a.get(n))
    violations, limitations = [], []
    for name in changed:
        if name in allowed: continue
        if name not in regions or name not in a or name not in b:
            violations.append(name); continue
        spec = regions[name]
        try:
            left = outside_region((before/name).read_bytes(), spec['start'].encode(), spec['end'].encode())
            right = outside_region((after/name).read_bytes(), spec['start'].encode(), spec['end'].encode())
            if left != right: violations.append(name)
        except (ValueError, KeyError) as exc:
            violations.append(name); limitations.append({'file': name, 'reason': str(exc)})
    return {'ok': not violations, 'changed': changed, 'out_of_scope': violations,
            'limitations': limitations, 'meaning': 'authorized byte regions only; not a TeX parser'}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('snapshot');a.add_argument('root',type=Path)
    a=sub.add_parser('check');a.add_argument('root',type=Path);a.add_argument('snapshot',type=Path)
    a=sub.add_parser('compare');a.add_argument('before',type=Path);a.add_argument('after',type=Path)
    a.add_argument('--allow-file',action='append',default=[]);a.add_argument('--regions',type=Path)
    args=p.parse_args()
    try:
        if args.cmd=='snapshot': result=inventory(args.root)
        elif args.cmd=='check': result=check_snapshot(args.root,json.loads(args.snapshot.read_text(encoding='utf-8-sig')))
        else: result=compare(args.before,args.after,args.allow_file,
                             json.loads(args.regions.read_text(encoding='utf-8-sig')) if args.regions else {})
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('ok',True) else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 2
if __name__=='__main__':sys.exit(main())
