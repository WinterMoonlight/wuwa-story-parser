"""Consensus suffix of a unique recap call across exclusive task branches."""
from .export_task import flow_key, walk, flow_actions, Exporter
from .rendering import render_result
from .dependency_positions import _sync_flow


def _complement(a, b):
    def atom(c):
        if not isinstance(c, dict) or set(c) != {'Type', 'Conditions'} or c['Type'] != 0 or not isinstance(c['Conditions'], list) or len(c['Conditions']) != 1 or not isinstance(c['Conditions'][0], dict):
            return None
        return c['Conditions'][0]
    a, b = atom(a), atom(b)
    if not a or not b:
        return False
    if a.get('Type') == b.get('Type') == 'CompareVar':
        return (set(a) == set(b) == {'Type', 'Var1', 'Compare', 'Var2'}
                and all(isinstance(v, dict) for v in (a['Var1'], b['Var1'], a['Var2'], b['Var2']))
                and a['Compare'] == b['Compare'] == 'Eq' and a['Var1'] == b['Var1']
                and a['Var1'].get('Type') == 'Boolean'
                and set(a['Var1']) == {'Type','Source','Keyword'}
                and a['Var1']['Source'] == 'Global' and isinstance(a['Var1']['Keyword'],str) and bool(a['Var1']['Keyword'])
                and set(a['Var2']) == set(b['Var2']) == {'Type', 'Source', 'Value'}
                and a['Var2']['Type'] == b['Var2']['Type'] == 'Boolean'
                and a['Var2']['Source'] == b['Var2']['Source'] == 'Constant'
                and type(a['Var2']['Value']) is bool and type(b['Var2']['Value']) is bool
                and a['Var2']['Value'] != b['Var2']['Value'])
    return (a.get('Type') == b.get('Type') == 'CheckChildQuestFinished'
            and set(a) == set(b) == {'Type', 'QuestId', 'ChildQuestId', 'Compare'}
            and {a['Compare'], b['Compare']} == {'Eq', 'Ne'}
            and a['QuestId'] == b['QuestId'] and a['ChildQuestId'] == b['ChildQuestId'])


def consensus_proof(quest, nodes, anchor, extra):
    """Prove local A->B for every explicit A/B call, not actual task execution."""
    by = {n['Id']: n for n in nodes}
    if len(by) != len(nodes) or anchor == extra:
        return None
    owners = set()
    invalid = False
    def visit(value, owner=None, path=()):
        nonlocal invalid
        if isinstance(value, dict):
            if value.get('Type') in ('ChildQuest', 'Sequence', 'ConditionSelector') and 'Id' in value:
                canonical = by.get(value['Id'])
                ignored = {'ParentNodeId'} | ({'Children'} if value['Type']=='Sequence' else set())
                if canonical is None or {k:v for k,v in value.items() if k not in ignored} != {k:v for k,v in canonical.items() if k not in ignored}:
                    invalid = True
                if value['Type']=='Sequence' and 'Children' in value:
                    children=value['Children']
                    expected={n['Id'] for n in nodes if n.get('ParentNodeId')==value['Id']}
                    if (not isinstance(children,list) or any(not isinstance(c,dict) for c in children)
                            or {c.get('Id') for c in children} != expected or len(children)!=len(expected)):
                        invalid=True
                if value['Type'] == 'ChildQuest':
                    owner, path = value['Id'], ()
            if value.get('FlowListName') and 'FlowId' in value and 'StateId' in value and flow_key(value) in {anchor, extra}:
                expected = 0 if flow_key(value) == anchor else 1
                if owner is None or path != ('FinishActions', expected, 'Params'):
                    invalid = True
                else:
                    owners.add(owner)
            for k,v in value.items(): visit(v,owner,path+(k,))
        elif isinstance(value,list):
            for i,v in enumerate(value):visit(v,owner,path+(i,))
    visit([quest,nodes])
    if invalid or len(owners) < 2:
        return None
    branches = {}
    for owner in owners:
        n=by[owner]; actions=n.get('FinishActions',[])
        if (n.get('Type') != 'ChildQuest' or n.get('EnterActions') or n.get('FailedCondition') or n.get('ExitCondition')
                or set(n) - {'Type','Id','Desc','ParentNodeId','TrackTarget','EnterActions','FinishActions','RewardId','Condition','TidTip'}
                or len(actions)!=2 or [_sync_flow(a) for a in actions] != [anchor,extra]):
            return None
        seen={owner}; current=n; selected={}
        while current.get('ParentNodeId') in by:
            parent=by[current['ParentNodeId']]
            if parent['Id'] in seen or parent.get('Type') not in {'Sequence','ConditionSelector'}:
                return None
            allowed = {'Type','Id','Desc','ParentNodeId','Children','OccupationConfig'} if parent['Type']=='Sequence' else {'Type','Id','Desc','ParentNodeId','Slots'}
            if set(parent) - allowed:
                return None
            seen.add(parent['Id'])
            if parent.get('Type')=='ConditionSelector':
                slots=parent.get('Slots',[])
                if (not isinstance(slots,list) or len(slots)!=2
                        or any(not isinstance(s,dict) or set(s)!={'Condition','Node'} for s in slots)
                        or not _complement(slots[0].get('Condition'),slots[1].get('Condition'))):
                    return None
                choices=[i for i,s in enumerate(slots) if s.get('Node',{}).get('Id')==current['Id']]
                if len(choices)!=1:return None
                selected[parent['Id']]=choices[0]
            current=parent
        if current.get('ParentNodeId') not in (None,0):return None
        branches[owner]=selected
    for a in owners:
        for b in owners:
            if a<b and not any(k in branches[b] and branches[a][k]!=branches[b][k] for k in branches[a]):
                return None
    return {'basis':'all explicit call sites share adjacent synchronous suffix in exclusive selector branches',
            'after_state':anchor,'state_key':extra,'owner_node_ids':sorted(owners),'selector_branches':branches,
            'source_actions':[{'node_id':i,'actions':by[i]['FinishActions']} for i in sorted(owners)],
            'runtime_verified':False,'task_completion_verified':False,'scope':'local suffix of the unique recap occurrence; not a runtime schedule'}


def insert_consensus_suffix(review, quest, nodes, backbone, states, source):
    extra=review['state_key']
    if extra not in states:return
    for target in backbone['segments']:
        anchor=target['state_key']
        if target['status']!='parsed' or sum(s['state_key']==anchor for s in backbone['segments'])!=1:
            continue
        proof=consensus_proof(quest,nodes,anchor,extra)
        if proof is None:continue
        try:
            actions,fields=flow_actions(states[extra]['BinData'])
            # Narrow to dialogue-only leaves; control/actions/condition changes are excluded.
            if any(a.get('Name') not in {'SetPlotMode','ShowTalk'} for a in actions):return
            if any(o.get('Actions') or o.get('PreCondition') or o.get('Type') in {'Jump','QTE','JumpTalk'} for o in walk(actions)):return
            parser=Exporter(source=source,allow_incomplete=True);parser.state_key=extra
            if parser.actions(actions) or parser.missing or parser.unverified_content or getattr(parser,'unordered_attachments',[]):return
            rendered=render_result({'title':'','route':{'choices':parser.decisions},'events':parser.events})
        except (ValueError,KeyError,TypeError,IndexError):return
        visible=[e for e in rendered['events'] if e.get('text','').strip()]
        if not visible:return
        for event in visible:event['task_placement']=proof
        target['events'].extend(visible)
        target.setdefault('inserted_task_flows',[]).append({'state_key':extra,'proof':proof,'source_actions':actions,'action_fields':fields,'route':rendered['route']})
        review.update(classification='placed_consensus_suffix',placement_verified=True,proof=proof,text_evidence=rendered['events'],visible_event_count=len(visible))
        return
