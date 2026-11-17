"""Narrow phone-step world context: record configuration, never run effects."""
from collections import defaultdict
import hashlib
from .database import embedded


def _positive(value):
    return type(value) is int and value > 0


def _shape(action):
    return (isinstance(action, dict)
            and not set(action)-{'Name','Params','Async','ActionId','ActionGuid'}
            and action.get('Async', False) is False and isinstance(action.get('Params'),dict))


def _entity(entity_id, source):
    if source is None:return None
    index=getattr(source,'_phone_context_entities',None)
    if index is None:
        index=defaultdict(list)
        for r in source.rows('db_level_entity.db','levelentityconfig'):index[r['EntityId']].append(r)
        source._phone_context_entities=index
    matches=index.get(entity_id,[])
    if len(matches)!=1:return None
    row=matches[0]
    configs=[(i,v) for i,v in embedded(row['BinData']) if isinstance(v,dict)]
    if not configs or any(v!=configs[0][1] for _,v in configs):return None
    return {'map_id':row['MapId'],'entity_id':entity_id,'row_id':row['Id'],
            'source_sha256':hashlib.sha256(row['BinData']).hexdigest(),
            'source_config':configs[0][1],'equivalent_json_fields':[i for i,_ in configs]}


def _preload(action):
    if not _shape(action) or action['Name']!='Preload':return False
    p=action['Params'];o=p.get('PreloadObjectType',{})
    if set(p)!={'PreloadObjectType'} or not isinstance(o,dict) or set(o)!={'Type','FlowData'} or o['Type']!='PreloadFlows':return False
    f=o['FlowData']
    return (isinstance(f,dict) and set(f)=={'FlowListName','FlowId','StateId'}
            and isinstance(f['FlowListName'],str) and bool(f['FlowListName'])
            and _positive(f['FlowId']) and _positive(f['StateId']))


def _position(p, allowed):
    return (isinstance(p,dict) and set(p)==allowed
            and all(v is None or type(v) in (int,float) for v in p.values()))


def _base(config):
    b=config.get('BaseInfoComponent',{})
    if not isinstance(b,dict) or set(b)-{'PackId','Category','Occupation','IsForceDestroy'}:return False
    if 'PackId'in b and (type(b['PackId'])is not int or b['PackId']<0):return False
    if b.get('Occupation')is not None:return False
    if 'IsForceDestroy'in b and type(b['IsForceDestroy'])is not bool:return False
    if 'Category'in b:
        c=b['Category']
        if not isinstance(c,dict) or set(c)!={'EntityPlotBindingType'} or not isinstance(c['EntityPlotBindingType'],str):return False
    return True


def _range(config):
    if 'RangeComponent'not in config:return True
    r=config['RangeComponent']
    if not isinstance(r,dict) or set(r)!={'Shape'} or not isinstance(r['Shape'],dict):return False
    s=r['Shape']
    if set(s) not in ({'Center','Size'},{'Center','Radius'}) or not _position(s['Center'],{'X','Y','Z'}):return False
    return (_position(s['Size'],{'X','Y','Z'}) if 'Size'in s else type(s['Radius'])in(int,float) and s['Radius']>0)


def _wake_config(config):
    if set(config)-{'BaseInfoComponent','NpcPerformComponent','RangeComponent','TriggerComponent'}:return False
    if not _base(config) or not _range(config):return False
    # Other components may define callbacks; admit only inspected configuration families.
    npc=config.get('NpcPerformComponent',{})
    if not isinstance(npc,dict) or set(npc)-{'ShowOnStandby','IsStare'}:return False
    if 'ShowOnStandby' in npc:
        s=npc['ShowOnStandby']
        if (not isinstance(s,dict) or set(s)!={'Type','PlayMode','Montages'}
                or s['Type']!='Finite' or s['PlayMode']!='Orderly' or not isinstance(s['Montages'],list)):return False
        for m in s['Montages']:
            if not isinstance(m,dict) or set(m)!={'RegisteredMontageId','Time'}:return False
            r=m['RegisteredMontageId']
            if not isinstance(r,dict) or set(r)!={'MontageId','IsAbp'} or not _positive(r['MontageId']) or type(r['IsAbp'])is not bool:return False
            if type(m['Time'])not in (int,float) or m['Time']<0:return False
    if 'IsStare'in npc and type(npc['IsStare'])is not bool:return False
    trigger=config.get('TriggerComponent',{})
    return (isinstance(trigger,dict) and not set(trigger)-{'Actions','MaxTriggerTimes','Condition'}
            and trigger.get('Condition') is None and trigger.get('MaxTriggerTimes') is None
            and isinstance(trigger.get('Actions',[]),list) and all(_preload(a) for a in trigger.get('Actions',[])))


def _state_callback(action):
    if not _shape(action):return False
    p=action['Params'];name=action.get('Name')
    if name=='EnableNearbyTracking':return set(p)=={'IsEnable'} and type(p['IsEnable'])is bool
    if name=='UnlockTeleportTrigger':return set(p)=={'TeleportId'} and _positive(p['TeleportId'])
    return name=='AwakeEntity' and p=={'EntityIds':[]}


def _state_config(config,state):
    if set(config)-{'BaseInfoComponent','EntityStateComponent','TeleportComponent'}:return False
    if not _base(config):return False
    if 'TeleportComponent'in config:
        t=config['TeleportComponent']
        if not isinstance(t,dict) or set(t)!={'TeleporterId','TeleportPos'} or not _positive(t['TeleporterId']) or not _position(t['TeleportPos'],{'X','Y','Z','A'}):return False
    c=config.get('EntityStateComponent',{})
    if not isinstance(c,dict) or set(c)!={'StateChangeBehaviors'} or not isinstance(c['StateChangeBehaviors'],list):return False
    matches=[b for b in c['StateChangeBehaviors'] if isinstance(b,dict) and b.get('State')==state]
    if len(matches)!=1:return False
    b=matches[0]
    return (set(b)=={'State','Action','PendingConditionAvailable'} and type(b['PendingConditionAvailable'])is bool
            and isinstance(b['Action'],list) and all(_state_callback(a) for a in b['Action']))


def context_effect(action, phase, source):
    if phase not in ('EnterActions','FinishActions') or not _shape(action):return None
    name=action.get('Name');p=action['Params'];entities=[];valid=False
    if name=='SetTime':
        valid=(set(p)=={'Hour','Min','ShowUi'} and type(p['Hour'])is int and 0<=p['Hour']<24
               and type(p['Min'])is int and 0<=p['Min']<60 and p['ShowUi']is False)
    elif phase=='FinishActions':
        if name=='AwakeEntity' and set(p)=={'EntityIds'} and isinstance(p['EntityIds'],list) and p['EntityIds'] and all(_positive(i)for i in p['EntityIds']):
            entities=[_entity(i,source) for i in p['EntityIds']]
            valid=all(e is not None and _wake_config(e['source_config'])for e in entities)
        elif name=='ChangeEntityState' and set(p)=={'Type','EntityId','State'} and p['Type']=='Directly' and _positive(p['EntityId']) and isinstance(p['State'],str) and p['State']:
            e=_entity(p['EntityId'],source);entities=[e]
            valid=e is not None and _state_config(e['source_config'],p['State'])
        elif name=='HideGroup':
            c=p.get('HideConfig',{})
            valid=(set(p)=={'GroupKey','HideConfig','IsHidePasserByNpc'} and isinstance(p['GroupKey'],str) and bool(p['GroupKey'])
                   and type(p['IsHidePasserByNpc'])is bool and isinstance(c,dict) and set(c)=={'Type','HideRangeEntities'}
                   and c['Type']=='WorldEntityAndLevelPlay' and isinstance(c['HideRangeEntities'],list)
                   and all(_positive(i)for i in c['HideRangeEntities']))
        elif name=='UnlockTeleportTrigger':valid=set(p)=={'TeleportId'} and _positive(p['TeleportId'])
        elif name=='FocusOnMapMark':
            m=p.get('MapMarkType',{})
            valid=set(p)=={'MapMarkType'} and isinstance(m,dict) and set(m)=={'Type','MarkId'} and m['Type']=='Custom' and _positive(m['MarkId'])
    if not valid:return None
    return {'source_action':action,'phase':phase,'entities':entities,'runtime_executed':False,
            'world_state_effects_verified':False,'asset_callbacks_verified':False,
            'scope':'phone recap-tip placement context only; not globally ignorable presentation',
            'preload_is_playback':False}
