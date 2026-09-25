#!/usr/bin/env python3
"""Explicit, fresh TeX build with source/PDF receipt. NOT an operating-system sandbox."""
from __future__ import annotations
import argparse, datetime, json, os, re, shutil, subprocess, sys
from pathlib import Path
from edit_guard import inventory, digest, safe_relative

FATAL_PATTERNS = {
 'undefined-reference-or-citation': r'(?:Reference|Citation) .+ undefined|There were undefined references',
 'rerun-required': r'Label\(s\) may have changed|Rerun to get|Please \(re\)run',
 'duplicate-label': r'multiply[- ]defined|multiply defined',
 'missing-glyph': r'Missing character:',
 'tex-error': r'^!|LaTeX Error:',
}

def diagnose(text: str) -> dict:
    blockers={k:re.findall(v,text,re.M) for k,v in FATAL_PATTERNS.items() if re.search(v,text,re.M)}
    warnings=[s.strip() for s in text.splitlines() if re.search(r'Warning:|Overfull|Underfull',s)]
    return {'blockers':blockers,'warnings':warnings}

def verify_receipt(project: Path, receipt: Path, pdf: Path) -> dict:
    r=json.loads(receipt.read_text(encoding='utf-8'))
    if r.get('status')!='compiled': return {'ok':False,'reason':'No successful build receipt'}
    actual=inventory(project)
    return {'ok':actual==r['project_inputs'] and digest(pdf)==r['pdf_sha256'],
            'source_match':actual==r['project_inputs'],'pdf_match':digest(pdf)==r['pdf_sha256']}

def build(project: Path, main: str, output: Path, engine: str, reviewed: bool) -> dict:
    if not reviewed: raise ValueError('Explicit --reviewed-input required after human source/dependency review; this is not a sandbox')
    if engine not in {'xelatex','pdflatex'}: raise ValueError('Supported explicit engines: xelatex, pdflatex')
    project=project.resolve(strict=True); safe_relative(main)
    source=project/main
    if not source.is_file() or source.suffix!='.tex':raise ValueError('Main must be an existing .tex inside project')
    if source.stem.startswith('-'):raise ValueError('Unsafe job name')
    output=output.resolve()
    if output==project or project in output.parents:raise ValueError('Build outside the source project')
    if output.exists():raise ValueError('Output directory must not exist; refuses stale artifacts or overwrite')
    before=inventory(project)
    executable=shutil.which(engine)
    if not executable:raise ValueError(f'TeX engine not installed: {engine}')
    # This bounded guard supplements, never replaces, human review.
    for name in before:
        if Path(name).suffix.lower() in {'.tex','.sty','.cls'}:
            t=(project/name).read_text(encoding='utf-8',errors='replace')
            if re.search(r'\\(?:write18|directlua|latelua|luaexec)\b|\\(?:input|include)\s*[\{"\s]*\|',t):
                raise ValueError(f'External execution construct requires a separately sandboxed workflow: {name}')
    output.mkdir(parents=True)
    cmd=[executable,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error',
         '-recorder',f'-output-directory={output}',main]
    env=os.environ.copy();env['openout_any']='p';env['shell_escape']='f'
    try:
        for i in range(1,4):
            run=subprocess.run(cmd,cwd=project,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               timeout=120,check=False)
            (output/f'pass-{i}.stdout').write_bytes(run.stdout)
            if run.returncode:raise RuntimeError(f'{engine} pass {i} failed; see {output}/pass-{i}.stdout')
        final_log=output/(source.stem+'.log'); pdf=output/(source.stem+'.pdf')
        if not final_log.is_file() or not pdf.is_file():raise RuntimeError('Engine did not produce expected log/PDF')
        diagnostics=diagnose(final_log.read_text(encoding='utf-8',errors='replace'))
        if diagnostics['blockers']:raise RuntimeError('Final log has blocking diagnostics: '+json.dumps(diagnostics['blockers']))
        after=inventory(project)
        if before!=after:raise RuntimeError('Source project changed during build; do not deliver this PDF')
        version=subprocess.run([executable,'--version'],stdout=subprocess.PIPE,timeout=10,check=True).stdout.decode(errors='replace').splitlines()[0]
        receipt={'status':'compiled','main':main,'engine':engine,'engine_version':version,'passes':3,
                 'project_inputs':before,'pdf_sha256':digest(pdf),'diagnostics':diagnostics,
                 'command':cmd,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'limitations':['Human-approved execution, not OS sandbox','No automatic bibliography/external build steps',
                                'Source/PDF correspondence, not mathematical certification','PDF visual inspection is separate']}
        (output/'build-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return receipt
    except Exception as exc:
        (output/'build-failure.json').write_text(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        raise

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('build');a.add_argument('project',type=Path);a.add_argument('main');a.add_argument('output',type=Path)
    a.add_argument('--engine',choices=['xelatex','pdflatex'],required=True);a.add_argument('--reviewed-input',action='store_true')
    a=s.add_parser('verify');a.add_argument('project',type=Path);a.add_argument('receipt',type=Path);a.add_argument('pdf',type=Path)
    args=p.parse_args()
    try:
        result=build(args.project,args.main,args.output,args.engine,args.reviewed_input) if args.cmd=='build' else verify_receipt(args.project,args.receipt,args.pdf)
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result.get('ok',True) else 1
    except (OSError,ValueError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 2
if __name__=='__main__':sys.exit(main())
