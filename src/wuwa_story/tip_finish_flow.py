"""Place a parsed task finish flow at its unique, empty recap tip interval."""
from copy import deepcopy

from .recap_order import anchored_finish_flows
from .task_local_order import _flow_segment
from .declared_entity_content import declared_entity_content
from .export_task import walk
from .levelplay_completion import ancestry
from .dependency_positions import _sync_flow


def _completed_interaction_anchor(quest, nodes, backbone, proof, source):
    """Check whether the preceding recap interaction requires this step to finish."""
    if source is None:
        return None, False
    links, _ = declared_entity_content(quest, source)
    matches = []
    chain, error = ancestry(proof['node_id'], nodes)
    if error:
        return None, True
    node = chain[0]
    dungeon = next((n['DungeonId'] for n in chain if type(n.get('DungeonId')) is int), quest.get('DungeonId'))
    maps = [r['MapConfigId'] for r in source.rows('db_instance_dungeon.db', 'instancedungeon') if r['Id'] == dungeon]
    for link in links:
        if link['component'] != 'InteractComponent':
            continue
        options = link['source_component'].get('Options', [])
        if not isinstance(options, list):
            continue
        targets = [s for s in backbone['segments'] if s['state_key'] == link['state_key']]
        earlier = [s for s in targets if s['entry_index'] < proof['recap_entry_index']]
        if not earlier:
            continue
        checks = [c for option in options if isinstance(option, dict) for c in walk(option.get('Condition', {}))
                  if c.get('Type') == 'CheckChildQuestFinished' and c.get('QuestId') == quest['Id']
                  and c.get('ChildQuestId') == proof['node_id']]
        if not checks:
            continue
        required = {'Type': 'CheckChildQuestFinished', 'QuestId': quest['Id'],
                    'ChildQuestId': proof['node_id'], 'Compare': 'Eq'}
        if len(options) != 1 or options[0].get('Condition') != {'Type': 0, 'Conditions': [required]}:
            return None, True
        option = options[0]
        condition = option['Condition']
        flow = option.get('Type', {})
        tracking = node.get('TrackTarget', {}).get('TrackType', {})
        if (len(targets) != 1 or targets[0]['entry_index'] != proof['recap_entry_index'] - 1
                or maps != [link['map_id']] or tracking.get('Type') != 'Entities'
                or tracking.get('EntityIds') != [link['entity_id']]
                or not isinstance(flow, dict) or flow.get('Type') != 'Flow'
                or _sync_flow({'Name': 'PlayFlow', 'Params': flow.get('Flow')}) != link['state_key']):
            return None, True
        matches.append((targets[0], link, condition))
    if not matches:
        return None, False
    if len(matches) != 1:
        return None, True
    target, link, condition = matches[0]
    return {**deepcopy(proof), 'tip_entry_index': proof['recap_entry_index'],
            'recap_entry_index': target['entry_index'], 'before_state': target['state_key'],
            'ordering_basis': 'synchronous task completion precedes the adjacent recap interaction gated by that completion',
            'interaction_condition': deepcopy(condition), 'entity_source': deepcopy(link)}, False


def insert_tip_finish_flows(quest, nodes, backbone, states, source, choices=None):
    entries = backbone['order_source']['entries']
    _, proofs = anchored_finish_flows(quest, nodes, entries, allow_nested=True)
    present = {s['state_key'] for s in backbone['segments']}
    reviews = {r['state_key']: r for r in backbone['task_only_review']}
    inserted = []
    for proof in proofs:
        key = proof['state_key']
        if key in present or key not in states or reviews.get(key, {}).get('placement_verified'):
            continue
        interaction_proof, conflict = _completed_interaction_anchor(quest, nodes, backbone, proof, source)
        if conflict:
            continue
        if interaction_proof:
            proof = interaction_proof
        parsed = _flow_segment(key, states, source, choices)
        if (parsed is None or parsed['missing_text_ids'] or not parsed['events']
                or any(e.get('kind') not in {'dialogue', 'choice', 'narration', 'center_text'} for e in parsed['events'])
                or any(u.get('kind') != 'presentation_state_restore' for u in parsed['unverified_content'])):
            continue
        segment = {'entry_index': proof['recap_entry_index'], 'state_key': key,
                   'source_entry': deepcopy(entries[proof.get('tip_entry_index', proof['recap_entry_index'])]),
                   'status': 'parsed',
                   'order_origin': 'task_finish_before_interaction' if interaction_proof else 'task_finish_tip',
                   'placement_proof': deepcopy(proof),
                   **deepcopy(parsed)}
        for event in segment['events']:
            event['task_placement'] = deepcopy(proof)
        position = next((i for i, s in enumerate(backbone['segments'])
                         if s['entry_index'] >= proof['recap_entry_index']), len(backbone['segments']))
        backbone['segments'].insert(position, segment)
        present.add(key)
        inserted.append(deepcopy(proof))
        if key in reviews:
            reviews[key].update(classification='placed_tip_finish_flow', placement_verified=True,
                                proof=deepcopy(proof), visible_event_count=len(segment['events']))
    if inserted:
        backbone['parsed_segments'] += len(inserted)
        backbone['tip_flow_insertions'] = inserted
    return inserted
