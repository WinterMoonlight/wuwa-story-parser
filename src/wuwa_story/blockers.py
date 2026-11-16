"""All observed task-action blockers plus first-error movement between batches."""
from collections import Counter
import argparse
import json
from pathlib import Path

from .coverage import TASK_EFFECTS, validate_world_effect
from .external import TASK_EXTERNAL
from .export_task import walk
from .reading_effects import READING_EFFECTS, validate_reading_effect, effect_evidence


def assess_actions(quest, nodes):
    issues, effects = [], []
    for owner, value in [('quest', quest)] + [(n['Id'], n) for n in nodes]:
        for obj in walk(value):
            if not {'Name', 'Params'} <= set(obj):
                continue
            name, params = obj['Name'], obj['Params']
            try:
                if name in READING_EFFECTS:
                    validate_reading_effect(name, params)
                    effects.append({'owner': owner, 'action_id': obj.get('ActionId'),
                                    **effect_evidence(name, params)})
                else:
                    validate_world_effect(name, params)
                    if name not in TASK_EFFECTS | TASK_EXTERNAL | {'PlayFlow'}:
                        raise ValueError('Unsupported task action: ' + str(name))
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                issues.append({'owner': owner, 'name': name, 'params': params,
                               'action_id': obj.get('ActionId'), 'reason': str(exc)})
    return {'scope': 'All task action occurrences; not external payload decoding or flow execution',
            'issues': issues, 'reading_effects': effects}


def first_error(task):
    return next((g['detail'] for g in task['gaps'] if g['kind'] == 'route_blocked'), None)


def compare(before, after):
    old = {t['quest_id']: t for t in before['tasks']}
    changes = [{'quest_id': t['quest_id'], 'title': t['title'],
                'before_status': old[t['quest_id']]['status'], 'after_status': t['status'],
                'before_error': first_error(old[t['quest_id']]), 'after_error': first_error(t)}
               for t in after['tasks'] if first_error(old[t['quest_id']]) != first_error(t)
               or old[t['quest_id']]['status'] != t['status']]
    return {'before_summary': before['summary'], 'after_summary': after['summary'],
            'first_error_changes': changes,
            'new_ordered_tasks': [c for c in changes if c['before_status'] != 'selected_route' and c['after_status'] == 'selected_route'],
            'new_partial_tasks': [c for c in changes if c['before_status'] != 'partial_order' and c['after_status'] == 'partial_order'],
            'lost_ordered_tasks': [c for c in changes if c['before_status'] == 'selected_route' and c['after_status'] != 'selected_route'],
            'all_task_action_blockers': dict(Counter(name for t in after['tasks'] for name in {
                i['name'] for i in t.get('task_action_assessment', {}).get('issues', [])})),
            'note': 'Counts are affected tasks, not additive gains; first-error movement is not task success'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('before', type=Path)
    parser.add_argument('after', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = compare(json.loads(args.before.read_text(encoding='utf-8')),
                     json.loads(args.after.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('New ordered:', len(result['new_ordered_tasks']), 'lost:', len(result['lost_ordered_tasks']),
          'first error changes:', len(result['first_error_changes']))
