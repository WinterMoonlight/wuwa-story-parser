"""Render the configured female Rover reading edition without altering evidence."""
import re


TOKEN = re.compile(r'\{([^{}]*)\}')


def render_text(text):
    def replace(match):
        token = match.group(1)
        if token.casefold() == 'playername':
            return '漂泊者'
        if token == 'TA':
            return '她'
        fields = token.split(';')
        pairs = [field.partition('=') for field in fields]
        if (len(pairs) == 2 and all(p[1] for p in pairs)
                and {p[0].strip().casefold() for p in pairs} == {'male', 'female'}):
            return next(p[2] for p in pairs if p[0].strip().casefold() == 'female')
        return match.group(0)
    # Inner tokens (e.g. PlayerName inside a gender branch) resolve first.
    while True:
        rendered = TOKEN.sub(replace, text)
        if rendered == text:
            return rendered
        text = rendered


def render_result(result):
    result['rendering'] = {'version': 1, 'player_name': '漂泊者', 'gender': 'female',
                           'unknown_tokens': 'preserved'}
    result['route']['gender'] = 'female'
    result['route']['player_name'] = '漂泊者'
    result['raw_title'] = result['title']
    result['title'] = render_text(result['title'])
    for value in result.get('task_ui_texts', []):
        value['text'] = render_text(value['raw_text']) if value['raw_text'] is not None else '[缺失文本]'
    for entry in result.get('external_content', []):
        for value in entry.get('texts', []):
            value['text'] = render_text(value['raw_text']) if value['raw_text'] is not None else '[缺失文本]'
    for event in result['events']:
        event['text'] = render_text(event['raw_text'])
        for field in ('display_name', 'resolved_name'):
            if event.get(field):
                event['raw_' + field] = event[field]
                event[field] = render_text(event[field])
    for decision in result['route']['choices']:
        for option in decision['options']:
            option['raw_text'] = option['text']
            option['text'] = render_text(option['raw_text'])
    return result
