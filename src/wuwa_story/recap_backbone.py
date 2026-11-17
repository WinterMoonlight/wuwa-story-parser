"""Independent recap segments: preserve explicit order without claiming task execution."""
import hashlib
from .database import embedded
from .export_task import Exporter, flow_key, flow_actions, walk
from .rendering import render_result
from .prefix_boundary import UnresolvedControlBoundary
from .qte_evidence import UnresolvedQteBoundary
from .pending_boundary import PendingDialogueBoundary


def build_backbone(quest_id, handbook_rows, states, source, choices=None):
    if len(handbook_rows) != 1:
        return None
    row = handbook_rows[0]
    arrays = [v for _, v in embedded(row['BinData']) if isinstance(v, list)]
    if len(arrays) != 1:
        return None
    entries = arrays[0]
    flows = [(i, e) for i, e in enumerate(entries) if e.get('Flow', {}).get('FlowListName')]
    if not flows:
        return None
    from .speakers import SpeakerResolver
    names = getattr(source, '_recap_speaker_records', None)
    if names is None:
        names = SpeakerResolver().records
        if source is not None:
            source._recap_speaker_records = names
    segments = []
    for i, entry in flows:
        key = flow_key(entry['Flow'])
        segment = {'entry_index': i, 'state_key': key, 'source_entry': entry,
                   'status': 'blocked', 'events': []}
        try:
            if key not in states:
                raise ValueError('Missing flow state')
            blob = states[key]['BinData']
            segment['sha256'] = hashlib.sha256(blob).hexdigest()
            actions, fields = flow_actions(blob)
            segment.update(source_actions=actions, equivalent_action_fields=fields)
            from .text_order import deferred_sequence
            deferred_media = deferred_sequence(actions, key)
            from .terminal_text import project_terminal_text
            terminal_projection = project_terminal_text(actions)
            parse_actions = actions[:-1] if deferred_media else terminal_projection[0] if terminal_projection else actions
            # Each occurrence gets a fresh parser: no leaked actor, option, or partial state.
            from .write_only_recap import write_only_environment
            local_env = write_only_environment(actions, f'recap:{quest_id}:{i}:{key}')
            if local_env is None:
                from .constant_writes import constant_write_recorder
                local_env = constant_write_recorder(actions, f'recap:{quest_id}:{i}:{key}')
                if (local_env is None and any(o.get('Name') == 'SetVar' for o in walk(actions))
                        and any(isinstance(o.get('Options'), list) and any(isinstance(v, dict) and 'PreCondition' in v for v in o['Options']) for o in walk(actions))):
                    from .unconditional_options import write_audit_projection
                    local_env = constant_write_recorder(write_audit_projection(actions), f'recap:{quest_id}:{i}:{key}')
            parser = Exporter(source=source, allow_incomplete=True, speaker_records=names, choices=choices,
                              variable_environment=local_env, capture_control_prefix=True, configured_text_order=True)
            parser.state_key = key
            if parser.actions(parse_actions):
                raise ValueError('Unexpected control outside dialogue')
            if deferred_media:
                parser.events.append({'kind': 'media_reference', 'state_key': key,
                    'raw_text': '【演出内容后置】', 'source_action': actions[-1], 'content_deferred': True})
                parser.unverified_content.append(deferred_media)
            if terminal_projection:
                from copy import deepcopy
                original_items = {item['Id']: item for item in actions[-1]['Params']['TalkItems']}
                for event in parser.events:
                    if event.get('kind') == 'dialogue' and event.get('talk_id') in original_items:
                        event['source_item'] = deepcopy(original_items[event['talk_id']])
                visited = {talk_id for group in parser.talk_coverage for talk_id in group['visited_talk_ids']}
                terminal_evidence = terminal_projection[1]
                terminal_evidence['selected_terminal_ids'] = [entry['talk_id'] for entry in terminal_evidence['terminal_controls']
                                                            if entry['talk_id'] in visited]
                parser.unverified_content.append(terminal_evidence)
            if local_env is not None:
                record_only = getattr(local_env, 'record_only', False)
                parser.unverified_content.append({'kind': ('isolated_constant_write_audit' if record_only else 'isolated_write_only_variables'),
                    'scope_id': local_env.self_scope, 'trace': local_env.trace,
                    ('recorded_writes' if record_only else 'final_values'): local_env.snapshot(),
                    'no_cross_segment_propagation': True,
                    'runtime_executed': False, 'downstream_effects_verified': False,
                    'note': ('Audit selected constant writes only; no runtime variable environment or cross-segment propagation'
                             if record_only else 'Record selected constant Self writes only; no conditions or state transfers in this segment')})
            rendered = render_result({'title': '', 'route': {'choices': parser.decisions},
                                      'events': parser.events})
            segment.update(status='parsed', events=rendered['events'],
                           route=rendered['route'], action_trace=parser.action_log,
                           talk_groups=parser.talk_coverage,
                           unverified_content=parser.unverified_content,
                           unordered_attachments=getattr(parser, 'unordered_attachments', []),
                           missing_text_ids=sorted(set(parser.missing)))
        except (UnresolvedControlBoundary, UnresolvedQteBoundary, PendingDialogueBoundary) as exc:
            from .viable_choice import retry_unconditional_choice
            alternative = None
            if isinstance(exc, PendingDialogueBoundary) and exc.kind == 'conditional_menu':
                from .conditional_route import conditional_text_route
                alternative = conditional_text_route(actions, key, source, names, choices)
            elif isinstance(exc, PendingDialogueBoundary) and exc.kind == 'enrollment':
                from .pending_boundary import enrollment_return_route
                alternative = enrollment_return_route(actions, exc, source, names, choices)
            if alternative is None:
                alternative = retry_unconditional_choice(actions, parser, exc, source, names, choices)
            if alternative is not None:
                rendered = render_result({'title': '', 'route': {'choices': alternative.decisions},
                                          'events': alternative.events})
                conditional = any(e.get('kind') == 'conditional_text_route' for e in alternative.unverified_content)
                panel_return = any(e.get('kind') == 'panel_return_text_route' for e in alternative.unverified_content)
                rendered['route']['policy'] = ('configured_panel_return_text_route' if panel_return else
                                               'first_satisfiable_conditional_text_route' if conditional else
                                               'first_fully_parsed_unconditional_alternative')
                segment.update(status='parsed', events=rendered['events'], route=rendered['route'],
                               action_trace=alternative.action_log, talk_groups=alternative.talk_coverage,
                               unverified_content=alternative.unverified_content,
                               unordered_attachments=alternative.unordered_attachments, missing_text_ids=[])
                segments.append(segment)
                continue
            # Only an explicit reached control may preserve a prefix. Ordinary
            # parse failures below remain transactional and discard partial text.
            rendered = render_result({'title': '', 'route': {'choices': parser.decisions}, 'events': parser.events})
            from .terminal_text import last_item_terminal_evidence
            terminal_end = last_item_terminal_evidence(actions, exc, getattr(parser, 'current_talk_id', None))
            if terminal_end:
                segment.update(status='parsed', events=rendered['events'], route=rendered['route'],
                               action_trace=parser.action_log, talk_groups=parser.talk_coverage,
                               unverified_content=parser.unverified_content + [terminal_end],
                               missing_text_ids=sorted(set(parser.missing)))
                segments.append(segment)
                continue
            segment.update(error=str(exc), events=rendered['events'], route=rendered['route'],
                prefix_event_count=len(rendered['events']), control_boundary=exc.as_dict(),
                action_trace=parser.action_log, unverified_content=parser.unverified_content,
                unordered_attachments=getattr(parser, 'unordered_attachments', []),
                missing_text_ids=sorted(set(parser.missing)))
            message = ('【此处的快速反应操作及后续流程仍待核验】' if isinstance(exc, UnresolvedQteBoundary)
                       else '【此处遇到尚未解析的控制动作；本段后续流程仍待核验】')
            if isinstance(exc, PendingDialogueBoundary):
                message = ('【此处选项的可用条件尚未确认，后续分支仍待核验】' if exc.kind == 'conditional_menu'
                           else '【此处打开入学界面，界面正文及返回后的流程仍待核验】')
            segment['events'].append({'kind':'recap_gap','display_name':'缺口', 'text':message,'state_key':key})
            if isinstance(exc, PendingDialogueBoundary) and exc.kind == 'enrollment':
                from .pending_boundary import enrollment_fragment
                fragment = enrollment_fragment(actions, exc, source, names, choices, segment['prefix_event_count'])
                if fragment:
                    segment['local_fragments'] = [fragment]
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            segment['error'] = str(exc)
            segment['events'] = [{'kind': 'recap_gap', 'display_name': '缺口',
                                  'text': f'【回顾第{len(segments)+1}段暂未解析，后续正文继续】',
                                  'state_key': key}]
        segments.append(segment)
    if not any(s['status'] == 'parsed' and s['events'] for s in segments):
        return None
    return {'quest_id': quest_id, 'status': 'recap_draft',
            'order_source': {'database': 'db_PlotHandBook.db', 'table': 'plothandbookconfig',
                             'sha256': hashlib.sha256(row['BinData']).hexdigest(), 'entries': entries},
            'segments': segments,
            'parsed_segments': sum(s['status'] == 'parsed' for s in segments),
            'blocked_segments': sum(s['status'] == 'blocked' for s in segments),
            'task_order_verified': False, 'accepted': False}


def duplicate_text_flows(inventories, recap_keys, states):
    """Only fold extra-source text; never collapse repeated recap occurrences."""
    groups = {}
    duplicates = []
    for key in sorted(inventories, key=lambda k: (k not in recap_keys, k)):
        records = inventories[key]
        # Match full ordered text inventory including IDs, types and speakers, not fuzzy prose.
        signature = tuple((r['text_id'], r['raw_text'], r.get('kind'), r.get('who_id')) for r in records)
        if not signature or not any(r.get('text') for r in records):
            continue
        if signature in groups and key not in recap_keys:
            canonical = groups[signature]
            a, _ = flow_actions(states[canonical]['BinData'])
            b, _ = flow_actions(states[key]['BinData'])
            duplicates.append({'state_key': key, 'text_duplicate_of': canonical,
                               'text_occurrences': len(records), 'actions_equal': a == b,
                               'source_sha256': hashlib.sha256(states[key]['BinData']).hexdigest(),
                               'canonical_sha256': hashlib.sha256(states[canonical]['BinData']).hexdigest(),
                               'runtime_equivalence_verified': False})
        else:
            groups.setdefault(signature, key)
    return duplicates


def export_task_backbone(quest_id, choices=None):
    from .batch import Snapshot
    from .reading_batch import analyze
    source = Snapshot()
    quest = next(embedded(r['BinData'])[0][1] for r in source.rows('db_QuestData.db', 'questdata')
                 if r['QuestId'] == quest_id)
    nodes = [embedded(r['BinData'])[0][1] for r in source.rows('db_QuestNodeData.db', 'questnodedata')
             if r['Key'].startswith(str(quest_id) + '_')]
    books = {quest_id: [r for r in source.rows('db_PlotHandBook.db', 'plothandbookconfig')
                       if r['QuestId'] == quest_id]}
    states = {r['StateKey']: r for r in source.rows('db_flowState.db', 'flowstate')}
    # This entry point does not run the strict audit; do not claim a strict success.
    return analyze(quest, nodes, states, books, source, {'status': 'not_checked'}, choices=choices)


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    from .export_task import write_result
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--quest-id', type=int, required=True)
    parser.add_argument('--output', type=Path, default=Path('outputs/回顾主干验证'))
    parser.add_argument('--choices', type=Path, help='JSON mapping of choice keys to selected indices')
    args = parser.parse_args()
    import json
    choices = json.loads(args.choices.read_text(encoding='utf-8-sig')) if args.choices else None
    write_result(export_task_backbone(args.quest_id, choices), args.output)
