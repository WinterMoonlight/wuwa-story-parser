"""Run without installing: python run.py export-task --quest-id 211750002."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from wuwa_story.cli import main

if __name__ == '__main__':
    main()
