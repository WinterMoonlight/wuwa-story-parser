import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from wuwa_story.cli import main


class CliTests(unittest.TestCase):
    def test_help_lists_reading_commands(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(['--help'])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn('export-review', output.getvalue())
        self.assertIn('export-recap', output.getvalue())

    def test_review_requires_all_paths(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            main(['export-review'])
        self.assertEqual(raised.exception.code, 2)

    def test_review_dispatch_preserves_paths(self):
        with patch('wuwa_story.reading_review.export_review') as export:
            main(['export-review','--batch','batch','--review','review.json','--output','out'])
        export.assert_called_once_with(Path('batch'),Path('review.json'),Path('out'))
