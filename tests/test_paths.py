import unittest
from unittest.mock import patch
from wuwa_story.paths import configured_path, PROJECT_ROOT


class PathTests(unittest.TestCase):
    def test_relative_path_is_project_relative(self):
        with patch.dict('os.environ', {'WUWA_TEST_PATH': 'data/example'}):
            self.assertEqual(configured_path('WUWA_TEST_PATH', 'ignored'), (PROJECT_ROOT / 'data/example').resolve())

    def test_absolute_override_is_preserved(self):
        value = str((PROJECT_ROOT / 'alternate').resolve())
        with patch.dict('os.environ', {'WUWA_TEST_PATH': value}):
            self.assertEqual(str(configured_path('WUWA_TEST_PATH', 'ignored')), value)
