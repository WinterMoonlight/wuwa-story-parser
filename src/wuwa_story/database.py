import pathlib,sqlite3,json,struct,collections,sys
if hasattr(sys.stdout, 'reconfigure'):
 sys.stdout.reconfigure(encoding='utf-8')
from .paths import DATABASE_DIR, WORK_DIR, OUTPUT_DIR
P = DATABASE_DIR
O = OUTPUT_DIR
O.mkdir(exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)
def rows(n,t):
 c=sqlite3.connect((P/n).as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 try:return [dict(r) for r in c.execute('select * from "'+t+'"')]
 finally:c.close()
def field(b,i):
 r=struct.unpack_from('<I',b)[0];v=r-struct.unpack_from('<i',b,r)[0];size=struct.unpack_from('<H',b,v)[0]
 off=struct.unpack_from('<H',b,v+4+2*i)[0] if 4+2*i<size else 0
 return r+off if off else None
def integer(b,i):
 p=field(b,i);return struct.unpack_from('<i',b,p)[0] if p else 0
def string(b,i):
 p=field(b,i)
 if p is None:return ''
 q=p+struct.unpack_from('<I',b,p)[0];n=struct.unpack_from('<I',b,q)[0]
 if q+4+n>len(b):raise ValueError()
 return b[q+4:q+4+n].decode('utf-8')
def vec(b,i):
 p=field(b,i)
 if p is None:return []
 q=p+struct.unpack_from('<I',b,p)[0];n=struct.unpack_from('<I',b,q)[0]
 if n>10000 or q+4+4*n>len(b):raise ValueError()
 return list(struct.unpack_from('<'+'i'*n,b,q+4))
def embedded(b):
 result=[]
 r=struct.unpack_from('<I',b)[0];v=r-struct.unpack_from('<i',b,r)[0];size=struct.unpack_from('<H',b,v)[0]
 for i in range((size-4)//2):
  try:
   s=string(b,i)
   if s.startswith(('{','[')):result.append((i,json.loads(s)))
  except (ValueError,UnicodeError,struct.error):pass
 return result
texts={r['Id']:r['Content'] for r in rows('zh-Hans/lang_multi_text.db','MultiText')}
for r in rows('zh-Hans/lang_multi_text_1sthalf.db','MultiText'):texts[r['Id']]=r['Content']
def resolve(k):return texts.get(k,k)
