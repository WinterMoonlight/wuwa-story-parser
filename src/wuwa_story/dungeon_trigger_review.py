"""Describe candidate trigger occurrences without assigning gameplay order."""
from collections import defaultdict


def trigger_review(audits, links, candidate_keys):
    reviews = []
    for audit in audits:
        if not audit.get('dungeon_link'):
            continue
        nodes = {node['Id']: node for node in audit['nodes']}
        grouped = defaultdict(list)
        for link in links:
            if link['levelplay_id'] != audit['levelplay_id'] or link['state_key'] not in candidate_keys:
                continue
            node = nodes.get(link['node_id'])
            if node is None:
                continue
            ancestors, seen = [], {node['Id']}
            parent = node.get('ParentNodeId', 0)
            while parent and parent in nodes and parent not in seen:
                seen.add(parent)
                ancestor = nodes[parent]
                ancestors.append({'node_id':parent,'type':ancestor['Type'],
                                  'condition':ancestor.get('Condition'),
                                  'save_config':ancestor.get('SaveConfig'),
                                  'count':ancestor.get('Count')})
                parent = ancestor.get('ParentNodeId',0)
            completion_successors = []
            if link['phase']=='Condition' and node.get('Condition',{}).get('Type')=='PlayFlow':
                for index, action in enumerate(node.get('FinishActions',[])):
                    if action.get('Name')=='PlayFlow' and action.get('Async',False) is False:
                        completion_successors.append({'action_index':index,'source_action':action,
                            'scope':'same node activation after configured flow condition completes',
                            'actual_condition_playback_verified':False})
            grouped[link['state_key']].append({
                'node_id':node['Id'], 'phase':link['phase'],
                'reference_kind':link.get('reference_kind','action_invocation'),
                'condition':node.get('Condition'), 'source_node':node,
                'source_link':link, 'ancestors':ancestors,
                'completion_successors':completion_successors,
                'trigger_executed':False, 'playback_completed':False})
        for key, occurrences in sorted(grouped.items()):
            unique = {(o['node_id'],o['phase'],o['source_link'].get('action_index')) for o in occurrences
                      if o['reference_kind']=='action_invocation'}
            reviews.append({'state_key':key, 'levelplay_id':audit['levelplay_id'],
                            'dungeon_id':audit['dungeon_link']['dungeon_id'],
                            'occurrences':occurrences, 'callsite_count':len(unique),
                            'reference_count':len(occurrences),
                            'multiple_callsites':len(unique)>1,
                            'order_verified':False, 'single_playback_verified':False})
    return reviews
