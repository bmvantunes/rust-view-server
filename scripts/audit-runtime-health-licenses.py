"""Audit every resolved package/edge, all target platforms and Kafka TLS feature."""
from pathlib import Path
import subprocess,json,re,hashlib,shutil
root=Path(__file__).resolve().parent.parent
m=json.loads(subprocess.check_output(['cargo','metadata','--locked','--offline','--all-features','--format-version','1','--manifest-path',str(root/'ingestion/Cargo.toml')]))
allowed={'MIT','MIT-0','Apache-2.0','BSD-2-Clause','BSD-3-Clause','ISC','Unicode-3.0','Zlib','CDLA-Permissive-2.0'}
def select(expression):
    tokens=re.findall(r'\(|\)|[^\s()]+',expression.replace('/',' OR '));i=0
    def atom():
        nonlocal i
        t=tokens[i];i+=1
        if t=='(':
            value=expr();assert tokens[i]==')';i+=1;return value
        if i<len(tokens) and tokens[i]=='WITH':i+=2;return None
        return [t] if t in allowed else None
    def conjunction():
        nonlocal i
        left=atom()
        while i<len(tokens) and tokens[i]=='AND':
            i+=1;right=atom();left=left+right if left is not None and right is not None else None
        return left
    def expr():
        nonlocal i
        left=conjunction()
        while i<len(tokens) and tokens[i]=='OR':
            i+=1;right=conjunction();left=left if left is not None else right
        return left
    result=expr();assert i==len(tokens);return result
out=root/'evidence/runtime-health/licenses';out.mkdir(parents=True,exist_ok=True)
packages=[]
for p in sorted(m['packages'],key=lambda p:(p['name'],p['version'])):
    local=p['source'] is None
    selected=['local unpublished project'] if local else select(p['license'] or '')
    assert selected is not None,(p['name'],p['license'])
    package={'name':p['name'],'version':p['version'],'id':p['id'],'expression':p['license'],'selected':sorted(set(selected)),'license_files':[]}
    base=Path(p['manifest_path']).parent
    files=[] if local else [f for f in base.iterdir() if f.is_file() and f.name.upper().startswith(('LICENSE','COPYING','NOTICE'))]
    if p['name'] in ['aws-lc-sys','rdkafka-sys','libsqlite3-sys']:
        files += [f for f in base.rglob('*') if f.is_file() and f.name.upper().startswith(('LICENSE','COPYING','NOTICE'))]
    for f in sorted(set(files)):
        destination=out/(p['name']+'-'+p['version'])/f.relative_to(base)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,destination)
        package['license_files'].append({'path':str(destination.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    if p['name']=='libsqlite3-sys':
        source=base/'sqlite3/sqlite3.c'
        content=source.read_text()
        start=content.index('/*\n** 2001-09-15')
        end=content.index('*/',start)+2
        destination=out/'libsqlite3-sys-0.38.2/SQLITE-PUBLIC-DOMAIN-NOTICE.txt'
        destination.write_text(content[start:end]+'\n')
        package['license_files'].append({'path':str(destination.relative_to(root)),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()})
    if not local and not files:
        package['notice_limitation']='Published crate declares an admitted license but includes no standalone license file; preserve Cargo metadata, do not invent a copyright holder.'
        destination=out/(p['name']+'-'+p['version'])/'Cargo.toml'
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p['manifest_path'],destination)
    packages.append(package)
openssl=Path('/opt/homebrew/opt/openssl@3/LICENSE.txt')
if openssl.exists():shutil.copy2(openssl,out/'system-openssl-LICENSE.txt')
summary={'policy':'Permissive license branches; preserve all mandatory AND notices. No selected GPL/LGPL/AGPL branch. Baseline MIT/Apache/Unicode practice extended to permissive ISC/BSD/CDLA native and root-certificate terms.','approved_permissive_set':sorted(allowed),'packages':packages,'dependency_graph':m['resolve']['nodes'],'native_components':{'SQLite':'3.53.2 bundled amalgamation; public-domain disclaimer copied from exact sqlite3.c; libsqlite3-sys wrapper MIT. SQLCipher is not enabled.', 'librdkafka':'2.12.1 bundled C/C++ (BSD-2-Clause and bundled notices copied)','aws-lc':'bundled crypto, full composite license selected; copied upstream LICENSE and notices','OpenSSL':'kafka-tls dynamically links system OpenSSL 3 (Apache-2.0); local license copied; deployment must package its own matching notices'}}
(root/'evidence/runtime-health/licenses.json').write_text(json.dumps(summary,indent=2)+'\n')
print(f'PASS {len(packages)} packages, all resolved dependency edges, native license notices; no disallowed selected branch')
