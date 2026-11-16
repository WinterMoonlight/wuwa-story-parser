"""Preserve normal completion-flow bodies when the recap provides no placement."""
from .export_task import walk, flow_key


def completion_only_flows(quest, nodes, extras):
    roots = [n['Id'] for n in nodes if n.get('ParentNodeId') == 0 and n.get('Type') == 'Sequence']
    if len(roots) != 1:
        return []
    links = []
    for key in sorted(extras):
        occurrences = [o for o in walk([quest, nodes]) if o.get('FlowListName') and 'StateId' in o and flow_key(o) == key]
        owners = [n for n in nodes if n.get('Type') == 'ChildQuest' and n.get('ParentNodeId') == roots[0]
                  and not n.get('FailedCondition') and not n.get('ExitCondition')
                  and set(n.get('Condition', {})) == {'Type', 'Flow'}
                  and n['Condition']['Type'] == 'PlayFlow' and flow_key(n['Condition']['Flow']) == key]
        if len(occurrences) != 1 or len(owners) != 1:
            return []
        links.append({'state_key': key, 'node_id': owners[0]['Id'], 'source_node': owners[0],
                      'classification': 'normal_completion_flow', 'placement_verified': False,
                      'note': 'Not a failure branch; no sibling ordering evidence. Do not sort narrative by node IDs.'})
    return links
