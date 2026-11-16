from .paths import WORK_DIR
from .database import *
from .speakers import SpeakerResolver
d=json.loads((WORK_DIR / 'parsed.json').read_text(encoding='utf-8'))
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values():yield from walk(v)
 elif isinstance(o,list):
  for v in o:yield from walk(v)
types={r['Id']:resolve(string(r['BinData'],2)) for r in rows('db_questtype.db','questtype')}
sp=dict((r['Id'],r['Content']) for r in rows('zh-Hans/lang_speaker.db','Speaker'))
speaker_resolver = SpeakerResolver()
speakers = {sid: info['name'] for sid, info in speaker_resolver.records.items()}
print('SPEAKERS',[(i,speakers.get(i)) for i in [873,875]])
print('TYPES',types)
node_index=collections.defaultdict(list)
for k,v in d['nodes'].items():node_index[k.split('_')[0]].append((k,v))
quest_index=[]; ref_total=ref_found=0
for qid,entries in d['quests'].items():
 q=entries[0][1];refs=[]
 for source,obj in [('QuestData',entries)]+node_index[qid]:
  for r in walk(obj):
   if 'FlowListName' in r and 'FlowId' in r:
    state=r.get('StateId');prefix=f"{r['FlowListName']}_{r['FlowId']}"
    sk=prefix+'_'+str(state) if state is not None else None
    exists=sk in d['states'] if sk else any(k.startswith(prefix+'_') for k in d['states'])
    refs.append({'source':source,'flow':r['FlowListName'],'flow_id':r['FlowId'],'state_id':state,'state_key':sk,'found':exists})
    ref_total+=1;ref_found+=exists
 quest_index.append({'quest_id':int(qid),'name':resolve(q.get('TidName','')),'internal_name':q.get('Key'),'type_id':q.get('Type'),'type_name':types.get(q.get('Type')),'task_node_count':len(node_index[qid]),'flow_references':refs})
lookup={q['quest_id']:q for q in quest_index}
for n in d['tree']:n['quest_names']=[lookup.get(i,{}).get('name','未找到任务') for i in n['quests']]
result={'note':'配置索引，不是完整剧情播放顺序。前后节点和分支保留；不把数字排序当作游戏执行顺序。','chapters':d['chapters'],'chapter_nodes':d['tree'],'quest_types':types,'quests':quest_index}
(O/'章节任务与流程索引.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
keys=[];missing=[]
for sk,v in d['states'].items():
 for obj in walk(v):
  for key in ['TidTalk','TidTalkOption']:
   if obj.get(key):
    keys.append(obj[key])
    if obj[key] not in texts:missing.append((sk,obj[key]))
print('REFS',ref_found,ref_total,'TEXT_REFS',len(keys),'UNIQUE',len(set(keys)),'MISSING',len(missing),len(set(k for s,k in missing)))
lines=['鸣潮 ConfigDB 阅读索引','来源：'+str(P),'原数据库只读检查，未修改。','','章节树记录（不代表全部均为已开放的正式章节）：']
for c in d['chapters']:
 lines.append(f"\n[{c['id']}] {c['name']} ({c['key']})")
 for n in d['tree']:
  if n['chapter']==c['id']:lines.append(f"  节点 {n['id']} | 任务 {list(zip(n['quests'],n['quest_names']))} | 前置 {n['pre']} | 后继 {n['next']}")
lines+=['','任务类型：']+[f'{k}: {v}' for k,v in types.items()]
lines+=['','验证示例：','章节树 1 → 节点 110000 → QuestId 139000025 → 万象新声·上','任务节点 139000025_19 → 剧情_新主线_CE版_序章 / FlowId 1 / StateId 1','流程状态键：剧情_新主线_CE版_序章_1_1']
for obj in walk(d['states']['剧情_新主线_CE版_序章_1_1']):
 if obj.get('TidTalk'):
  lines.append(f"  WhoId={obj.get('WhoId')} {speakers.get(obj.get('WhoId'),'未解析')} | {obj['TidTalk']} | {resolve(obj['TidTalk'])}")
  if sum('WhoId=' in l for l in lines)>=3:break
lines+=['','结构说明：','QuestTree：章节树和任务入口。QuestData：任务定义。QuestNodeData：任务节点、条件、触发动作。','flow：流程目录。flowState：动作、对白、选项和跳转。','TidTalk/TidTalkOption → 中文 MultiText.Id。WhoId → speaker.Id → NameStringKey → 中文 Speaker.Id → 必要时再查 MultiText。','RedirectDbIndex=1 的2148条正文由 multi_text_1sthalf 按相同ID补回。','BinData 是二进制结构；任务、节点、流程动作的JSON嵌在其中。','不要按文本ID或节点数字直接拼接；需解析 Sequence、条件、JumpTalk、状态切换等。','本索引未证明游戏中全部剧情覆盖，配置中存在测试、隐藏、占位和未必可达的记录。',f'任务/节点/状态的内嵌JSON成功读取：1930/1930、27161/27161、21971/21971。',f'任务及其节点中显式流程引用可匹配：{ref_found}/{ref_total}（重复引用计入；缺失不必然代表资源遗漏）。',f'流程中非空对白/选项文本引用：{len(keys)}次，{len(set(keys))}个不同ID；缺少{len(set(k for s,k in missing))}个不同ID。','索引JSON保留原始关联，未生成完整阅读版剧本。']
(O/'章节目录与关联说明.txt').write_text('\n'.join(lines),encoding='utf-8-sig')
(O/'未匹配文本引用.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2),encoding='utf-8')
