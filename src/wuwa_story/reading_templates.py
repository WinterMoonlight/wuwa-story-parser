"""Display dynamic text templates without evaluating game state."""
import re

from .rendering import render_text


TOKEN = re.compile(r'\{([^{}]*)\}')
VARIABLE = re.compile(r'Cus:Var,\s*VarType=(Global|Self)\s+Key=([^\s{}]+)', re.IGNORECASE)
AXIS_LABELS = {'MoveForward': '前后移动', 'MoveRight': '左右移动',
               'LookUp': '上下视角', 'Turn': '左右视角'}
VARIABLE_LABELS = {'main_team_name': '队伍名称'}


def format_templates(text, named_values=None, argument_candidates=None, input_context=False):
    """Use supplied values or explicit readable labels for unresolved fields."""
    named_values = named_values or {}
    argument_candidates = argument_candidates or {}

    def replace(match):
        token = match.group(1)
        if token.isdigit():
            index = int(token)
            labels = []
            for values in argument_candidates.values():
                if index >= len(values):
                    continue
                value = values[index].split('#')[-1]
                label = AXIS_LABELS.get(value, value)
                if label and label not in labels:
                    labels.append(label)
            if labels:
                return '【' + '／'.join(labels) + '】'
            return '【操作键】' if input_context else f'【参数{index + 1}】'
        variable = VARIABLE.fullmatch(token)
        if variable:
            scope, key = variable.groups()
            value = named_values.get((scope.casefold(), key))
            if value is not None:
                return value
            return '【' + VARIABLE_LABELS.get(key, '变量 ' + key) + '】'
        return match.group(0)

    return TOKEN.sub(replace, render_text(text))


def guide_text(value):
    return format_templates(value.get('text', ''),
                            argument_candidates=value.get('format_argument_candidates'),
                            input_context=value.get('source_table') in {'guidetips', 'guidefocusnew', 'guidetutorialpage'})


def update_selected_strings(values, segment):
    """Carry selected string labels within this reading, with source traces intact."""
    from .database import texts
    from .export_task import walk

    for action in walk(segment.get('source_actions', [])):
        if action.get('Name') == 'SetVar':
            target = action.get('Params', {}).get('VarLeft', {})
            key = target.get('Keyword') if target.get('Source') == 'Global' else target.get('Name')
            if key:
                values.pop((target.get('Source', '').casefold(), key), None)
    for evidence in segment.get('unverified_content', []):
        for record in evidence.get('trace', []):
            variable = record.get('variable', {})
            constant = record.get('recorded_constant')
            if (record.get('kind') != 'selected_route_constant_write'
                    or variable.get('Type') != 'String' or variable.get('Source') != 'Global'
                    or not isinstance(constant, str)):
                continue
            key = variable.get('Keyword')
            if key:
                values['global', key] = render_text(texts.get(constant, constant))
