"""Tool regression checks; temporary fixtures are not manuscript templates."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'pure-math-polish'
sys.path.insert(0, str(SKILL / 'scripts'))
import author_templates
import build_tex
import edit_guard
import macro_conflicts
import profile_check
import release
from tex_preflight import Scanner


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.work = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def cli(self, script, *args):
        env = os.environ.copy()
        env['PYTHONUTF8'] = '0'
        env['PYTHONIOENCODING'] = 'utf-8'
        result = subprocess.run([sys.executable, '-B', str(SKILL / 'scripts' / script), *map(str, args)],
                                capture_output=True, env=env, timeout=30)
        return result, json.loads(result.stdout.decode('utf-8'))

    def test_release_integrity(self):
        result = release.verify(SKILL)
        self.assertTrue(result['ok'], result)
        self.assertEqual((result['paper_count'], result['tex_files']), (20, 27))

    def test_corpus_detects_modified_source(self):
        target = self.work / 'corpus'
        shutil.copytree(SKILL / release.CORPUS_PATH, target)
        paper = author_templates.records(target)[0]
        source = target / paper['main']
        source.write_bytes(source.read_bytes() + b'\n% altered\n')
        self.assertFalse(author_templates.verify(target)['ok'])

    def test_release_detects_changed_instructions(self):
        target = self.work / 'skill'
        shutil.copytree(SKILL, target)
        source = target / 'SKILL.md'
        source.write_bytes(source.read_bytes() + b'\nChanged.\n')
        self.assertFalse(release.verify(target)['ok'])

    def test_archive_rejects_traversal(self):
        path = self.work / 'unsafe.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            archive.writestr('pure-math-polish/../outside.txt', 'bad')
        with self.assertRaises(ValueError):
            release.validate_zip(path)

    def test_pack_roundtrip_is_deterministic(self):
        first, second = self.work / 'first.zip', self.work / 'second.zip'
        release.pack(SKILL, first)
        release.pack(SKILL, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            archive.extractall(self.work / 'unpacked')
        self.assertTrue(release.verify(self.work / 'unpacked/pure-math-polish')['ok'])

    def test_original_source_matches_profile(self):
        profile = json.loads((SKILL / 'profiles/hym-amsart.json').read_text(encoding='utf-8'))
        corpus = SKILL / release.CORPUS_PATH
        source = corpus / author_templates.records(corpus)[0]['main']
        self.assertTrue(profile_check.check(profile, source.read_text(encoding='utf-8'))['ok'])

    def test_profile_cli_reads_utf8_comments(self):
        source = self.write('main.tex', '% 中文注释\n\\documentclass{article}\n\\begin{document}Test.\\end{document}\n')
        result, report = self.cli('profile_check.py', SKILL / 'profiles/hym-amsart.json', source)
        self.assertEqual(result.returncode, 1, report)
        self.assertIn('Document class differs from selected profile', report['errors'])

    def test_macro_cli_preserves_utf8_definitions(self):
        before = self.write('before.tex', '\\newcommand{\\word}{中文甲}\n\\begin{document}\\word\\end{document}')
        after = self.write('after.tex', '\\newcommand{\\word}{中文乙}\n\\begin{document}\\word\\end{document}')
        result, report = self.cli('macro_conflicts.py', before, after)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report['changed_definitions'][0]['original_definition'], '中文甲')
        self.assertEqual(report['changed_definitions'][0]['target_definition'], '中文乙')

    def test_macro_conflict_reports_imaginary_factor(self):
        left = '\\newcommand{\\ddbar}{\\partial\\bar\\partial}\n\\begin{document}\\ddbar u\\end{document}'
        right = left.replace('{\\partial\\bar\\partial}', '{i\\partial\\bar\\partial}')
        report = macro_conflicts.compare(left, right)
        self.assertEqual(report['count'], 1)
        self.assertFalse(report['rewritten'])
        self.assertTrue(report['changed_definitions'][0]['call_lines'])

    def test_scope_detects_outside_change(self):
        before = self.write('before/main.tex', 'Title\nSTART\nOld abstract\nEND\nTheorem')
        after = self.write('after/main.tex', 'Title\nSTART\nNew abstract\nEND\nTheorem')
        regions = {'main.tex': {'start': 'START', 'end': 'END'}}
        self.assertTrue(edit_guard.compare(before.parent, after.parent, regions=regions)['ok'])
        after.write_text('Title\nSTART\nNew abstract\nEND\nChanged theorem', encoding='utf-8')
        self.assertFalse(edit_guard.compare(before.parent, after.parent, regions=regions)['ok'])

    def test_snapshot_cli_reads_utf8_filename(self):
        source = self.write('project/中文备注.txt', 'metadata')
        snapshot = self.write('snapshot.json', json.dumps(edit_guard.inventory(source.parent), ensure_ascii=False))
        result, report = self.cli('edit_guard.py', 'check', source.parent, snapshot)
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report['ok'])

    def test_preflight_finds_missing_reference(self):
        source = self.write('main.tex', '\\documentclass{article}\n\\begin{document}See \\ref{missing}.\\end{document}')
        report = Scanner(source).run()
        self.assertIn('unresolved_reference', [item['code'] for item in report['errors']])

    def test_preflight_resolves_included_label(self):
        source = self.write('main.tex', '\\documentclass{article}\n\\begin{document}\\input{part} See \\ref{known}.\\end{document}')
        self.write('part.tex', '\\section{Result}\\label{known}')
        self.assertEqual(Scanner(source).run()['errors'], [])

    def test_build_requires_reviewed_input(self):
        with self.assertRaises(ValueError):
            build_tex.build(self.work, 'main.tex', self.work / 'out', 'pdflatex', False)

    @unittest.skipUnless(shutil.which('pdflatex'), 'pdflatex is not installed')
    def test_actual_build_utf8_receipt_and_stale_detection(self):
        source = self.write('project/main.tex', '% 中文注释\n\\documentclass{article}\n\\begin{document}\\section{Test}\\label{test}See Section~\\ref{test}.\\end{document}\n')
        self.write('project/中文备注.txt', 'Build metadata; not a TeX input.')
        output = self.work / 'build'
        result = build_tex.build(source.parent, 'main.tex', output, 'pdflatex', True)
        receipt, pdf = output / 'build-receipt.json', output / 'main.pdf'
        self.assertEqual(json.loads(receipt.read_text(encoding='utf-8'))['status'], 'compiled')
        self.assertTrue(build_tex.verify_receipt(source.parent, receipt, pdf)['ok'])
        source.write_bytes(source.read_bytes() + b'\n% changed\n')
        self.assertFalse(build_tex.verify_receipt(source.parent, receipt, pdf)['ok'])
        self.assertEqual(result['diagnostics']['blockers'], {})


if __name__ == '__main__':
    unittest.main()
