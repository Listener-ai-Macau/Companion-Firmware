"""Freeze an exact built screen version on an isolated Git ref, without checkout.

This is a version-management operation, not a product test or installation.
Only explicitly listed files are added or replaced in the checkpoint tree;
other tracked files are inherited from its Git parent.
The regular index, branch, working files and device are not modified.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    manifest_path=args.manifest.resolve()
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    regular_env=os.environ.copy()
    env=regular_env.copy();env['GIT_INDEX_FILE']=str(out/'snapshot.index')
    env['GIT_AUTHOR_NAME']=env['GIT_COMMITTER_NAME']='Codex'
    env['GIT_AUTHOR_EMAIL']=env['GIT_COMMITTER_EMAIL']='codex@local'
    def git(*argv,input=None):
        p=subprocess.run(['git',*argv],cwd=ROOT,env=env,input=input,capture_output=True)
        if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace').strip())
        return p.stdout
    original_head=git('rev-parse','HEAD').decode().strip()
    parent=git('rev-parse','--verify',manifest.get('gitParentRef','HEAD')+'^{commit}').decode().strip()
    index_query=subprocess.run(['git','rev-parse','--git-path','index'],cwd=ROOT,
                               env=regular_env,capture_output=True,check=True)
    regular_index=Path(index_query.stdout.decode().strip())
    if not regular_index.is_absolute():regular_index=ROOT/regular_index
    index_before=regular_index.read_bytes() if regular_index.is_file() else None
    sources={}
    for relative in manifest['buildReceipts']:
        receipt=json.loads((ROOT/relative).read_text(encoding='utf-8'))
        frozen_sources=receipt.get('source_sha256',receipt.get('sources',{}))
        if not isinstance(frozen_sources,dict) or not frozen_sources:
            raise RuntimeError('Build receipt has no frozen source hashes: '+relative)
        for raw_name,expected in frozen_sources.items():
            name=Path(raw_name).as_posix()
            if name in sources and sources[name]!=expected:raise RuntimeError('Conflicting frozen source: '+name)
            sources[name]=expected
    entries={}
    def add(destination,path,expected=None):
        if destination.startswith('/') or '..' in Path(destination).parts:
            raise RuntimeError('Snapshot Git path escapes its tree')
        data=path.read_bytes()
        if expected and hashlib.sha256(data).hexdigest()!=expected:
            raise RuntimeError('Built source/package changed: '+str(path))
        if (path.name=='.env' or path.name in ('before-internal.bin','after-internal.bin') or
                data.lstrip().startswith((b'-----BEGIN PRIVATE KEY-----',
                b'-----BEGIN EC PRIVATE KEY-----',b'-----BEGIN RSA PRIVATE KEY-----'))):
            raise RuntimeError('Private/NVM material is outside the snapshot scope')
        if destination in entries and entries[destination]!=(path,data):
            raise RuntimeError('Snapshot path conflict: '+destination)
        entries[destination]=(path,data)
    for name,expected in sources.items():add(Path(name).as_posix(),ROOT/name,expected)
    for item in manifest['snapshotFiles']:
        add(item['gitPath'],(ROOT/item['path']).resolve(),item.get('sha256'))
    add(manifest_path.relative_to(ROOT).as_posix(),manifest_path)
    git('read-tree',parent)
    # Replace only gitlinks intersecting the compiled source tree in this
    # temporary index. Real submodule checkouts and the regular index stay put.
    for row in git('ls-tree','-rz',parent).split(b'\0'):
        if not row:continue
        mode,_,tail=row.split(b' ',2);_,name=tail.split(b'\t',1)
        prefix=name.decode('utf-8')
        if mode==b'160000' and any(p.startswith(prefix+'/') for p in entries):
            git('update-index','--force-remove',prefix)
    paths=list(entries)
    # Hash exactly the bytes checked above, even if shared working files change.
    blobs=out/'frozen-blobs';blobs.mkdir()
    object_paths=[]
    for _,data in entries.values():
        blob=blobs/hashlib.sha256(data).hexdigest()
        if not blob.exists():blob.write_bytes(data)
        object_paths.append(blob)
    input_paths=''.join(json.dumps(p.as_posix(),ensure_ascii=True)+'\n' for p in object_paths).encode('ascii')
    object_ids=git('hash-object','-w','--no-filters','--stdin-paths',input=input_paths).decode().splitlines()
    if len(object_ids)!=len(paths):raise RuntimeError('Git blob count differs')
    index_data=b''.join(('100644 '+oid+'\t'+name+'\0').encode('utf-8') for oid,name in zip(object_ids,paths))
    git('update-index','-z','--index-info',input=index_data)
    tree=git('write-tree').decode().strip()
    message=manifest.get('gitMessage',
             f'Freeze {manifest["firmware"]}/UI{manifest["uiGeneration"]} screen failure and source\n\n'
             'Installed image verified; physical refresh remains unresolved.\n'
             'Preserve accepted UI67 art and original failure evidence.\n').encode('utf-8')
    commit=git('commit-tree',tree,'-p',parent,input=message).decode().strip()
    # Creation only: an existing checkpoint must never be silently replaced.
    index_after=regular_index.read_bytes() if regular_index.is_file() else None
    if original_head!=git('rev-parse','HEAD').decode().strip() or index_before!=index_after:
        raise RuntimeError('Regular Git HEAD/index changed during checkpoint; inspect concurrent work')
    refs=('start\ncreate '+manifest['gitBranchRef']+' '+commit+'\ncreate '+
          manifest['gitTagRef']+' '+commit+'\nprepare\ncommit\n').encode('utf-8')
    git('update-ref','--stdin',input=refs)
    result={'result':'GIT_SCREEN_CHECKPOINT_CREATED','createdAtLocal':datetime.now().isoformat(),
            'commit':commit,'tree':tree,'parent':parent,'branch':manifest['gitBranchRef'],
            'tag':manifest['gitTagRef'],'compiledSourceFiles':len(sources),'frozenFiles':len(entries),
            'regularHeadAndIndexUnchanged':True,'boardAccess':False,'testsRun':False,
            'screenFixed':False,'sourceManifest':str(manifest_path)}
    (out/'checkpoint.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
