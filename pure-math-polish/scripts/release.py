#!/usr/bin/env python3
"""Check and deterministically package the Pure Math Polish distribution."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

try:
    import yaml
except ImportError as exc:
    raise SystemExit('Release validation requires PyYAML.') from exc

from author_templates import verify as verify_corpus

FONT_EXT = {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.pfb', '.pfa', '.eot'}
ROOT_FILES = {'SKILL.md', 'README.md', 'NOTICE.md', 'VERSION', 'MANIFEST.sha256'}
ROOT_DIRS = {'agents', 'assets', 'profiles', 'references', 'scripts'}
CORPUS_PATH = 'assets/templates/xiaokui-yang-20'
MAX_FILES = 2048
MAX_TOTAL = 64 * 1024 * 1024


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys rather than accepting hidden overrides."""


def mapping(loader, node, deep=False):
    result = {}
    for k, v in node.value:
        key = loader.construct_object(k, deep=deep)
        if key in result:
            raise ValueError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(v, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load_yaml(text: str):
    return yaml.load(text, Loader=UniqueLoader)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or name == '.' or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or path.as_posix() != name:
        raise ValueError(f'Unsafe relative path: {name!r}')
    return name


def files(root: Path) -> dict[str, Path]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Expected a skill directory')
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symbolic link: {path.name}')
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if path.is_file():
            name = safe_name(path.relative_to(root).as_posix())
            result[name] = path
    if len(result) > MAX_FILES or sum(p.stat().st_size for p in result.values()) > MAX_TOTAL:
        raise ValueError('Distribution exceeds size limits')
    return result


def allowed(name: str) -> bool:
    path = PurePosixPath(name)
    if len(path.parts) == 1:
        return name in ROOT_FILES
    if path.parts[0] not in ROOT_DIRS:
        return False
    if path.suffix.lower() in FONT_EXT | {'.log', '.pdf', '.aux', '.out', '.toc', '.pyc', '.zip', '.gz'}:
        return False
    if path.suffix.lower() in {'.tex', '.cls', '.sty', '.bib', '.bbl'}:
        return name.startswith(CORPUS_PATH + '/papers/')
    if path.parts[0] == 'assets':
        return name in {'assets/icon.svg', 'assets/templates/INDEX.md'} or name.startswith(CORPUS_PATH + '/')
    return True


def manifest(root: Path) -> str:
    entries = files(root)
    invalid = [name for name in entries if not allowed(name)]
    if invalid:
        raise ValueError('Unexpected distribution members: ' + ', '.join(invalid))
    return ''.join(f'{sha(path.read_bytes())}  {name}\n' for name, path in entries.items() if name != 'MANIFEST.sha256')


def verify(root: Path) -> dict:
    errors = []
    try:
        root = root.resolve(strict=True)
        entries = files(root)
        listed = {}
        for line in (root/'MANIFEST.sha256').read_text(encoding='utf-8').splitlines():
            match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
            if not match:
                raise ValueError('Malformed manifest line')
            digest, name = match.groups()
            safe_name(name)
            if name in listed:
                raise ValueError('Duplicate manifest path: ' + name)
            listed[name] = digest
        actual = {name: sha(path.read_bytes()) for name, path in entries.items() if name != 'MANIFEST.sha256'}
        changed = sorted(name for name in set(listed) | set(actual) if listed.get(name) != actual.get(name))
        if changed:
            errors.append({'manifest_mismatch': changed})
        invalid = [name for name in entries if not allowed(name)]
        if invalid:
            errors.append({'unexpected_files': invalid})
        text = (root/'SKILL.md').read_text(encoding='utf-8')
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        if not match:
            raise ValueError('Missing skill front matter')
        meta = load_yaml(match[1])
        agent = load_yaml((root/'agents/openai.yaml').read_text(encoding='utf-8'))
        version = (root/'VERSION').read_text(encoding='utf-8').strip()
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            errors.append('Invalid version')
        if meta.get('name') != 'pure-math-polish':
            errors.append('Skill identifier mismatch')
        if not isinstance(meta.get('description'), str) or not meta['description'].strip():
            errors.append('Missing skill description')
        if str(meta.get('metadata', {}).get('version')) != version:
            errors.append('Version metadata mismatch')
        interface = agent.get('interface', {})
        if interface.get('display_name') != 'Pure Math Polish':
            errors.append('Display name mismatch')
        if '$pure-math-polish' not in interface.get('default_prompt', ''):
            errors.append('Default invocation mismatch')
        for key in ('icon_small', 'icon_large'):
            name = safe_name(interface.get(key, ''))
            if name not in entries:
                errors.append('Missing icon: ' + name)
        # Check relative Markdown links in distribution-owned documentation.
        for name, path in entries.items():
            if path.suffix != '.md':
                continue
            body = re.sub(r'(?ms)^(```|~~~)[^\n]*\n.*?^\1\s*$', '', path.read_text(encoding='utf-8'))
            for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)', body):
                if re.match(r'[a-zA-Z][\w+.-]*:|//|#', target):
                    continue
                target = target.split('#', 1)[0]
                if not target:
                    continue
                dest = (path.parent/target).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    errors.append(f'Broken local link: {name} -> {target}')
        corpus = verify_corpus(root/CORPUS_PATH)
        if not corpus['ok']:
            errors.append({'corpus': corpus})
        # Verify that style evidence refers to unchanged real source definitions.
        from audit_tex_style import audit_text
        for profile_path in (root/'profiles').glob('*.json'):
            profile = json.loads(profile_path.read_text(encoding='utf-8'))
            if profile.get('corpus') != CORPUS_PATH:
                errors.append('Unknown profile corpus: ' + profile_path.name)
                continue
            source_records = {}
            for name, rule in profile.get('macros', {}).items():
                rel = safe_name(rule['source'])
                path = root/CORPUS_PATH/rel
                if path not in source_records:
                    source_records[path] = audit_text(path.read_text(encoding='utf-8', errors='replace'))['macros']
                matches = [m for m in source_records[path] if m['name'] == name and m['line'] == rule['definition_line']]
                if not matches or matches[0]['definition'] != rule['definition'] or matches[0]['options'] != rule['options']:
                    errors.append('Profile evidence mismatch: ' + name)
        return {'ok': not errors, 'version': version, 'files_including_manifest': len(entries),
                'paper_count': corpus.get('paper_count'), 'tex_files': corpus.get('tex_files'),
                'errors': errors, 'limits': ['Distribution integrity, not host installation',
                                           'No mathematical proof or rendered-style certification']}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as exc:
        return {'ok': False, 'errors': errors + [str(exc)]}


def validate_zip(path: Path) -> list[str]:
    names, seen, total = [], set(), 0
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > MAX_FILES:
            raise ValueError('Too many archive entries')
        for item in archive.infolist():
            name = safe_name(item.filename[:-1] if item.is_dir() else item.filename)
            parts = PurePosixPath(name).parts
            if parts[0] != 'pure-math-polish' or (len(parts) == 1 and not item.is_dir()):
                raise ValueError('Wrong archive root')
            if name in seen:
                raise ValueError('Duplicate archive entry')
            seen.add(name)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Archive contains a symbolic link')
            total += item.file_size
            if total > MAX_TOTAL:
                raise ValueError('Expanded archive exceeds size limit')
            if not item.is_dir():
                relative = '/'.join(parts[1:])
                if not allowed(relative) or '__pycache__' in parts:
                    raise ValueError('Unexpected archive member: ' + name)
                names.append(name)
        if archive.testzip() is not None:
            raise ValueError('Corrupt archive')
    if not names:
        raise ValueError('Empty archive')
    return names


def pack(root: Path, output: Path) -> dict:
    root, output = root.resolve(), output.resolve()
    if output.is_relative_to(root):
        raise ValueError('Archive must be outside the skill root')
    if output.exists():
        raise ValueError('Refuses to overwrite an archive')
    result = verify(root)
    if not result['ok']:
        raise ValueError('Verify before packaging: ' + json.dumps(result, ensure_ascii=False))
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in files(root).items():
            entry = zipfile.ZipInfo('pure-math-polish/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    names = validate_zip(output)
    return {'ok': True, 'entries': len(names), 'sha256': sha(output.read_bytes())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('manifest', 'verify'):
        child = commands.add_parser(command)
        child.add_argument('root', type=Path)
    child = commands.add_parser('pack')
    child.add_argument('root', type=Path)
    child.add_argument('output', type=Path)
    child = commands.add_parser('check-zip')
    child.add_argument('archive', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'manifest':
            print(manifest(args.root), end='')
            return 0
        if args.command == 'verify':
            result = verify(args.root)
        elif args.command == 'pack':
            result = pack(args.root, args.output)
        else:
            result = {'ok': True, 'entries': len(validate_zip(args.archive))}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['ok'] else 1
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 2


if __name__ == '__main__':
    sys.exit(main())
