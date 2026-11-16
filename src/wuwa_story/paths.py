"""All relative paths are anchored to the project, never the shell working directory."""
import os
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get('WUWA_PROJECT_ROOT', Path(__file__).resolve().parents[2])).resolve()


def configured_path(variable, default):
    path = Path(os.environ.get(variable, default)).expanduser()
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


DATABASE_DIR = configured_path('WUWA_CONFIG_DB', 'ConfigDB')
WORK_DIR = configured_path('WUWA_WORK_DIR', 'work')
OUTPUT_DIR = configured_path('WUWA_OUTPUT_DIR', 'outputs')
