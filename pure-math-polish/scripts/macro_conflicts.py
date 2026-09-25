#!/usr/bin/env python3
"""Compare literal preamble definitions. Reports only; never rewrites a manuscript."""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
from audit_tex_style import audit_text,uncomment

def compare(source:str,target:str)->dict:
    def last(text):return {m['name']:m for m in audit_text(text)['macros'] if m['in_preamble']}
    left,right=last(source),last(target);conflicts=[];clean=uncomment(source);split=clean.find('\\begin{document}')
    body=clean[split:] if split>=0 else '';offset=clean[:split].count('\n') if split>=0 else 0
    for name in sorted(set(left)&set(right)):
        a,b=left[name],right[name]
        # Exact (whitespace-normalized) inequality is a review item, not proof of inequivalence.
        if re.sub(r'\s+','',a['definition'])!=re.sub(r'\s+','',b['definition']) or a['options']!=b['options']:
            calls=[offset+body[:m.start()].count('\n')+1 for m in re.finditer(re.escape(name)+(r'(?![A-Za-z@])' if name[-1:].isalpha() else ''),body)]
            conflicts.append({'name':name,'original_definition':a['definition'],'target_definition':b['definition'],
                              'original_line':a['line'],'target_line':b['line'],'call_lines':calls,
                              'review':'unused-declaration: may omit after dependency review' if not calls else 'used: semantic review required'})
    return {'changed_definitions':conflicts,'count':len(conflicts),'rewritten':False,
            'limits':['Lexical differences include equivalent grouping and typography','Dependencies and scopes require human review',
                      'Zero direct calls does not rule out use inside another macro']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('original',type=Path);p.add_argument('template',type=Path);a=p.parse_args()
    try:print(json.dumps(compare(a.original.read_text(encoding='utf-8-sig',errors='replace'),a.template.read_text(encoding='utf-8-sig',errors='replace')),ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError) as exc:print(json.dumps({'error':str(exc)}));return 2
if __name__=='__main__':sys.exit(main())
