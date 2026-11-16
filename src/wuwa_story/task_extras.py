"""Narrow same-node transition placement and task-only reference evidence."""
from .export_task import walk, flow_key, flow_actions, Exporter
from .rendering import render_result


def references(value, key):
    return any(o.get('FlowListName') and 'StateId' in o and 'FlowId' in o
               and flow_key(o) == key for o in walk(value))


def interaction_evidence(owner, nodes, entries):
    """Record branch conditions and nearby recap evidence, never infer execution order."""
    by_id = {n['Id']: n for n in nodes}
    def lineage(node):
        result, seen = [], set()
        while node and node['Id'] not in seen:
            seen.add(node['Id']); result.append(node)
            node = by_id.get(node.get('ParentNodeId'))
        return result
    chain = lineage(owner)
    boundary = next((n for n in chain if n.get('Type') == 'AlwaysFalse'), None)
    if boundary is None:
        return None
    branch = [n for n in nodes if boundary['Id'] in {a['Id'] for a in lineage(n)}]
    interactions = [{'node_id': n['Id'], 'condition': n['Condition']}
                    for n in branch if any(o.get('Type') == 'DoInteract' for o in walk(n.get('Condition', {})))]
    if not interactions:
        return None
    tips = {n.get('TidTip') for n in branch} - {None, ''}
    direct = [{'entry_index': i, 'tid_tip': e['TidTip']} for i, e in enumerate(entries) if e.get('TidTip') in tips]
    region = None
    for ancestor in chain[chain.index(boundary) + 1:]:
        members = [n for n in nodes if ancestor['Id'] in {a['Id'] for a in lineage(n)}]
        matches = [{'entry_index': i, 'node_id': n['Id'], 'tid_tip': e['TidTip'], 'entry': e}
                   for i, e in enumerate(entries) for n in members
                   if e.get('TidTip') and e['TidTip'] == n.get('TidTip')]
        if matches:
            region = {'ancestor_id': ancestor['Id'], 'matches': matches,
                      'scope': 'shared_ancestor_only_not_playback_interval'}
            break
    conditions = [{'node_id': n['Id'], 'condition': n['Condition']} for n in branch if n.get('Condition')]
    variables = {(o.get('Type'), o.get('Source'), o.get('Name')) for c in conditions for o in walk(c)
                 if o.get('Source') and o.get('Name')}
    writes = [{'node_id': n['Id'], 'action': a} for n in nodes for a in walk(n)
              if a.get('Name') == 'SetVar' and
              tuple(a.get('Params', {}).get('VarLeft', {}).get(k) for k in ('Type', 'Source', 'Name')) in variables]
    entities = {o['EntityId'] for c in interactions for o in walk(c) if 'EntityId' in o}
    lifecycle = [{'node_id': n['Id'], 'action': a} for n in nodes for a in walk(n)
                 if a.get('Name') in {'AwakeEntity', 'DestroyEntity', 'LockEntity', 'UnlockEntity'}
                 and entities.intersection(a.get('Params', {}).get('EntityIds', []))]
    return {'branch_root': boundary['Id'], 'conditions': conditions, 'interactions': interactions,
            'variable_writes': writes, 'entity_lifecycle': lifecycle,
            'direct_tip_matches': direct, 'recap_region_evidence': region,
            'runtime_verified': False, 'placement_verified': False,
            'reason': 'branch conditions and shared recap region do not establish a unique playback position'}


def review_extras(quest, nodes, backbone, states, source):
    recap = {s['state_key'] for s in backbone['segments']}
    extras = {flow_key(o) for o in walk([quest, nodes])
              if o.get('FlowListName') and 'FlowId' in o and 'StateId' in o} - recap
    by_id = {n['Id']: n for n in nodes}
    reviews = []
    for key in sorted(extras):
        owners = [n for n in nodes if references(n, key)]
        chains = []
        for n in owners:
            chain, seen = [], set()
            parent = n.get('ParentNodeId')
            while parent in by_id and parent not in seen:
                seen.add(parent); p = by_id[parent]
                chain.append({'id': parent, 'type': p['Type'], 'count': p.get('Count')})
                parent = p.get('ParentNodeId')
            chains.append({'node_id': n['Id'], 'ancestors': chain})
        genders = [{'selector_id': n['Id'], 'condition': slot.get('Condition')}
                   for n in nodes if n.get('Type') == 'ConditionSelector'
                   for slot in n.get('Slots', []) if references(slot.get('Node', {}), key)
                   and any(o.get('Type') == 'CheckPlayerGender' for o in walk(slot.get('Condition', {})))]
        async_calls = [o for n in owners for o in walk(n)
                       if o.get('Name') == 'PlayFlow' and o.get('Async') is True and references(o, key)]
        review = {'state_key': key, 'owner_nodes': owners, 'ancestor_chains': chains,
                  'gender_conditions': genders, 'async_calls': async_calls,
                  'classification': 'gender_conditioned' if genders else 'asynchronous' if async_calls else
                  'parallel_conditioned' if any(a['type'] in ('ParallelSelect', 'AlwaysFalse') for c in chains for a in c['ancestors']) else 'unplaced',
                  'placement_verified': False}
        evidence = [interaction_evidence(n, nodes, backbone.get('order_source', {}).get('entries', [])) for n in owners]
        review['interaction_evidence'] = [e for e in evidence if e is not None]
        from .sync_prefix import insert_qte_prefix
        insert_qte_prefix(review, quest, nodes, backbone, states, source)
        # A pure screen-text flow immediately before a unique synchronous recap call.
        if len(owners) == 1 and chains[0]['ancestors']:
            n = owners[0]
            actions = n.get('FinishActions', [])
            if (n.get('Type') == 'ChildQuest' and not n.get('FailedCondition') and not n.get('ExitCondition')
                    and all(a['type'] == 'Sequence' for a in chains[0]['ancestors']) and len(actions) >= 2):
                first, second = actions[-2:]
                fields = {'FlowListName', 'FlowId', 'StateId'}
                pair_ok = all(a.get('Name') == 'PlayFlow' and a.get('Async', False) is False
                              and set(a.get('Params', {})) == fields
                              and set(a) <= {'Name', 'Params', 'Async', 'ActionGuid', 'ActionId'}
                              for a in (first, second))
                if pair_ok and flow_key(first['Params']) == key:
                    anchor = flow_key(second['Params'])
                    targets = [s for s in backbone['segments'] if s['state_key'] == anchor]
                    occurrences = lambda k: sum(1 for o in walk([quest, nodes])
                        if o.get('FlowListName') and 'FlowId' in o and 'StateId' in o and flow_key(o) == k)
                    if (key in states and len(targets) == 1 and targets[0]['status'] == 'parsed'
                            and occurrences(key) == occurrences(anchor) == 1):
                        raw, raw_fields = flow_actions(states[key]['BinData'])
                        talks = [a for a in raw if a.get('Name') == 'ShowTalk']
                        items = [i for a in talks for i in a.get('Params', {}).get('TalkItems', [])]
                        pure = (items and all(a.get('Name') in {'SetPlotMode', 'ShowTalk'} for a in raw)
                                and all(i.get('Type') == 'CenterText' and not i.get('Options')
                                        and not i.get('Actions') for i in items))
                        if pure:
                            try:
                                p = Exporter(source=source, allow_incomplete=True); p.state_key = key
                                control = p.actions(raw)
                                rendered = render_result({'title': '', 'route': {'choices': p.decisions}, 'events': p.events})
                                safe = not (control or p.missing or p.unverified_content or p.decisions)
                            except (ValueError, KeyError, TypeError, IndexError):
                                safe = False
                            if safe:
                                proof = {'node_id': n['Id'], 'before_state': anchor,
                                         'source_actions': actions[-2:], 'runtime_verified': False,
                                         'basis': 'adjacent synchronous finish calls; unique recap anchor; pure screen text'}
                                visible = [e for e in rendered['events'] if e.get('text', '').strip()]
                                for e in visible:
                                    if e.get('source_item', {}).get('Type') == 'CenterText':
                                        e.update(kind='center_text', display_name='画面文字', raw_display_name='画面文字')
                                    e['task_placement'] = proof
                                targets[0]['events'][0:0] = visible
                                targets[0].setdefault('inserted_task_flows', []).append({
                                    'state_key': key, 'proof': proof, 'source_actions': raw, 'action_fields': raw_fields})
                                review.update(classification='placed_screen_text', placement_verified=True,
                                              proof=proof, text_evidence=rendered['events'], visible_event_count=len(visible))
        # Only a unique direct child call pair, below Sequence ancestors, can be placed.
        if len(owners) == 1:
            n = owners[0]; actions = n.get('FinishActions', [])
            chain = chains[0]['ancestors']
            safe = (n.get('Type') == 'ChildQuest' and not n.get('FailedCondition') and not n.get('ExitCondition')
                    and chain and all(a['type'] == 'Sequence' for a in chain) and len(actions) == 2)
            if safe:
                first, second = actions
                tr = second.get('Params', {}).get('TransitionOption', {})
                anchor = first.get('Params', {})
                safe = (first.get('Name') == 'PlayFlow' and first.get('Async', False) is False
                        and second.get('Name') == 'TeleportDungeon' and second.get('Async', False) is False
                        and tr.get('Type') == 'CenterText' and set(tr) == {'Type', 'CenterTextFlow'}
                        and references(tr['CenterTextFlow'], key) and all(k in anchor for k in ('FlowListName', 'FlowId', 'StateId')))
                targets = [s for s in backbone['segments'] if safe and s['state_key'] == flow_key(anchor)]
                if (safe and len(targets) == 1 and targets[0]['status'] == 'parsed' and key in states
                        and set(anchor) == {'FlowListName', 'FlowId', 'StateId'}
                        and sum(references(node, flow_key(anchor)) for node in nodes) == 1):
                    raw, fields = flow_actions(states[key]['BinData'])
                    if len(raw) == 1 and raw[0].get('Name') == 'ShowCenterText':
                        p = Exporter(source=source, allow_incomplete=True); p.state_key = key
                        p.actions(raw)
                        rendered = render_result({'title': '', 'route': {'choices': []}, 'events': p.events})
                        proof = {'node_id': n['Id'], 'after_state': flow_key(anchor), 'source_actions': actions,
                                 'basis': 'synchronous flow then same-node teleport transition',
                                 'runtime_verified': False}
                        for event in rendered['events']:
                            event['task_placement'] = proof
                        visible = [e for e in rendered['events'] if e.get('text', '').strip()]
                        targets[0]['events'].extend(visible)
                        targets[0].setdefault('inserted_task_flows', []).append({'state_key': key, 'proof': proof,
                            'source_actions': raw, 'action_fields': fields})
                        targets[0]['missing_text_ids'] = sorted(set(targets[0].get('missing_text_ids', []) + p.missing))
                        review.update(classification='placed_transition_text' if visible else 'placed_empty_transition',
                                      placement_verified=True, proof=proof,
                                      text_evidence=rendered['events'], visible_event_count=len(visible))
        reviews.append(review)
    return reviews
