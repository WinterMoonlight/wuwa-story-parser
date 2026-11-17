"""Identify hidden teaching calls in an independently triggered task branch."""
from .export_task import flow_key


def _flow(value):
    if (not isinstance(value, dict)
            or set(value) != {'FlowListName', 'FlowId', 'StateId'}
            or not isinstance(value['FlowListName'], str)
            or not value['FlowListName']
            or type(value['FlowId']) is not int or value['FlowId'] <= 0
            or type(value['StateId']) is not int or value['StateId'] <= 0):
        return None
    return flow_key(value)


def _action(action, name):
    return (isinstance(action, dict) and action.get('Name') == name
            and not set(action) - {'Name', 'Params', 'Async', 'ActionId', 'ActionGuid'})


def _references(value, by_id, owner=None, path=()):
    """Retain owning node and path, checking repeated embedded node copies."""
    if isinstance(value, dict):
        if value.get('Type') == 'ChildQuest' and 'Id' in value:
            owner = value['Id']
            path = ()
            canonical = by_id.get(owner)
            if canonical is None or {k: v for k, v in value.items() if k != 'ParentNodeId'} != {
                    k: v for k, v in canonical.items() if k != 'ParentNodeId'}:
                yield None, None, None
                return
        key = _flow({field: value[field] for field in ('FlowListName', 'FlowId', 'StateId')}
                    if all(field in value for field in ('FlowListName', 'FlowId', 'StateId')) else None)
        if key:
            yield key, owner, path
        for field, child in value.items():
            yield from _references(child, by_id, owner, path + (field,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _references(child, by_id, owner, path + (index,))


def guidance_evidence(nodes, recap_entries):
    """Require the inspected PlayFlow-condition -> UI/guide pair structure.

    Hidden recap flags alone carry no ordering meaning. The enclosing
    AlwaysFalse/ParallelSelect branch and explicit guide action provide the
    independent instructional context recorded here.
    """
    by_id = {node['Id']: node for node in nodes}
    if len(by_id) != len(nodes):
        return {}
    references = list(_references(nodes, by_id))
    if any(key is None for key, _, _ in references):
        return {}
    result = {}
    for branch in nodes:
        if (branch.get('Type') != 'Sequence'
                or set(branch) - {'Type', 'Id', 'Desc', 'ParentNodeId'}):
            continue
        wrapper = by_id.get(branch.get('ParentNodeId'), {})
        parallel = by_id.get(wrapper.get('ParentNodeId'), {})
        if (wrapper.get('Type') != 'AlwaysFalse'
                or set(wrapper) - {'Type', 'Id', 'Desc', 'ParentNodeId'}
                or parallel.get('Type') != 'ParallelSelect'
                or parallel.get('Count') != 1
                or set(parallel) - {'Type', 'Id', 'Desc', 'ParentNodeId', 'Count'}):
            continue
        if [node['Id'] for node in nodes if node.get('ParentNodeId') == wrapper['Id']] != [branch['Id']]:
            continue
        children = [node for node in nodes if node.get('ParentNodeId') == branch['Id']]
        if len(children) != 2:
            continue
        node_fields = {'Type', 'Id', 'Desc', 'ParentNodeId', 'Condition', 'TidTip',
                       'TrackTarget', 'HideUi', 'HideTip', 'EnterActions', 'FinishActions'}
        if any(node.get('Type') != 'ChildQuest' or node.get('HideUi') is not True
               or node.get('HideTip') is not True or set(node) - node_fields
               or node.get('EnterActions') for node in children):
            continue
        flow_nodes = [node for node in children if node.get('Condition', {}).get('Type') == 'PlayFlow']
        ui_nodes = [node for node in children if node.get('Condition') == {'Type': 'ShowUi', 'UiType': {'Type': 'All'}}]
        if len(flow_nodes) != 1 or len(ui_nodes) != 1:
            continue
        first, second = flow_nodes[0], ui_nodes[0]
        condition = first['Condition']
        if set(condition) != {'Type', 'Flow'} or first.get('FinishActions'):
            continue
        first_key = _flow(condition['Flow'])
        actions = second.get('FinishActions', [])
        if not first_key or not isinstance(actions, list) or len(actions) != 2:
            continue
        guide, call = actions
        guide_params = guide.get('Params', {})
        if (not _action(guide, 'GuideTrigger') or guide.get('Async', False) is not False
                or not isinstance(guide_params, dict) or set(guide_params) != {'Type', 'GuideId'}
                or guide_params['Type'] != 'BeginnerGuide'
                or type(guide_params['GuideId']) is not int or guide_params['GuideId'] <= 0
                or not _action(call, 'PlayFlow') or call.get('Async') is not True):
            continue
        second_key = _flow(call.get('Params'))
        if not second_key or first_key == second_key:
            continue
        expected = {first_key: (first['Id'], ('Condition', 'Flow')),
                    second_key: (second['Id'], ('FinishActions', 1, 'Params'))}
        valid = True
        entries = {}
        for key, expected_reference in expected.items():
            owners = [(owner, path) for candidate, owner, path in references if candidate == key]
            matches = [(index, entry) for index, entry in enumerate(recap_entries)
                       if _flow(entry.get('Flow')) == key]
            if (not owners or any(owner != expected_reference for owner in owners)
                    or len(matches) != 1 or matches[0][1].get('IsHideUi') is not True):
                valid = False
                break
            entries[key] = matches[0]
        if not valid:
            continue
        proof = {'branch_node_id': branch['Id'], 'wrapper_node_id': wrapper['Id'],
                 'parallel_node_id': parallel['Id'], 'source_nodes': [parallel, wrapper, branch, first, second],
                 'guide_id': guide_params['GuideId'], 'runtime_verified': False,
                 'order_verified': False,
                 'basis': 'hidden UI teaching pair in independent AlwaysFalse/ParallelSelect branch'}
        for key, (index, entry) in entries.items():
            result[key] = {**proof, 'entry_index': index, 'source_entry': entry,
                           'owner_node_id': expected[key][0], 'source_path': list(expected[key][1])}
    return result
