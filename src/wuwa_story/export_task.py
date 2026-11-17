"""Evidence-backed task routes; unsupported control flow stops export."""
import argparse
import hashlib
import re
from .database import P, O, rows, embedded, texts, json
from .speakers import SpeakerResolver
from .rendering import render_result
from .sequence_calls import head_icon, sequence_call
from .text_refs import option_container, non_dialogue_reason, control_references, phone_media_reference
from .camera_effects import CAMERA_EFFECTS, camera_shape
from .reading_effects import FLOW_LOCK_EFFECTS, flow_lock_shape, ENTITY_LOCK_EFFECTS, entity_lock_shape
from .npc_perform import npc_perform_shape
from .sublevels import switch_shape, switch_evidence
from .screen_effects import screen_stop_shape
from .client_scene_effects import CLIENT_SCENE_EFFECTS, client_scene_shape, client_scene_evidence
from .actor_binding_review import unbound_change_readable, unbound_change_evidence


PRESENTATION_ACTIONS = {'SetPlotMode', 'AwakeEntity', 'HideByRangeInFlow', 'SetFlowTemplate',
                        'FadeOutScreen', 'FadeInScreen', 'DestroyEntity',
                        'ChangeEntityState', 'SetTime', 'PostAkEvent', 'SetPlayerPos',
                        'UnlockSystemItem', 'CameraLookAt', 'SetEntityVisible'}

FLOW_ACTIONS = PRESENTATION_ACTIONS | {'SetWeather', 'Wait', 'FinishDoInteract', 'SetHeadIconVisible', 'BeginFlowTemplate', 'ChangeActorTalker',
                'CloseFlowTemplate', 'ShowTalk', 'JumpTalk', 'FinishTalk', 'ShowCenterText'}


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def flow_key(flow):
    return f'{flow["FlowListName"]}_{flow["FlowId"]}_{flow["StateId"]}'


def flow_restore_shape(action):
    return (action.get('Name') == 'ShowAllHidedGroupInFlow' and action.get('Params', {}) == {}
            and not set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}
            and action.get('Async', False) is False)


def flow_actions(blob):
    candidates = [(i, v) for i, v in embedded(blob) if isinstance(v, list)]
    if not candidates or any(v != candidates[0][1] for _, v in candidates):
        raise ValueError('Ambiguous action array')
    return candidates[0][1], [i for i, _ in candidates]


def choose_option(options, override=None):
    if any(any('condition' in k.lower() for k in o) for o in options):
        raise ValueError('Conditional options require a condition evaluator')
    index = 0 if override is None else override
    if not 0 <= index < len(options):
        raise ValueError('Choice index out of bounds')
    return index


class Exporter:
    def __init__(self, choices=None, source=None, allow_incomplete=False, speaker_records=None, variable_environment=None, capture_control_prefix=False, configured_text_order=False):
        self.allow_incomplete = allow_incomplete
        self.variable_environment = variable_environment
        self.capture_control_prefix = capture_control_prefix
        self.configured_text_order = configured_text_order
        self.unordered_attachments = []
        self.external_content = []
        self.task_ui_texts = []
        self.unverified_content = []
        self.rows = source.rows if source is not None else rows
        self.speakers = SpeakerResolver(records=speaker_records)
        self.choices = choices or {}
        self.events = []
        self.decisions = []
        self.missing = []
        self.action_log = []
        self.talk_coverage = []
        self.talk_groups = {}
        self.used_loop_policy = False

    def export_handbook(self, quest, nodes):
        """Use an explicit recap order, never infer sibling order from node IDs."""
        from .coverage import audit_task
        from .external import TASK_EXTERNAL, inspect_task_content, inspect_node_ui
        task_audit = audit_task(quest, nodes, TASK_EXTERNAL if self.allow_incomplete else frozenset(), reading_projection=self.allow_incomplete)
        if task_audit.get('reading_effects'):
            self.unverified_content.append({'kind': 'world_effects_not_simulated',
                'count': len(task_audit['reading_effects']),
                'note': 'Recap route only; visibility/audio effects on runtime triggers remain unverified'})
        if self.allow_incomplete:
            self.external_content = inspect_task_content(nodes, self.rows)
            for entry in self.external_content:
                entry['quest_id'] = quest['Id']
                if entry['status'] in {'proximity_bubble_read', 'system_board_body_unresolved', 'phone_body_unparsed'}:
                    self.unverified_content.append({'kind': entry['status'], 'node_id': entry['node_id'],
                                                    'note': entry.get('note', 'Referenced content or runtime trigger remains unverified')})
                    self.unverified_content.extend(entry.get('bubble', {}).get('unverified_content', []))
                if entry['status'] in {'gameplay_text_inventory_only', 'variable_assignment_not_executed'}:
                    self.unverified_content.append({'kind': entry['status'], 'node_id': entry['node_id'],
                        'note': 'Configuration evidence only; gameplay values and runtime branch selection not simulated'})
                if entry['status'] in {'mail_body_unavailable_in_row', 'chapter_ui_unverified', 'teleport_transition_unverified', 'phone_flow_read_timing_unverified', 'sublevel_switch_not_simulated'}:
                    self.unverified_content.append({'kind': entry['status'], 'node_id': entry['node_id'],
                                                    'source_action': entry['source_action']})
            self.task_ui_texts = inspect_node_ui(nodes)
            guides = [e for e in self.external_content if e['status'] == 'guide_config_read_display_unverified']
            if guides:
                self.unverified_content.append({'kind': 'guide_content',
                    'guide_ids': sorted({e['guide_id'] for e in guides}),
                    'note': 'Guide text references read; platform selection, input bindings, internal eligibility and runtime display unverified'})
            if self.external_content or self.task_ui_texts:
                self.unverified_content.append({'kind': 'task_ui_and_placement',
                    'note': 'Task text is preserved in an appendix; runtime placement and additional UI content are unverified'})
        matches = [r for r in self.rows('db_PlotHandBook.db', 'plothandbookconfig') if r['QuestId'] == quest['Id']]
        if len(matches) != 1:
            raise ValueError('No unique PlotHandBook order for this quest')
        blob = matches[0]['BinData']
        lists = [v for _, v in embedded(blob) if isinstance(v, list)]
        if len(lists) != 1:
            raise ValueError('Ambiguous handbook entry array')
        entries = lists[0]
        flows = [e['Flow'] for e in entries if e.get('Flow', {}).get('FlowListName')]
        ordered = [flow_key(f) for f in flows]
        references = {flow_key(o) for o in walk([quest, nodes]) if o.get('FlowListName') and 'FlowId' in o}
        direct_references = set(references)
        anchored_insertions = []
        if self.allow_incomplete and references - set(ordered):
            from .recap_order import anchored_finish_flows
            augmented, proofs = anchored_finish_flows(quest, nodes, entries)
            if proofs:
                ordered, anchored_insertions = augmented, proofs
                self.unverified_content.append({'kind': 'anchored_finish_flow', 'proofs': proofs,
                    'note': 'Step completion and exact recap tip anchor; runtime not simulated'})
        from .task_flows import classify_task_flows, bubble_only_extras
        occurrences = classify_task_flows(quest, nodes)
        from .dependencies import dependency_report, read_supplement
        dependencies = dependency_report(quest, nodes, ordered)
        if dependencies['recap_dependency_conflicts']:
            raise ValueError('Recap contradicts explicit same-node completion dependencies')
        parallel_extras = set(dependencies['separate_state_keys']) if self.allow_incomplete else set()
        for key in sorted(parallel_extras):
            detail = read_supplement(key, self.rows)
            relation = next(r for r in dependencies['parallel_relations'] if r['outer_state'] == key)
            self.external_content.append({'status': 'parallel_flow_unordered', 'parallel_flow': detail,
                                          'texts': detail.pop('texts'), 'dependency': relation})
            self.unverified_content.append({'kind': 'parallel_flow_unordered', 'state_key': key,
                                            'note': 'Async sibling flow kept separately; playback order and mandatory status unverified'})
            self.unverified_content.extend(detail['unverified_content'])
        references -= parallel_extras
        bubble_extras = bubble_only_extras(references, ordered, occurrences) if self.allow_incomplete else set()
        if bubble_extras:
            references -= bubble_extras
            self.unverified_content.append({'kind': 'proximity_bubble_supplement',
                'state_keys': sorted(bubble_extras),
                'note': 'Proximity bubble callers only; text retained separately, runtime trigger/timing not verified'})
        levelplay_links = []
        if self.allow_incomplete and references != set(ordered):
            from .recap_links import linked_levelplays, reconcile
            candidates = linked_levelplays(nodes, entries, self.rows)
            if reconcile(references, ordered, candidates):
                levelplay_links = candidates
                references |= {key for link in candidates for key in link['flow_references']}
                self.unverified_content.append({'kind': 'linked_levelplay_runtime',
                    'note': 'Exact recap tip ownership and dungeon map match; LevelPlay actions and runtime are not simulated',
                    'levelplay_ids': [link['levelplay_id'] for link in candidates]})
        entity_links = []
        unplaced_links = []
        if self.allow_incomplete and references != set(ordered):
            from .entity_links import linked_entity_flows
            from .unplaced import completion_only_flows
            candidates = linked_entity_flows(quest, nodes, set(ordered) - references, self.rows)
            pending = references - set(ordered)
            unplaced = completion_only_flows(quest, nodes, pending) if pending else []
            if (references - {l['state_key'] for l in unplaced}) | {l['state_key'] for l in candidates} == set(ordered):
                entity_links, unplaced_links = candidates, unplaced
                references |= {l['state_key'] for l in candidates}
                references -= {l['state_key'] for l in unplaced}
                if candidates:
                    self.unverified_content.append({'kind': 'entity_interactions_recap_order',
                        'note': 'Quest child entities and awake calls prove ownership; interaction timing and mandatory participation are not verified'})
                for link in unplaced:
                    detail = read_supplement(link['state_key'], self.rows)
                    self.external_content.append({'status': 'normal_flow_unplaced', 'unplaced_flow': detail,
                                                  'texts': detail.pop('texts'), 'source_link': link})
                    self.unverified_content.append({'kind': 'normal_flow_unplaced', 'state_key': link['state_key']})
                    self.unverified_content.extend(detail['unverified_content'])
        if not ordered or set(ordered) != references or len(ordered) != len(set(ordered)):
            raise ValueError('Handbook order does not uniquely cover task flow references')
        state_rows = {r['StateKey']: r['BinData'] for r in self.rows('db_flowState.db', 'flowstate') if r['StateKey'] in references}
        if set(state_rows) != references:
            raise ValueError('Missing flow states: ' + repr(sorted(references - set(state_rows))))
        scenes = []
        for number, key in enumerate(ordered, 1):
            self.state_key = key
            # Independent recap scenes must not inherit an anonymous actor binding.
            self.speakers.actors = []
            state_blob = state_rows[key]
            actions, action_fields = flow_actions(state_blob)
            start = len(self.events)
            if self.actions(actions):
                raise ValueError('Unexpected control transfer outside ShowTalk')
            entity_link = next((link for link in entity_links if link['state_key'] == key), None)
            if entity_link:
                for event in self.events[start:]:
                    event['reading_context'] = 'entity_interaction_in_recap_order'
                    event['interaction_entity_id'] = entity_link['entity_id']
            scenes.append({'scene_number': number, 'state_key': key,
                           'equivalent_action_fields': action_fields,
                           'sha256': hashlib.sha256(state_blob).hexdigest(),
                           'event_start': start, 'event_end_exclusive': len(self.events),
                           'task_node_ids': [n['Id'] for n in nodes if any(o.get('FlowListName') and flow_key(o) == key for o in walk(n) if 'FlowId' in o)]})
        for number, event in enumerate(self.events, 1):
            event['sequence'] = number
        return {'schema_version': 2, 'quest_id': quest['Id'], 'title': self.text(quest['TidName']),
                'source': {'database_dir': 'ConfigDB', 'quest_definition': quest, 'task_nodes': nodes,
                           'order_source': {'database': 'db_PlotHandBook.db', 'table': 'plothandbookconfig',
                                            'quest_id': quest['Id'], 'sha256': hashlib.sha256(blob).hexdigest(), 'entries': entries},
                           'scenes': scenes, 'task_audit': task_audit,
                           'recap_reference_resolution': {'direct_references': sorted(direct_references),
                               'anchored_insertions': anchored_insertions,
                               'dependencies': dependencies, 'separate_parallel_references': sorted(parallel_extras),
                               'separate_bubble_references': sorted(bubble_extras), 'flow_occurrences': occurrences,
                               'unplaced_task_flows': unplaced_links, 'linked_entities': entity_links, 'linked_levelplays': levelplay_links, 'expanded_references': sorted(references)}},
                'route': {'policy': 'first_untried_option_on_menu_revisit' if self.used_loop_policy else ('first_unconditional_option' if not self.choices else 'explicit_overrides_else_first'),
                          'choices': self.decisions, 'gender': 'raw_templates_preserved',
                          'gameplay_assumption': 'Prerequisites and task interactions satisfied; recap order, no gameplay simulation'},
                'events': self.events, 'action_trace': self.action_log,
                'validation': {'scope': 'Validated recap flows in configured order; separately decoded supplements remain outside the route',
                               'complete_for_supported_task_shape': not self.missing,
                               'unplaced_flow_count': len(unplaced_links), 'referenced_flow_count': len(references), 'exported_flow_count': len(scenes),
                               'talk_groups': self.talk_coverage,
                               'missing_text_ids': self.missing,
                               'unresolved_anonymous_lines': sum(e.get('identity_status') == 'unresolved' for e in self.events),
                               'limitations': ['Recap order does not prove runtime sibling execution order',
                                               'World effects are logged, not simulated', 'Unselected dialogue routes omitted; decoded task bubbles retained separately',
                                               'No AI identity inference; source templates retained in raw_text']}}

    def text(self, key):
        if key not in texts:
            self.missing.append(key)
            return '[缺失文本：' + str(key) + ']'
        return texts[key]

    def action(self, action):
        name, params = action['Name'], action.get('Params', {})
        self.action_log.append({'state_key': self.state_key, **action})
        evidence = {'state_key': self.state_key, 'action_id': action.get('ActionId'), 'action': name}
        if name == 'SetVar' and self.allow_incomplete and self.variable_environment is not None:
            self.variable_environment.assign(action, evidence)
        elif name == 'PhoneSystemInteract' and self.allow_incomplete:
            from .phone import inspect_open_phone
            phone = inspect_open_phone(action, self.rows, self.choices)
            self.missing.extend(phone['missing_text_ids'])
            self.unverified_content.append({'kind': 'explicit_phone_open', **evidence,
                'source_action': action, 'phone': phone, 'read_completion_verified': False,
                'close_completion_verified': False, 'order_basis': 'explicit_config_call'})
            for event in phone['events']:
                self.events.append({**event, 'parent_state_key': self.state_key,
                    'parent_phone_action': action, 'phone_message_id': phone['message_id']})
            from copy import deepcopy
            for choice in phone['route']['choices']:
                decision = deepcopy(choice)
                for option in decision['options']:
                    option['text'] = option.get('raw_text', option['text'])
                self.decisions.append(decision)
        elif name == 'LeisureInteract' and self.allow_incomplete:
            from .reading_effects import leisure_sit_shape
            if not leisure_sit_shape(action):
                raise ValueError('Unsupported leisure interaction parameters')
            self.unverified_content.append({'kind': 'leisure_pose_call', **evidence,
                'source_action': action, 'runtime_executed': False,
                'pose_completion_verified': False, 'indirect_triggers_verified': False,
                'scene_entity_identity_verified': False})
        elif name == 'Wait':
            if set(params) != {'Time'} or not isinstance(params['Time'], (int, float)) or params['Time'] < 0:
                raise ValueError('Unsupported flow wait')
        elif name == 'StopUiScreenEffect' and self.allow_incomplete:
            if not screen_stop_shape(action):
                raise ValueError('Unsupported screen effect stop parameters')
            self.unverified_content.append({'kind': 'screen_effect_stop', **evidence,
                'source_action': action, 'callbacks_verified': False, 'asset_content_verified': False,
                'note': 'Screen effect stop recorded at source position; visual state and implicit callbacks not simulated'})
        elif name in CLIENT_SCENE_EFFECTS and self.allow_incomplete:
            if not client_scene_shape(action):
                raise ValueError('Unsupported client scene effect parameters: ' + name)
            self.unverified_content.append({**evidence, **client_scene_evidence(action)})
        elif name == 'SwitchSubLevels' and self.allow_incomplete:
            if not switch_shape(action):
                raise ValueError('Unsupported sublevel switch parameters')
            self.unverified_content.append({'kind': 'sublevel_switch', **evidence, **switch_evidence(action)})
        elif name == 'FlowDefineNpcGroupPerform' and self.allow_incomplete:
            if not npc_perform_shape(action):
                raise ValueError('Unsupported NPC group performance parameters')
            self.unverified_content.append({'kind': 'npc_group_performance', **evidence,
                'source_action': action, 'callbacks_verified': False,
                'note': 'Scalar performance call retained in order; implicit callbacks and asset content not simulated'})
            if params['PerformType']['Type'] == 7:
                self.unverified_content[-1].update(
                    enum_semantics_verified=False, runtime_completion_verified=False,
                    asset_content_verified=False, order_scope='explicit_configuration_only')
        elif name in ENTITY_LOCK_EFFECTS and self.allow_incomplete:
            if not entity_lock_shape(action):
                raise ValueError('Unsupported entity lock parameters: ' + name)
            self.unverified_content.append({'kind': 'entity_lock_state', **evidence,
                'source_action': action, 'runtime_executed': False, 'callbacks_verified': False,
                'reachability_verified': False,
                'note': 'Explicit entity IDs recorded in configuration order; interaction availability and indirect triggers not simulated'})
        elif name in FLOW_LOCK_EFFECTS and self.allow_incomplete:
            if not flow_lock_shape(action):
                raise ValueError('Unsupported flow lock parameters: ' + name)
            self.unverified_content.append({'kind': 'world_lock_state', **evidence,
                'source_action': action, 'note': 'Time/weather lock recorded in configuration order; runtime state and indirect triggers not simulated'})
        elif name in CAMERA_EFFECTS and self.allow_incomplete:
            if not camera_shape(action):
                raise ValueError('Unsupported camera effect parameters: ' + name)
            self.unverified_content.append({'kind': 'camera_effect', **evidence,
                'source_action': action, 'note': 'Camera effect retained in call order; timing and runtime effects not simulated'})
            if name == 'PlayerLookAt' and 'PlayAnimation' in params:
                self.unverified_content[-1].update(play_animation=params['PlayAnimation'],
                    animation_playback_verified=False, animation_completion_verified=False)
            if action.get('Timeout', 0) > 0:
                self.unverified_content[-1].update(timeout_seconds=action['Timeout'],
                    deadline_outcome_verified=False, camera_completion_verified=False,
                    order_scope='configuration_text_order_only')
        elif name == 'SetAudioState' and self.allow_incomplete:
            from .reading_effects import flow_audio_state_shape
            if not flow_audio_state_shape(action):
                raise ValueError('Unsupported flow audio state parameters')
            self.unverified_content.append({'kind': 'audio_state_change', **evidence,
                'source_action': action, 'note': 'Audio state recorded in call order; playback and indirect callbacks not simulated'})
        elif name == 'ShowAllHidedGroupInFlow' and self.allow_incomplete:
            if not flow_restore_shape(action):
                raise ValueError('Unsupported flow hidden-group restore parameters')
            self.unverified_content.append({'kind': 'presentation_state_restore', **evidence,
                'source_action': action, 'note': 'Flow hidden-group restore recorded; world visibility and callbacks not simulated'})
        elif name == 'FinishDoInteract':
            if not self.allow_incomplete:
                raise ValueError('Interaction completion callback requires review mode')
            if params: raise ValueError('Unsupported interaction completion')
            self.unverified_content.append({'kind': 'interaction_completion', 'state_key': self.state_key,
                                            'note': 'Completion callback recorded, not executed'})
        elif name == 'SetHeadIconVisible':
            if not head_icon(params):
                raise ValueError('Unsupported head icon visibility parameters')
            # Presentation only: WhoId here never changes speaker identity.
        elif name == 'BeginFlowTemplate':
            self.speakers.begin(params, evidence)
        elif name == 'SetWeather':
            from .coverage import validate_world_effect
            validate_world_effect(name, params)
        elif name == 'ChangeActorTalker':
            if not self.speakers.change(params, evidence):
                if self.allow_incomplete and unbound_change_readable(
                        action, self.speakers.actors, getattr(self, '_active_talk_items', None)):
                    self.unverified_content.append({**evidence, **unbound_change_evidence(action)})
                else:
                    raise ValueError('Actor change has no active binding')
        elif name == 'CloseFlowTemplate':
            self.speakers.actors = []
        elif name == 'ShowTalk':
            previous_items = getattr(self, '_active_talk_items', None)
            previous_show = getattr(self, '_active_show_action', None)
            self._active_talk_items = params['TalkItems']
            self._active_show_action = action
            try:
                if self.allow_incomplete and self.capture_control_prefix:
                    from .pending_boundary import conditional_menu_prefix, PendingDialogueBoundary
                    pending_menu = conditional_menu_prefix(action, texts)
                    if pending_menu:
                        from copy import deepcopy
                        prefix, menu = pending_menu
                        prefix_start = len(self.events)
                        self.talk(prefix)
                        original_items = {item['Id']: item for item in params['TalkItems']}
                        for event in self.events[prefix_start:]:
                            if event.get('state_key') == self.state_key and event.get('talk_id') in original_items:
                                event['source_item'] = deepcopy(original_items[event['talk_id']])
                        raise PendingDialogueBoundary('conditional_menu', action, self.state_key, menu)
                if self.allow_incomplete and self.capture_control_prefix:
                    from .qte_consensus import consensus_projection
                    consensus = consensus_projection(action, texts)
                    if consensus:
                        self.talk(consensus[0])
                        self.unverified_content.append(consensus[1])
                        return
                if self.allow_incomplete and self.configured_text_order:
                    from .qte_text_order import append_configured_qte_text
                    if append_configured_qte_text(self, action):
                        return
                if (self.allow_incomplete and self.capture_control_prefix
                        and action.get('Async', False) is False
                        and not set(action) - {'Name', 'Params', 'ActionId', 'ActionGuid', 'Async'}):
                    from .qte_evidence import linear_qte_prefix, UnresolvedQteBoundary
                    prefix = linear_qte_prefix(params)
                    if prefix is not None:
                        self.talk(prefix)
                        raise UnresolvedQteBoundary(action, self.state_key)
                self.talk(params['TalkItems'], params if action.get('Async', False) is False else None)
            finally:
                self._active_talk_items = previous_items
                self._active_show_action = previous_show
        elif name == 'ShowCenterText':
            key = params['TidCenterText']
            self.events.append({'kind': 'narration', 'state_key': self.state_key,
                                'text_id': key, 'display_name': '画面文字',
                                'raw_text': self.text(key), 'source_action': action})
        elif self.allow_incomplete and name == 'OpenSystemBoard' and params.get('SystemType') == 'TransitionPopup':
            from .transition_panels import inspect_transition
            panel = inspect_transition(action, self.rows)
            panel['parent_state_key'] = self.state_key
            panel['call_anchor']['after_event_count'] = len(self.events)
            self.unordered_attachments.append(panel)
            self.unverified_content.append({'kind': 'async_panel_display_unverified', **evidence,
                'board_id': panel['board_id'], 'display_order_verified': False})
        elif self.allow_incomplete and name == 'OpenSystemBoard' and params.get('SystemType') == 'WriteLetter':
            from .letters import inspect_letter
            letter = inspect_letter(action, self.rows, self.choices)
            self.missing.extend(letter['missing_text_ids'])
            self.unverified_content.append({'kind': 'explicit_letter_open', **evidence,
                'source_action': action, 'letter': letter, 'order_basis': 'explicit_config_call'})
            for event in letter['events']:
                self.events.append({**event, 'parent_state_key': self.state_key,
                    'parent_letter_action': action, 'letter_id': letter['letter_id']})
        elif self.allow_incomplete and name == 'OpenSystemBoard' and params.get('SystemType') == 'ConfirmBox':
            from .confirm_boxes import inspect_confirm_box
            board = inspect_confirm_box(action, self.rows)
            self.unverified_content.append({'kind': 'static_confirmation_panel', **evidence,
                                            'panel': board})
            for value in board['texts']:
                self.events.append({'kind': 'narration', 'state_key': self.state_key,
                    'display_name': '界面文字', **value, 'source_action': action,
                    'panel_source': board['source_table'], 'board_id': board['board_id']})
        elif self.allow_incomplete and ((name == 'PlaySequenceData' and sequence_call(params))
                                       or (name == 'OpenSystemBoard' and set(params) == {'SystemType', 'BoardId'}
                                           and params['SystemType'] == 'InformationView')):
            self.unverified_content.append({'kind': 'unparsed_flow_content', **evidence, 'params': params,
                                            'frame_events_executed': False, 'asset_content_decoded': False,
                                            'note': 'Call position known; asset and frame callbacks not executed; entity-state side effects remain unverified'})
            event = {'kind': 'unparsed_content', 'state_key': self.state_key,
                     'display_name': '待补充', 'source_action': action}
            if name == 'PlaySequenceData':
                from .performance_sources import sequence_source
                source = sequence_source(params['Path'], self.rows)
                event.update(content_channel='sequence_asset', source_resolution=source,
                             raw_text='【演出资产的文本与字幕来源尚未核实】')
                if source.get('media'):
                    event.update(kind='media_reference', media=source['media'])
                    self.missing.extend(source['media'].get('caption_missing_text_ids', []))
            else:
                event.update(content_channel='information_board',
                             raw_text='【信息面板正文尚未解析】')
                from .information_boards import inspect_information
                try:
                    board = inspect_information(params['BoardId'], self.rows)
                    event.update(kind='information_board', display_name='资料面板', information_board=board,
                                 raw_text='\n'.join(v['raw_text'] if v['raw_text'] is not None else '[缺失文本：'+v['text_id']+']' for v in board['texts']))
                    self.missing.extend(board['missing_text_ids'])
                    self.unverified_content[-1].update(kind='information_board_display_timing',
                        note='Exact BoardId and text keys resolved; call order retained, runtime display duration not simulated',
                        body_decoded=not board['missing_text_ids'])
                except (ValueError, KeyError, TypeError) as exc:
                    event['source_resolution_error'] = str(exc)
            self.events.append(event)
        elif name == 'PlayMovie' and self.allow_incomplete:
            from .external import inspect_movie
            movie = inspect_movie(params['VideoName'], self.rows)
            self.missing.extend(movie.get('caption_missing_text_ids', []))
            self.unverified_content.append({'kind': 'media_text', 'video_name': params['VideoName'],
                                            'state_key': self.state_key, 'status': movie['text_coverage'],
                                            'note': movie['note']})
            self.events.append({'kind': 'media_reference', 'state_key': self.state_key,
                                'display_name': '媒体调用', 'raw_text': ('【过场：已提取配置字幕；额外画面文字与实际播放时序尚未核验】' if movie.get('captions') else '【媒体：' + params['VideoName'] + '；是否含额外对白或字幕尚未核验】'),
                                'media': movie, 'source_action': action})
        elif name == 'AccpetCurrentQuest' and self.allow_incomplete:
            if params:
                raise ValueError('Unsupported current quest acceptance parameters')
            self.unverified_content.append({'kind': 'quest_acceptance', 'state_key': self.state_key,
                'source_action': action, 'note': 'Current quest acceptance invocation preserved; runtime activation and callbacks not simulated'})
            self.events.append({'kind': 'quest_control', 'state_key': self.state_key,
                'display_name': '任务控制', 'raw_text': '【接受当前任务；保留调用位置，未模拟运行时激活与回调】',
                'source_action': action})
        elif name == 'JumpTalk':
            return ('jump', params['TalkId'])
        elif name == 'FinishTalk':
            return ('finish', None)
        elif name not in PRESENTATION_ACTIONS:
            if self.allow_incomplete and self.capture_control_prefix:
                from .prefix_boundary import unresolved_control_shape, UnresolvedControlBoundary
                if unresolved_control_shape(action):
                    raise UnresolvedControlBoundary(action, self.state_key)
            raise ValueError('Unsupported action: ' + name)

    def actions(self, actions):
        for action in actions:
            control = self.action(action)
            if control:
                return control

    def talk(self, items, show_params=None):
        positions = {item['Id']: i for i, item in enumerate(items)}
        if len(positions) != len(items):
            raise ValueError('Duplicate talk IDs')
        supported = FLOW_ACTIONS | ({'PlayMovie', 'AccpetCurrentQuest', 'PlaySequenceData', 'OpenSystemBoard', 'ShowAllHidedGroupInFlow', 'SetAudioState'} if self.allow_incomplete else set())
        if self.allow_incomplete:
            if self.variable_environment is not None:
                supported.add('SetVar')
            supported |= CAMERA_EFFECTS
            supported |= CLIENT_SCENE_EFFECTS
            supported |= FLOW_LOCK_EFFECTS
            supported |= ENTITY_LOCK_EFFECTS
            supported.add('FlowDefineNpcGroupPerform')
            supported.add('SwitchSubLevels')
            supported.add('StopUiScreenEffect')
            supported.add('LeisureInteract')
            supported.add('PhoneSystemInteract')
        # QTE outcomes are runtime gates, not freely chosen dialogue responses.
        if any(i.get('Type') == 'QTE' for i in items):
            raise ValueError('QTE runtime outcome evaluator is unsupported')
        # A control on an unselected dialogue path must not block a known path.
        # Its semantics remain unsupported: action() still rejects it if reached.
        deferred_controls = []
        for item in items:
            for obj in walk(item):
                if (self.allow_incomplete and obj.get('Name') in {'SetVar', 'FinishState', 'ChangeState'}
                        and obj['Name'] not in supported and 'Params' in obj):
                    deferred_controls.append({'talk_id': item['Id'], 'source_action': obj})
        from .unconditional_options import preflight_walk, select_option, selection_evidence
        for obj in (preflight_walk(items) if self.allow_incomplete else walk(items)):
            if any('condition' in k.lower() for k in obj):
                raise ValueError('Conditional dialogue requires a condition evaluator')
            if 'Name' in obj and 'Params' in obj:
                if obj['Name'] not in supported:
                    if not (self.allow_incomplete and obj['Name'] in {'SetVar', 'FinishState', 'ChangeState'}):
                        raise ValueError('Unsupported action: ' + obj['Name'])
                if obj['Name'] == 'JumpTalk' and obj['Params']['TalkId'] not in positions:
                    raise ValueError('Missing JumpTalk target')
            for key in ('TidTalk', 'TidTalkOption'):
                if key == 'TidTalk' and (non_dialogue_reason(obj) or phone_media_reference(obj)):
                    continue
                if obj.get(key):
                    self.text(obj[key])
        group = self.talk_groups.get(self.state_key, 0) + 1
        self.talk_groups[self.state_key] = group
        index = 0
        visits = set()
        visited_ids = []
        chosen = {}
        progress = 0
        while index < len(items):
            item = items[index]
            self.current_talk_id = item['Id']
            signature = (index, progress)
            if signature in visits:
                raise ValueError('Dialogue loop has no new option progress')
            visits.add(signature)
            visited_ids.append(item['Id'])
            if any('condition' in k.lower() for k in item):
                raise ValueError('Conditional talk item is unsupported')
            key = item.get('TidTalk')
            if key and not non_dialogue_reason(item):
                visual = phone_media_reference(item)
                event = {'kind': 'dialogue', 'state_key': self.state_key,
                         'talk_group': group,
                         'talk_id': item['Id'], 'text_id': key,
                         **self.speakers.identify(item.get('WhoId')),
                         'raw_text': texts.get(key, '') if visual else self.text(key),
                         'source_item': item}
                if visual:
                    event['phone_media'] = visual
                self.events.append(event)
            # Only inspected combinations may cross the item/option boundary.
            options = item.get('Options', [])
            if options and item.get('Actions'):
                if (self.allow_incomplete and self.capture_control_prefix
                        and isinstance(getattr(self, '_active_show_action', None), dict)
                        and self._active_show_action.get('Async', False) is False
                        and not set(self._active_show_action) - {'Name','Params','ActionId','ActionGuid','Async'}):
                    from .pending_boundary import enrollment_boundary, PendingDialogueBoundary
                    pending_panel = enrollment_boundary(item)
                    if pending_panel:
                        raise PendingDialogueBoundary('enrollment', pending_panel, self.state_key, item)
                from .combined_presentation import combined_hide, combined_actor, evidence as combined_evidence
                safe_combined_hide = self.allow_incomplete and combined_hide(item)
                safe_combined_actor = self.allow_incomplete and combined_actor(item, items, self.speakers.records)
                combined_panel = None
                if (self.allow_incomplete and len(item['Actions']) == 1
                        and item['Actions'][0].get('Name') == 'OpenSystemBoard'
                        and item['Actions'][0].get('Params', {}).get('SystemType') == 'InformationView'):
                    from .combined_information import inspect_combined_information
                    combined_panel = inspect_combined_information(item, show_params, self.rows)
                # Other control/identity/text combinations retain their ordering barrier.
                visual = {'FadeInScreen', 'FadeOutScreen', 'DestroyEntity', 'SetFlowTemplate', 'CameraLookAt'}
                if not (safe_combined_hide or safe_combined_actor or combined_panel) and any(a['Name'] not in visual and not (self.allow_incomplete and a['Name'] == 'SetHeadIconVisible'
                        and head_icon(a.get('Params'))) for a in item['Actions']):
                    raise ValueError('Combined item/option actions need ordering verification')
                if safe_combined_hide:
                    self.unverified_content.append({'state_key': self.state_key,
                        **combined_evidence(item, 'combined_range_visibility')})
                if safe_combined_actor:
                    self.unverified_content.append({'state_key': self.state_key, 'identity_inferred': False,
                        **combined_evidence(item, 'combined_actor_change')})
                if any(a['Name'] == 'SetHeadIconVisible' for a in item['Actions']):
                    self.unverified_content.append({'kind': 'combined_head_icon_presentation',
                        'state_key': self.state_key, 'talk_id': item['Id'],
                        'note': 'Icon visibility does not assign speaker or select dialogue; exact UI timing not verified'})
                if combined_panel:
                    combined_panel['parent_state_key'] = self.state_key
                    combined_panel['call_anchor']['after_event_count'] = len(self.events)
                    self.unordered_attachments.append(combined_panel)
                    self.action_log.append({'state_key': self.state_key, **item['Actions'][0]})
                    self.unverified_content.append({'kind': 'combined_information_display_timing',
                        'state_key': self.state_key, 'talk_id': item['Id'],
                        'display_order_verified': False, 'dialogue_branches_verified': True})
                else:
                    self.actions(item['Actions'])
            if options:
                choice_key = f'{self.state_key}:{item["Id"]}' + (f':group{group}' if group > 1 else '')
                tried = chosen.setdefault(item['Id'], set())
                guarded_menu = self.allow_incomplete and any('PreCondition' in o for o in options)
                if guarded_menu:
                    selected = select_option(options, override=self.choices.get(choice_key) if not tried else None, tried=tried)
                    if tried:
                        self.used_loop_policy = True
                    self.unverified_content.append({**selection_evidence(options), 'state_key': self.state_key,
                        'talk_id': item['Id'], 'choice_key': choice_key, 'selected_index': selected})
                elif tried:
                    self.used_loop_policy = True
                    candidates = [i for i in range(len(options)) if i not in tried]
                    if not candidates:
                        raise ValueError('Dialogue loop exhausted all options without exit')
                    selected = choose_option(options, candidates[0])
                else:
                    selected = choose_option(options, self.choices.get(choice_key))
                tried.add(selected)
                progress += 1
                option = options[selected]
                decision = {'choice_key': choice_key, 'selected_index': selected, 'visit': len(tried),
                            'options': [{'text_id': o.get('TidTalkOption'),
                                         'text': self.text(o.get('TidTalkOption')),
                                         'actions': o.get('Actions', [])} for o in options]}
                if guarded_menu:
                    decision['condition_policy'] = selection_evidence(options)
                    for original, rendered_option in zip(options, decision['options']):
                        if 'PreCondition' in original:
                            rendered_option.update(source_condition=original['PreCondition'], availability='unverified')
                self.decisions.append(decision)
                self.events.append({'kind': 'choice', 'state_key': self.state_key,
                                    'talk_group': group, 'visit': len(tried),
                                    'talk_id': item['Id'], 'display_name': '漂泊者',
                                    'text_id': option.get('TidTalkOption'),
                                    'raw_text': self.text(option.get('TidTalkOption')),
                                    'choice_key': choice_key, 'selected_index': selected})
                control = self.actions(option.get('Actions', []))
            else:
                control = self.actions(item.get('Actions', []))
            if control and control[0] == 'finish':
                break
            if control and control[0] == 'jump':
                if control[1] not in positions:
                    raise ValueError('Missing JumpTalk target')
                index = positions[control[1]]
            else:
                index += 1
        if deferred_controls:
            self.unverified_content.append({'kind': 'unselected_control_actions',
                'state_key': self.state_key, 'talk_group': group, 'controls': deferred_controls,
                'note': 'Unsupported controls were not reached on the selected dialogue path; other routes remain unverified'})
        self.talk_coverage.append({'state_key': self.state_key, 'talk_group': group,
                                   **({'unselected_control_actions': deferred_controls,
                                       'all_branch_actions_verified': False} if deferred_controls else {}),
                                   'non_dialogue_option_containers': [i for i in items if option_container(i)],
                                   'non_dialogue_controls': control_references(items, texts),
                                   'all_talk_ids': list(positions), 'visited_talk_ids': visited_ids,
                                   'unselected_talk_ids': [i for i in positions if i not in visited_ids],
                                   'all_branch_text_and_jump_references_checked': True})

    def export(self, quest_id):
        result = self._export_raw(quest_id)
        if self.allow_incomplete:
            result['external_content'] = self.external_content
            result['unordered_attachments'] = self.unordered_attachments
            result['task_ui_texts'] = self.task_ui_texts
            external_missing = [t['text_id'] for c in self.external_content for t in c.get('texts', []) if t.get('missing')]
            external_missing += [key for c in self.external_content for key in c.get('phone', {}).get('missing_text_ids', [])]
            external_missing += [t['text_id'] for t in self.task_ui_texts if t['missing']]
            missing = sorted(set(result['validation']['missing_text_ids'] + external_missing))
            result['validation'].update(
                coverage_version=2, missing_text_ids=missing,
                confirmed_missing_text_ids=missing,
                known_text_references_complete=not missing,
                unverified_content=self.unverified_content)
            if self.unverified_content or missing:
                result['validation']['complete_for_supported_task_shape'] = False
                result['validation']['status'] = 'needs_review'
        return render_result(result)

    def _export_raw(self, quest_id):
        quest = next(embedded(r['BinData'])[0][1] for r in self.rows('db_QuestData.db', 'questdata')
                     if r['QuestId'] == quest_id)
        nodes = [embedded(r['BinData'])[0][1] for r in self.rows('db_QuestNodeData.db', 'questnodedata')
                 if r['Key'].startswith(str(quest_id) + '_')]
        # Deliberately narrow supported task shape: root Sequence, one gameplay step, success.
        if sorted(n['Type'] for n in nodes) != ['ChildQuest', 'QuestSucceed', 'Sequence']:
            return self.export_handbook(quest, nodes)
        root = next(n for n in nodes if n['Type'] == 'Sequence')
        step = next(n for n in nodes if n['Type'] == 'ChildQuest')
        success = next(n for n in nodes if n['Type'] == 'QuestSucceed')
        if root.get('ParentNodeId') != 0 or any(n.get('ParentNodeId') != root['Id'] for n in [step, success]):
            raise ValueError('Unexpected task topology')
        if any(quest.get(k) for k in ['ActiveActions', 'AcceptActions', 'FinishActions', 'AddInteractOption']):
            raise ValueError('Additional task entry/exit behavior is unsupported')
        if success.get('FinishActions') or success.get('EnterActions'):
            raise ValueError('Additional task success behavior is unsupported')
        if step.get('EnterActions') or step['Condition']['Type'] != 'ReachArea':
            raise ValueError('Unsupported task step')
        actions = step.get('FinishActions', [])
        if len(actions) != 1 or actions[0]['Name'] != 'PlayFlow':
            raise ValueError('Expected one explicit PlayFlow')
        flow = actions[0]['Params']
        self.state_key = f'{flow["FlowListName"]}_{flow["FlowId"]}_{flow["StateId"]}'
        blob = next(r['BinData'] for r in self.rows('db_flowState.db', 'flowstate') if r['StateKey'] == self.state_key)
        lists = [value for _, value in embedded(blob) if isinstance(value, list)]
        if len(lists) != 1:
            raise ValueError('Ambiguous action array')
        if self.actions(lists[0]):
            raise ValueError('Unexpected control transfer outside ShowTalk')
        return {'schema_version': 1, 'quest_id': quest_id, 'title': self.text(quest['TidName']),
                'source': {'database_dir': 'ConfigDB', 'quest_definition': quest,
                           'task_nodes': nodes, 'flow_state': self.state_key,
                           'flow_state_sha256': hashlib.sha256(blob).hexdigest()},
                'route': {'policy': 'first_unconditional_option', 'choices': self.decisions,
                          'gender': 'raw_templates_preserved', 'gameplay_assumption': 'ReachArea completed'},
                'events': self.events, 'action_trace': self.action_log,
                'validation': {'scope': 'selected route of single explicitly referenced flow',
                               'complete_for_supported_task_shape': not self.missing,
                               'missing_text_ids': self.missing,
                               'unresolved_anonymous_lines': sum(e.get('identity_status') == 'unresolved' for e in self.events),
                               'limitations': ['No AI identity inference', 'Unselected branch dialogue omitted',
                                               'Actor continuity is not a universal character identity',
                                               'Not a general game-runtime or all-task exporter']}}


def write_result(result, folder=None, quiet=False):
    folder = folder if folder is not None else O / ('待核验任务' if result['validation'].get('status') == 'needs_review' else '任务样本')
    folder.mkdir(parents=True, exist_ok=True)
    stem = str(result['quest_id']) + '_' + re.sub(r'[<>:"/\\|?*]', '_', result['title'])
    from .mainline_reading import build_mainline_reading, mainline_reading_text
    document = {**result, 'mainline_reading': build_mainline_reading(result)}
    (folder / (stem + '.json')).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / (stem + '.txt')).write_text(mainline_reading_text(document), encoding='utf-8-sig')
    if not quiet:
        if result.get('recap_backbone'):
            b = result['recap_backbone']
            print(stem, 'recap segments:', b['parsed_segments'], 'parsed,', b['blocked_segments'], 'blocked')
        print(stem, len(result['events']), 'validated task-route events',
              {k: v for k, v in result['validation'].items() if k != 'talk_groups'})
    return [folder / (stem + suffix) for suffix in ('.json', '.txt')]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--quest-id', type=int, default=211750002)
    args = parser.parse_args()
    write_result(Exporter().export(args.quest_id))
