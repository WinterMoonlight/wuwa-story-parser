"""Place completed-message reading at a unique recap tip, never at send time."""
from copy import deepcopy
from .database import texts
from .rendering import render_text


def _send(action):
    if not isinstance(action, dict) or set(action) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'} or action.get('Async', False) is not False:
        return None
    p = action.get('Params', {})
    if action.get('Name') != 'PhoneSystemInteract' or not isinstance(p, dict) or set(p) != {'InteractType'}:
        return None
    interaction = p['InteractType']
    if not isinstance(interaction, dict) or set(interaction) != {'Type', 'PhoneRecordActionConfig'} or interaction['Type'] != 'SendPhoneMessage':
        return None
    config = interaction['PhoneRecordActionConfig']
    if not isinstance(config, dict) or set(config) != {'PhoneMessageId'}:
        return None
    value = config['PhoneMessageId']
    return value if type(value) is int and value > 0 else None


def _effect(action):
    if not isinstance(action, dict) or set(action) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'} or action.get('Async', False) is not False:
        return False
    p = action.get('Params'); name = action.get('Name')
    if not isinstance(p, dict):
        return False
    if name == 'SetAudioState' and set(p) == {'AudioConfig'}:
        c = p['AudioConfig']
        return isinstance(c, dict) and set(c) == {'Group', 'State'} and all(isinstance(v, str) and v for v in c.values())
    if name == 'GetItem' and set(p) == {'Items'} and isinstance(p['Items'], list):
        return all(isinstance(i, dict) and set(i) == {'ItemId', 'Count'} and all(type(v) is int and v > 0 for v in i.values()) for i in p['Items'])
    return name == 'ShowHidedGroup' and set(p) == {'GroupKey', 'DelayShow'} and isinstance(p['GroupKey'], str) and bool(p['GroupKey']) and type(p['DelayShow']) is bool


def _walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values():
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)


def phone_tip_insertions(nodes, backbone, external_content, source=None):
    if not backbone or not isinstance(nodes, list):
        return []
    entries = backbone.get('order_source', {}).get('entries', [])
    by = {n['Id']: n for n in nodes}
    if len(by) != len(nodes):
        return []
    out = []
    for node in nodes:
        if (node.get('Type') != 'ChildQuest'
                or set(node) - {'Type','Id','Desc','Condition','TidTip','TrackTarget','EnterActions','FinishActions','TrackCustomBoard','ParentNodeId'}):
            continue
        condition = node.get('Condition', {})
        if (not isinstance(condition, dict) or set(condition) != {'Type','PhoneMessageId','ProgressType'}
                or condition['Type'] != 'ReadPhoneMessage' or condition['ProgressType'] != {'Type':'CompleteMessage'}):
            continue
        mid = condition['PhoneMessageId']; tip = node.get('TidTip')
        if type(mid) is not int or mid <= 0 or not isinstance(tip, str) or not tip:
            continue
        if node.get('TrackCustomBoard') != {'TrackPhoneMessageBoard': {'PhoneMessageId':mid}}:
            continue
        if sum(n.get('TidTip') == tip for n in nodes) != 1:
            continue
        tips = [(i,e) for i,e in enumerate(entries) if e.get('TidTip') == tip]
        if (len(tips) != 1 or tips[0][1].get('Flow') != {'FlowListName':'','FlowId':0,'StateId':0}
                or set(tips[0][1]) - {'TidTip','Flow','IsHideUi'} or tips[0][1].get('IsHideUi',False) is not False):
            continue
        enter, finish = node.get('EnterActions', []), node.get('FinishActions', [])
        if not isinstance(enter,list) or not isinstance(finish,list):
            continue
        sends = [(i,a) for i,a in enumerate(enter) if _send(a) == mid]
        mentioned_sends = [a for a in _walk(nodes) if a.get('Name') == 'PhoneSystemInteract'
                           and isinstance(a.get('Params'),dict)
                           and isinstance(a['Params'].get('InteractType'),dict)
                           and a['Params']['InteractType'].get('Type') == 'SendPhoneMessage'
                           and isinstance(a['Params']['InteractType'].get('PhoneRecordActionConfig'),dict)
                           and a['Params']['InteractType']['PhoneRecordActionConfig'].get('PhoneMessageId') == mid]
        if len(sends) != 1 or len(mentioned_sends) != 1:
            continue
        surrounding=[]; context_safe=True
        for phase, actions in (('EnterActions',enter),('FinishActions',finish)):
            for index, effect in enumerate(actions):
                if (phase=='EnterActions' and _send(effect)==mid) or _effect(effect):
                    continue
                from .phone_world_context import context_effect
                evidence=context_effect(effect,phase,source)
                if evidence is None:
                    context_safe=False;break
                surrounding.append({'phase':phase,'action_index':index,'evidence':evidence})
            if not context_safe:break
        if not context_safe:
            continue
        chain=[]; current=node; seen={node['Id']}; safe=True
        while current.get('ParentNodeId') in by:
            current=by[current['ParentNodeId']]
            if (current['Id'] in seen or current.get('Type') != 'Sequence'
                    or set(current) - {'Type','Id','Desc','ParentNodeId'}):
                safe=False;break
            seen.add(current['Id']);chain.append(current['Id'])
        if not safe or not chain or current.get('ParentNodeId') != 0:
            continue
        matches=[(i,e) for i,e in enumerate(external_content) if e.get('phone',{}).get('message_id')==mid]
        if len(matches) != 1:
            continue
        ei,entry=matches[0]; ai,action=sends[0]; phone=entry['phone']
        if (entry.get('node_id') != node['Id'] or entry.get('phase') != 'EnterActions'
                or entry.get('source_action') != action
                or entry.get('original_action_index',entry.get('action_index')) != ai
                or phone.get('missing_text_ids') or not phone.get('events')
                or any(s['state_key']==phone.get('state_key') for s in backbone.get('segments',[]))):
            continue
        proof={'basis':'same-node send and complete-message condition, unique recap tip',
               'node_id':node['Id'],'source_condition':condition,'source_send_action':action,
               'ancestor_sequence_ids':chain,'source_node':node,'recap_entry':tips[0][1],
               'runtime_verified':False,'read_completion_verified':False,
               'surrounding_action_evidence':surrounding,
               'post_read_world_effects_simulated':False,
               'scope':'configured reading step at recap tip; not send-time or global runtime order'}
        out.append({'entry_index':tips[0][0],'tid_tip':tip,'title':render_text(texts.get(tip,'')),
                    'events':deepcopy(phone['events']),'phone_message_id':mid,'message_id':mid,'phone':phone,
                    'proof':proof,'external_index':ei,'order_scope':'recap_tip_reading_step'})
    return sorted(out,key=lambda x:x['entry_index'])


def phone_tip_diagnostics(nodes, backbone, external_content, insertions):
    """Explain retained phone material; a partial anchor is never a placement."""
    entries=(backbone or {}).get('order_source',{}).get('entries',[])
    placed={i['external_index'] for i in insertions}
    out=[]
    for index, entry in enumerate(external_content):
        phone=entry.get('phone')
        if not phone or index in placed:continue
        mid=phone['message_id'];matches=[n for n in nodes if n['Id']==entry.get('node_id')]
        reasons=[];tip_hits=[];node=matches[0] if len(matches)==1 else None
        if node is None:reasons.append('missing_or_ambiguous_owner_node')
        else:
            tip_hits=[i for i,e in enumerate(entries) if node.get('TidTip') and e.get('TidTip')==node['TidTip']]
            if len(tip_hits)!=1:reasons.append('no_unique_recap_tip')
            if node.get('Condition')!={'Type':'ReadPhoneMessage','PhoneMessageId':mid,'ProgressType':{'Type':'CompleteMessage'}}:
                reasons.append('no_same_node_complete_message_condition')
            if node.get('TrackCustomBoard')!={'TrackPhoneMessageBoard':{'PhoneMessageId':mid}}:
                reasons.append('no_matching_tracked_phone_board')
            if entry.get('phase')!='EnterActions':reasons.append('not_same_node_enter_send')
            unknown=[a.get('Name') for phase in ('EnterActions','FinishActions') for a in node.get(phase,[])
                     if _send(a)!=mid and not _effect(a)]
            if unknown:reasons.append('unverified_surrounding_action_shape')
        if phone.get('missing_text_ids'):reasons.append('phone_text_reference_missing')
        if not reasons:reasons.append('placement_guards_not_satisfied')
        out.append({'external_index':index,'message_id':mid,'node_id':entry.get('node_id'),
                    'recap_tip_indices':tip_hits,'reasons':reasons,'source_node':node,
                    'placement_verified':False,'runtime_verified':False})
    return out
