import pathlib,sqlite3,json,sys
if hasattr(sys.stdout, 'reconfigure'):
 sys.stdout.reconfigure(encoding='utf-8')
from .paths import DATABASE_DIR
p = DATABASE_DIR
for n in ['db_QuestTree.db','db_QuestData.db','db_QuestNodeData.db','db_flow.db','db_flowState.db','db_speaker.db','db_PlotHandBook.db','db_questtype.db']:
 c=sqlite3.connect((p/n).as_uri()+'?mode=ro',uri=True)
 print('\n',n)
 for t,sql in c.execute("select name,sql from sqlite_master where type='table'"):
  q='"'+t+'"';print(sql,'COUNT',c.execute('select count(*) from '+q).fetchone()[0])
  row=c.execute('select * from '+q+' limit 1').fetchone()
  print(str([(v[:1800] if isinstance(v,str) else ('BYTES '+str(len(v))+' '+v[:50].hex() if isinstance(v,bytes) else v)) for v in row])[:3000] if row else '')
