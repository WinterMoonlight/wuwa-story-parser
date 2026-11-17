"""Render inspected game markup for plain-text reading exports."""
import re


COLOR_PAIR = re.compile(r'<color=(?:Highlight|#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?)>([^<>]*)</color>')
ANNOTATION_PAIR = re.compile(r'<ano=([^<>\r\n]+)>([^<>]*)</ano>')


def reading_markup(text):
    """Keep annotation wording and unknown syntax while removing known styling.

    Innermost balanced pairs are handled first. Unknown nested tags prevent an
    enclosing pair from matching, so malformed or unfamiliar markup survives.
    Dynamic placeholders remain available for later runtime verification.
    """
    while True:
        rendered = COLOR_PAIR.sub(lambda match: match.group(1), text)
        rendered = ANNOTATION_PAIR.sub(
            lambda match: match.group(2) + '〔' + match.group(1) + '〕', rendered)
        if rendered == text:
            return rendered
        text = rendered
