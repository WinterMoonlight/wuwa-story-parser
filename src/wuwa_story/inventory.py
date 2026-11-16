from .database import *

chap=[]
for r in rows('db_QuestTree.db','questtreechapter'):
 b=r['BinData'];chap.append({'id':r['Id'],'decoded_id':integer(b,0),'key':string(b,1),'name':resolve(string(b,1))})
nodes=[]
for r in rows('db_QuestTree.db','questtreenode'):
 b=r['BinData'];nodes.append({'id':r['Id'],'decoded_id':integer(b,0),'chapter':r['ChapterId'],'quests':vec(b,2),'pre':vec(b,9),'next':integer(b,10)})
quests={r['QuestId']:embedded(r['BinData']) for r in rows('db_QuestData.db','questdata')}
qn={r['Key']:embedded(r['BinData']) for r in rows('db_QuestNodeData.db','questnodedata')}
fs={r['StateKey']:embedded(r['BinData']) for r in rows('db_flowState.db','flowstate')}
print('CHAPTERS',chap);print('NODES',nodes[:3]);print('QUEST SAMPLE',list(quests.items())[:2]);print('NODE SAMPLE',list(qn.items())[:2]);print('FLOW SAMPLE',str(list(fs.items())[:1])[:5000])
print('PARSE', {k:[len(d),sum(bool(v) for v in d.values())] for k,d in [('quests',quests),('nodes',qn),('states',fs)]})
# inventory all SQLite files, without dumping full text
inventory=[]
for p in sorted(P.rglob('*.db')):
 c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)
 try:
  ts=[]
  for t, in c.execute("select name from sqlite_master where type='table'"):
   q='"'+t.replace('"','""')+'"';ts.append({'table':t,'rows':c.execute('select count(*) from '+q).fetchone()[0],'columns':[r[1] for r in c.execute('pragma table_info('+q+')')]})
  inventory.append({'file':str(p.relative_to(P)),'bytes':p.stat().st_size,'tables':ts})
 except Exception as e:inventory.append({'file':str(p.relative_to(P)),'error':str(e)})
 finally:c.close()
(O/'数据库目录清单.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
(WORK_DIR / 'parsed.json').write_text(json.dumps({'chapters':chap,'tree':nodes,'quests':quests,'nodes':qn,'states':fs},ensure_ascii=False),encoding='utf-8')
print('INVENTORY',len(inventory),'errors',sum('error'in x for x in inventory))
