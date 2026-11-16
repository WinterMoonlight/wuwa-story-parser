"""Validate a recap-backed reading route without pretending to run gameplay."""
from .export_task import walk, flow_key, PRESENTATION_ACTIONS
from .reading_effects import READING_EFFECTS, validate_reading_effect, effect_evidence


NODE_TYPES = {'Sequence', 'ParallelSelect', 'ConditionSelector', 'ChildQuest',
              'QuestSucceed', 'QuestFailed', 'AlwaysFalse', 'AlwaysTrue', 'Repeater',
              'Action', 'Condition'}
# These task actions do not supply narrative text themselves. Their raw parameters
# remain in the source; gameplay is assumed completed, not executed here.
TASK_EFFECTS = PRESENTATION_ACTIONS | {
    'Wait', 'AddBuffToPlayer', 'RemoveBuffFromPlayer', 'AddTrialCharacter',
    'RemoveTrialCharacter', 'DestroyQuestItem', 'EnableSystem', 'FinishCondition',
    'GetItem', 'GuideTrigger', 'HideTargetRange', 'ShowTargetRange', 'LockEntity',
    'UnlockEntity', 'SetTimeLockState', 'CameraLookAt', 'SetEntityVisible',
    'SetReviveRegion', 'SetPlayerOperationRestriction', 'ServerSetPlayerPos',
    'UnlockTeleportTrigger', 'AddBuffToEntity', 'SetWeather',
    'HideGroup', 'ShowHidedGroup', 'ResetPlayerCameraFocus',
}


def validate_world_effect(name, params):
    """Only admit inspected parameter shapes; retain gameplay as an assumption."""
    shapes = {
        'ResetPlayerCameraFocus': {'ResetType', 'FadeInTime'},
        'SetReviveRegion': {'SetReviveType', 'ReviveId'},
        'SetPlayerOperationRestriction': {'Type'},
        'ServerSetPlayerPos': {'Pos'}, 'UnlockTeleportTrigger': {'TeleportId'},
        'AddBuffToEntity': {'EntityId', 'BuffIds'}, 'SetWeather': {'WeatherId'},
        'HideGroup': {'GroupKey', 'HideConfig', 'IsHidePasserByNpc'},
        'ShowHidedGroup': {'GroupKey', 'DelayShow'},
    }
    if name not in shapes:
        return
    if name == 'HideGroup' and set(params) == {'GroupKey', 'HideConfig', 'IsHidePasserByNpc'}:
        cfg = params['HideConfig']
        if isinstance(cfg, dict) and set(cfg) == {'Type', 'HideRangeEntities', 'AppendEntities', 'AppendLevelPlays'} and cfg['Type'] == 'WorldEntityAndLevelPlay':
            if type(params['IsHidePasserByNpc']) is bool and all(isinstance(cfg[k], list) and all(type(x) is int for x in cfg[k]) for k in ('HideRangeEntities', 'AppendEntities', 'AppendLevelPlays')):
                return
    if name == 'HideGroup' and set(params) == {'GroupKey', 'HideConfig', 'IsHidePasserByNpc'} and params['HideConfig'].get('Type') == 'WorldEntityAndLevelPlay' and set(params['HideConfig']) == {'Type', 'HideRangeEntities'}:
        if isinstance(params['HideConfig']['HideRangeEntities'], list) and all(type(i) is int for i in params['HideConfig']['HideRangeEntities']) and type(params['IsHidePasserByNpc']) is bool:
            return
    if name == 'SetPlayerOperationRestriction' and params.get('Type') == 'DisableModule':
        # Inspected module flags carry no text/flow; retain them without execution.
        allowed = {'Type', 'MoveOption', 'SkillOption', 'UiOption'}
        move, skill, ui = (params.get(k, {}) for k in ('MoveOption', 'SkillOption', 'UiOption'))
        if (set(params) == allowed and move.get('Type') == 'Disable'
                and set(move) <= {'Type', 'Forward', 'Back', 'Left', 'Right', 'ForbidSprint', 'ForceJog'}
                and all(type(v) is bool for k, v in move.items() if k != 'Type')
                and skill == {'Type': 'Disable', 'DisplayMode': 'Hide'}
                and ui.get('Type') == 'EnableSectionalUi'
                and set(ui) <= {'Type', 'ShowQuestTrack', 'ShowScreenEffect'}
                and all(type(v) is bool for k, v in ui.items() if k != 'Type')):
            return
    if name == 'HideGroup' and set(params) == {'GroupKey', 'HideConfig'} and params['HideConfig'].get('Type') == 'SpecifyEntity' and set(params['HideConfig']) == {'Type', 'EntityIds'}:
        return
    if not isinstance(params, dict) or set(params) != shapes[name]:
        raise ValueError('Unsupported world effect parameters: ' + name)
    if name == 'ResetPlayerCameraFocus' and params['ResetType'] != {'Type': 'ResetToDefaultDirection'}:
        raise ValueError('Unsupported camera reset')
    if name == 'HideGroup' and (set(params['HideConfig']) != {'Type', 'HideRangeEntities', 'AppendEntities'} or
                              params['HideConfig']['Type'] != 'WorldEntityAndLevelPlay'):
        raise ValueError('Unsupported hidden group configuration')
    if name == 'SetReviveRegion' and params['SetReviveType'] not in {'Add', 'Remove'}:
        raise ValueError('Unsupported revive operation')
    if name == 'SetPlayerOperationRestriction' and params['Type'] != 'EnableAll':
        raise ValueError('Unsupported player restriction operation')
    if name == 'ServerSetPlayerPos' and (not isinstance(params['Pos'], dict) or
            not {'X', 'Y', 'Z'} <= set(params['Pos']) or set(params['Pos']) - {'X', 'Y', 'Z', 'A'}):
        raise ValueError('Unsupported server position shape')


def audit_task(quest, nodes, external_actions=frozenset(), reading_projection=False):
    by_id = {n['Id']: n for n in nodes}
    if len(by_id) != len(nodes):
        raise ValueError('Duplicate task node IDs')
    roots = [n for n in nodes if n.get('ParentNodeId') == 0]
    if len(roots) != 1 or roots[0]['Type'] != 'Sequence':
        raise ValueError('Unsupported task topology: expected one root Sequence')
    for n in nodes:
        if n['Type'] not in NODE_TYPES:
            raise ValueError('Unsupported task topology: ' + str(n['Type']))
        seen = set()
        current = n
        while current.get('ParentNodeId') != 0:
            if current['Id'] in seen:
                raise ValueError('Cycle in task parent topology')
            seen.add(current['Id'])
            parent = current.get('ParentNodeId')
            if parent not in by_id:
                raise ValueError('Missing task parent: ' + str(parent))
            current = by_id[parent]
    if sum(n['Type'] == 'QuestSucceed' for n in nodes) != 1:
        raise ValueError('Expected one task success node')
    refs = []
    actions = []
    reading_effects = []
    for owner, value in [('quest', quest)] + [(n['Id'], n) for n in nodes]:
        for obj in walk(value):
            if obj.get('FlowListName') and 'FlowId' in obj:
                if 'StateId' not in obj:
                    raise ValueError('Flow reference has no explicit StateId')
                refs.append({'owner': owner, 'state_key': flow_key(obj)})
            if any(obj.get(k) for k in ('TidTalk', 'TidTalkOption', 'TidCenterText')):
                raise ValueError('Task contains narrative text outside referenced flows')
            if 'Name' in obj and 'Params' in obj:
                name = obj['Name']
                if reading_projection and name in READING_EFFECTS:
                    validate_reading_effect(name, obj['Params'])
                    reading_effects.append({'owner': owner, **effect_evidence(name, obj['Params'])})
                else:
                    validate_world_effect(name, obj['Params'])
                if name != 'PlayFlow' and name not in TASK_EFFECTS and name not in external_actions and not (reading_projection and name in READING_EFFECTS):
                    raise ValueError('Unsupported task action: ' + str(name))
                actions.append({'owner': owner, 'name': name,
                                'handling': ('external_content_appendix' if name in external_actions else
                                             'covered_by_recap_reference' if name == 'PlayFlow' else 'gameplay_assumed_completed')})
    return {'mode': 'recap_reading_projection', 'parent_links_valid': True,
            'runtime_graph_executed': False, 'flow_references': refs,
            'task_actions': actions, 'reading_effects': reading_effects,
            'condition_assumptions': [{'node_id': n['Id'], 'condition': n['Condition']}
                                      for n in nodes if n.get('Condition')]}
