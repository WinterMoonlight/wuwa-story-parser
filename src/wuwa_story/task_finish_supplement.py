"""Restore a unique task completion call missing from the recap."""
from copy import deepcopy
import math

from .coverage import validate_world_effect
from .dependency_positions import _sync_flow
from .levelplay_completion import ancestry
from .task_flows import classify_task_flows
from .task_local_order import _flow_segment


def _known_scene_action(action):
    if (not isinstance(action, dict) or action.get('Async', False) is not False
            or set(action) - {'Name', 'Params', 'Async', 'ActionGuid', 'ActionId'}):
        return False
    name, params = action.get('Name'), action.get('Params', {})
    if not isinstance(params, dict):
        return False
    if name == 'DestroyEntity':
        return (set(params) == {'EntityIds'} and isinstance(params['EntityIds'], list)
                and all(type(i) is int and i > 0 for i in params['EntityIds']))
    if name == 'SetPlayerPos':
        config = params.get('TelePortConfig', {})
        position = config.get('TargetPos', {}) if isinstance(config, dict) else {}
        return (set(params) == {'TelePortConfig'} and isinstance(config, dict)
                and set(config) == {'Type', 'TargetPos'} and type(config['Type']) is int and config['Type'] == 0
                and isinstance(position, dict) and {'X', 'Y', 'Z'} <= set(position) <= {'X', 'Y', 'Z', 'A'}
                and all(type(v) in (int, float) and math.isfinite(v) for v in position.values()))
    if name == 'ShowHidedGroup':
        try:
            validate_world_effect(name, params)
        except (ValueError, TypeError, KeyError):
            return False
        return isinstance(params['GroupKey'], str) and bool(params['GroupKey']) and type(params['DelayShow']) is bool
    if name == 'FadeOutScreen':
        ease = params.get('Ease', {})
        return (set(params) == {'Ease'} and isinstance(ease, dict) and set(ease) == {'Type', 'Duration'}
                and type(ease['Type']) is int and type(ease['Duration']) in (int, float)
                and math.isfinite(ease['Duration']) and ease['Duration'] >= 0)
    return False


def insert_task_finish_supplements(quest, nodes, backbone, states, source, choices=None):
    try:
        occurrences = classify_task_flows(quest, nodes)
    except ValueError:
        return []
    segments = backbone['segments']
    used = {s['state_key'] for s in segments}
    used.update(f['state_key'] for s in segments for f in s.get('inserted_task_flows', []))
    reviews = {r['state_key']: r for r in backbone.get('task_only_review', [])}
    insertions = []
    for node in nodes:
        if node.get('Type') != 'ChildQuest' or any(node.get(k) for k in ('ExitCondition', 'FailedCondition', 'Slots')):
            continue
        condition = node.get('Condition', {})
        if set(condition) != {'Type', 'Flow'} or condition['Type'] != 'PlayFlow':
            continue
        anchor = _sync_flow({'Name': 'PlayFlow', 'Params': condition['Flow']})
        targets = [s for s in segments if s['state_key'] == anchor]
        if len(targets) != 1 or targets[0]['status'] != 'parsed' or targets[0].get('prefix_event_count'):
            continue
        chain, error = ancestry(node['Id'], nodes)
        if (error or len(chain) < 2 or any(n['Type'] != 'Sequence' for n in chain[1:])
                or any(n.get(k) for n in chain[1:] for k in ('Condition', 'ExitCondition', 'FailedCondition', 'Slots'))):
            continue
        actions = node.get('FinishActions', [])
        if not isinstance(actions, list) or not actions or not all(_known_scene_action(a) for a in actions[:-1]):
            continue
        call = actions[-1]
        if not isinstance(call, dict) or type(call.get('Async', False)) is not bool:
            continue
        key = _sync_flow({k: v for k, v in call.items() if k != 'Async'})
        if (not key or key in used or key not in states
                or any(len(occurrences.get(k, [])) != 1 for k in (anchor, key))):
            continue
        # A detached async block can be appended at the end of the known backbone.
        # Placing it before another known segment would also assert its completion order.
        if call.get('Async', False) and targets[0] is not segments[-1]:
            continue
        parsed = _flow_segment(key, states, source, choices)
        if (parsed is None or not parsed['events'] or parsed['missing_text_ids']
                or parsed['unverified_content']
                or any(e['kind'] not in {'dialogue', 'choice', 'narration', 'center_text'} for e in parsed['events'])):
            continue
        proof = {'kind': 'task_finish_supplement', 'node_id': node['Id'], 'after_state': anchor,
                 'state_key': key, 'condition': deepcopy(condition), 'source_actions': deepcopy(actions),
                 'ancestor_ids': [n['Id'] for n in chain[1:]], 'invocation_async': call.get('Async', False),
                 'order_basis': 'completed task condition flow before unique finish call',
                 'runtime_verified': False, 'other_callback_content_verified': False,
                 'later_async_completion_order_verified': False}
        events = deepcopy(parsed['events'])
        for event in events:
            event['task_placement'] = deepcopy(proof)
        target = targets[0]
        target['events'].extend(events)
        target.setdefault('inserted_task_flows', []).append({
            'state_key': key, 'proof': proof, 'source_actions': parsed['source_actions'],
            'action_fields': parsed['action_fields'], 'sha256': parsed['sha256'], 'route': parsed['route']})
        if key in reviews:
            reviews[key].update(classification='placed_task_finish_supplement', placement_verified=True,
                                proof=proof, visible_event_count=len(events))
        used.add(key)
        insertions.append(proof)
    if insertions:
        backbone['task_finish_supplements'] = insertions
    return insertions
