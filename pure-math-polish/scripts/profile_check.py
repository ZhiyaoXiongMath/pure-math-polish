#!/usr/bin/env python3
"""Read-only lexical conformance check against an explicit author profile.
It does not expand TeX, infer mathematics, or replace rendering/manual review.
"""
from __future__ import annotations
import argparse,json,re,sys
from pathlib import Path
from audit_tex_style import audit_text,uncomment

def compact(text:str)->str:
    return re.sub(r'\s+','',text)

def check(profile:dict,text:str)->dict:
    audit=audit_text(text); clean=uncomment(text); errors=[]; warnings=[]
    pre=clean.split('\\begin{document}',1)[0]
    classes=[x for x in audit['class_and_packages'] if x['kind']=='documentclass']
    if len(classes)!=1 or classes[0]['names']!=profile['class']:
        errors.append('Document class differs from selected profile')
    elif not set(profile['class_options']).issubset(set(classes[0]['options'].strip('[]').replace(' ','').split(','))):
        errors.append('Document class options differ')
    packages=set()
    for x in audit['class_and_packages']:
        if x['kind']!='documentclass':packages.update(x['names'].split(','))
    for p in profile['required_packages']:
        if p not in packages:errors.append('Missing selected package: '+p)
    definitions={}
    for d in audit['macros']:
        if d['in_preamble']:definitions[d['name']]=d
    results=[]
    for name,rule in profile['macros'].items():
        d=definitions.get(name)
        same=d is not None and compact(d['definition'])==compact(rule['definition']) and d['options']==rule['options']
        used = bool(re.search(re.escape(name) + (r'(?![A-Za-z@])' if name[-1:].isalpha() else ''), clean.split('\\begin{document}', 1)[-1]))
        required = d is not None or used or name in profile.get('mandatory_macros', [])
        if required and not same:errors.append('Missing/different macro: '+name)
        results.append({'name':name,'matches':same,'required':required,'calls':d['body_occurrences'] if d else 0,
                        'source_line':rule['definition_line'],'source':rule['source']})
    settings=profile['page_settings']; geo=re.search(r'\\geometry\{([^}]*)\}',pre)
    if not geo or compact(geo[1])!=compact(settings['geometry']):errors.append('Page geometry differs')
    for key,value in settings.items():
        if key=='geometry':continue
        if key=='baselinestretch':
            d=definitions.get('\\'+key); ok=d is not None and compact(d['definition'])==compact(value)
        else:
            m=re.search(r'\\setlength\s*\{\\'+key+r'\}\s*\{([^}]*)\}',pre)
            ok=bool(m and compact(m[1])==compact(value))
        if not ok:errors.append('Layout setting differs: '+key)
    for d in audit['macros']:
        if d['name'] in {r'\btheorem',r'\blemma',r'\bproposition',r'\bcorollary'} and any(k in d['definition'] for k in ['samepage','Needspace']):
            errors.append('Blanket pagination wrapper: '+d['name'])
    for name in profile.get('convention_sensitive_macros',[]):
        if name in definitions: warnings.append('Review a convention-sensitive macro not needed by this profile: '+name)
    if 'amssymb' in packages and 'stix2' in packages:warnings.append('amssymb is redundant with stix2; inspect build diagnostics')
    return {'ok':not errors,'profile':profile['name'],'errors':errors,'warnings':warnings,
            'macros':results,'manual_checks':profile['manual_checks'],
            'limits':['Lexical match only; equivalent TeX spellings may differ',
                      'No permission to silently change mismatches','No mathematical certification or render check']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('source',type=Path)
    a=p.parse_args()
    try:
        r=check(json.loads(a.profile.read_text(encoding='utf-8')),a.source.read_text(encoding='utf-8-sig'));print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['ok'] else 1
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)}));return 2
if __name__=='__main__':sys.exit(main())
