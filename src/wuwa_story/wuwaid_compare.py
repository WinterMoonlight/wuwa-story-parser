"""Run the reviewed WuwaID per-task extraction on the same read-only ConfigDB."""
# Per-task loop adapted from TitoTFP/WuwaID, Copyright (c) 2026 Tito Fauzan Putra.
# MIT license: docs/third-party/WuwaID-LICENSE.txt. Upstream parsing is imported unchanged.
import hashlib, importlib.util, json, os, sqlite3, sys, types, argparse
from pathlib import Path
from collections import defaultdict
from wuwa_story.paths import DATABASE_DIR, OUTPUT_DIR, WORK_DIR
from wuwa_story.recap_backbone import export_task_backbone
from wuwa_story.export_task import write_result


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--quest-id',type=int,required=True)
    parser.add_argument('--reference',type=Path,default=WORK_DIR/'reference.py')
    parser.add_argument('--output',type=Path,default=OUTPUT_DIR/'WuwaID对照')
    args=parser.parse_args()
    qid=args.quest_id
    out=args.output/str(qid)
    out.mkdir(parents=True,exist_ok=True)
    path=args.reference.resolve()
    source=path.read_bytes().replace(b'\r\n',b'\n')
    expected='617f129f3b008775f1576aee0506341a618f69e66dda17a6990bde05c86f4ef5'
    if hashlib.sha256(source).hexdigest()!=expected:
        raise ValueError('Unreviewed WuwaID source revision; review and update the pinned hash first')
    spec=importlib.util.spec_from_file_location('wuwaid_reference',path)
    ref=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ref;spec.loader.exec_module(ref)
    # Only replace base-directory layout and DB open mode. Extraction code stays unchanged.
    opened=set()
    def mapped(path):
        p=Path(path)
        try:
            rel=p.relative_to(DATABASE_DIR)
        except ValueError:
            raise ValueError('Unexpected reference DB path: '+str(p))
        if rel.parts[0]=='base':rel=Path(*rel.parts[1:])
        return DATABASE_DIR/rel
    def connect(path):
        p=mapped(path);opened.add(p)
        return sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
    ref.os=types.SimpleNamespace(path=types.SimpleNamespace(join=os.path.join,isfile=lambda p:mapped(p).is_file()))
    ref.sqlite3=types.SimpleNamespace(connect=connect)
    ref.CONFIG_DB_DIR=str(DATABASE_DIR)
    qdb=connect(DATABASE_DIR/'db_QuestNodeData.db')
    fdb=connect(DATABASE_DIR/'db_flowState.db')
    pairs=ref.get_quest_flows(qid,qdb.cursor())
    index=defaultdict(list); ids=defaultdict(set)
    for key,blob in fdb.execute('SELECT StateKey,BinData FROM flowstate ORDER BY StateKey'):
        parsed=ref.parse_flowstate_key(key)
        if parsed:
            name,fid,sid=parsed;index[name,fid].append((key,sid,blob));ids[name].add(fid)
    expanded=ref._expand_to_all_flowids(pairs,ids)
    packs=[ref.LangPack('zh-Hans')]
    all_lines=[];flows=[]
    for pair in expanded:
        lines=[];states=[]
        for key,_,blob in sorted(index[pair],key=lambda x:(x[1],x[0])):
            extracted,mode,actions=ref.extract_dialogue_from_flowstate(key,blob,packs)
            lines.extend(extracted);states.append({'state_key':key,'plot_mode':mode,'actions':actions})
        if lines:flows.append({'pair':pair,'states':states,'dialogue':lines})
        all_lines.extend(lines)
    ref.renumber_lines_globally(all_lines)
    ours=export_task_backbone(qid);write_result(ours,out,quiet=True)
    def dump(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    dump('wuwaid.json',{'quest_id':qid,'base_pairs':pairs,'expanded_pairs':expanded,'flows':flows,'all_lines':all_lines})
    source=path.read_bytes().replace(b'\r\n',b'\n')
    dump('manifest.json',{'quest_id':qid,'source_url':'https://github.com/TitoTFP/WuwaID/blob/main/scripts/export_quest_ordered.py','git_blob_sha1':hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest(),'sha256':hashlib.sha256(source).hexdigest(),'adapter':'same files; base/ layout remapped; sqlite mode=ro; zh-Hans only; original extraction functions and main per-task loop; no chapter/main cleanup','files':{str(p.relative_to(DATABASE_DIR)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(opened)}})
    qdb.close();fdb.close()
    from .extractor_comparison import compare_extractions
    dump('comparison.json',compare_extractions(ours, {'all_lines':all_lines}))
    print(json.dumps({'pairs':len(pairs),'expanded':len(expanded),'states':sum(len(f['states']) for f in flows),'lines':len(all_lines),'option_lines':sum(len(x.get('options',[])) for x in all_lines),'ours_records':len(ours['batch_coverage']['records']),'ours_segments':len(ours['recap_backbone']['segments']),'out':str(out)},ensure_ascii=False))

if __name__ == "__main__":
    main()
