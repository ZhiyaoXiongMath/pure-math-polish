# Pure Math Polish

A Codex skill for polishing pure-mathematics LaTeX manuscripts while preserving mathematical meaning, authorship, language, and the requested editing scope.

**Version 1.3.0** · [Download the skill ZIP](https://github.com/ZhiyaoXiongMath/pure-math-polish/releases/download/v1.3.0/pure-math-polish-1.3.0.zip) · [Release](https://github.com/ZhiyaoXiongMath/pure-math-polish/releases/tag/v1.3.0)

## What it does

- Selects an appropriate author style from 20 fixed-version Xiaokui Yang papers, including coauthored works: 27 original TeX files and their supporting sources.
- Improves abstracts, introductions, theorem statements, proof exposition, notation, and verified literature positioning.
- Checks macro meanings and call sites before migrating LaTeX layout or notation.
- Respects partial-edit requests and preserves mathematical assumptions, conclusions, dependencies, and valid labels.
- Delivers editable TeX and, when compilation is available, the corresponding PDF with concise change notes.

The original papers are the only template corpus. The HYM JSON profile is a source-backed checking aid, not another template. Repository tests use temporary fixtures outside the distributed skill.

## Install

Extract the release ZIP and copy its complete `pure-math-polish/` folder into your Codex skills directory, normally `~/.codex/skills/`. Alternatively, copy the [`pure-math-polish/`](pure-math-polish/) directory from this repository. Invoke it with `$pure-math-polish` and specify the manuscript and editing scope.

Python 3.10+ is required for the helpers; release validation requires PyYAML. PDF builds require an installed TeX engine and the manuscript's dependencies. Fonts are not bundled.

## Documentation

- [Skill workflow](pure-math-polish/SKILL.md)
- [The 20 paper templates](pure-math-polish/assets/templates/INDEX.md)
- [Mathematical writing](pure-math-polish/references/mathematical-writing.md)
- [LaTeX migration](pure-math-polish/references/latex-migration.md)
- [Build and delivery](pure-math-polish/references/build-and-delivery.md)
- [Source attribution](pure-math-polish/NOTICE.md)

## Verification

From the repository root:

```sh
python -B pure-math-polish/scripts/release.py verify pure-math-polish
python -B pure-math-polish/scripts/author_templates.py verify pure-math-polish/assets/templates/xiaokui-yang-20
python -B -m unittest discover -s tests -v
```

The 15 regression tests cover source integrity, package round trips, macro conflicts, references, authorized edit regions, UTF-8 input and receipts, and stale-PDF detection. The actual build test requires `pdflatex` and explicitly skips when it is unavailable.

These checks establish tool behavior and package integrity. They do not certify mathematical proofs, provide a fresh model editing benchmark, or establish that all 20 original papers compile on every platform. Final manuscript review and PDF inspection remain part of each editing task.

## Attribution

Original source bytes, authorship, version metadata, and supplied license URLs are preserved. The skill does not relicense the papers or imply author endorsement. Consult [NOTICE.md](pure-math-polish/NOTICE.md) and each paper's metadata for the applicable terms.
