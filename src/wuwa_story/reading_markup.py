"""Remove presentation tags from plain-text reading exports."""
import re


TAG = re.compile(r'''</?[A-Za-z][\w:-]*(?=[\s=/>])(?:"[^"\r\n]*"|'[^'\r\n]*'|[^'"<>])*?>''')
ANNOTATION_TAG = re.compile(r'</?ano(?=[=>\s])', re.IGNORECASE)
ANNOTATION_PAIR = re.compile(r'<ano=([^<>\r\n]+)>([^<>]*)</ano>', re.IGNORECASE)
LINE_BREAK = re.compile(r'<br\s*/?>', re.IGNORECASE)


def reading_markup(text):
    """Keep visible wording, annotation glosses and explicit line breaks."""
    text = LINE_BREAK.sub('\n', text)
    # Keep annotation pairs until their glosses have been converted to text.
    text = TAG.sub(lambda match: match[0] if ANNOTATION_TAG.match(match[0]) else '', text)
    while True:
        rendered = ANNOTATION_PAIR.sub(
            lambda match: match.group(2) + '〔' + match.group(1) + '〕', text)
        if rendered == text:
            return TAG.sub('', rendered)
        text = rendered
