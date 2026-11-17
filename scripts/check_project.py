"""Check Python syntax and repository Markdown links without loading game data."""
import ast
from pathlib import Path
import re
from urllib.parse import unquote


def check_project(root):
    errors = []
    python_files = [root/'run.py']
    for directory in ('src','tests','scripts'):
        python_files.extend((root/directory).rglob('*.py'))
    for path in python_files:
        try:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        except (SyntaxError, UnicodeError) as exc:
            errors.append(f'{path.relative_to(root)}: {exc}')
    markdown_files = list(root.glob('*.md')) + list((root/'docs').rglob('*.md'))
    pattern = re.compile(r'\]\(<?([^\s)>]+)>?\)')
    for path in markdown_files:
        for target in pattern.findall(path.read_text(encoding='utf-8-sig')):
            if '://' in target or target.startswith('#'):
                continue
            relative = unquote(target.split('#',1)[0])
            resolved = (path.parent/relative).resolve()
            if resolved.exists():
                continue
            try:
                parts = resolved.relative_to(root).parts
            except ValueError:
                continue
            if parts and parts[0] in {'outputs','work','ConfigDB','.codex'}:
                continue
            errors.append(f'{path.relative_to(root)}: missing link {relative}')
    return errors, len(python_files), len(markdown_files)


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    errors, python_count, markdown_count = check_project(root)
    for error in errors:
        print(error)
    print(f'Checked {python_count} Python files and {markdown_count} Markdown files')
    raise SystemExit(bool(errors))
