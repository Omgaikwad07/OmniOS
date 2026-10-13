"""
tests/test_app.py
=================
Tests for the app.py CLI entry point.

All application launches and browser openings are mocked.
No real processes are started and no network calls are made.
"""

import unittest
from io import StringIO
from unittest.mock import MagicMock, patch


class TestAppRun(unittest.TestCase):

    def _run(self, commands: list[str]) -> str:
        """Feed commands into app.run() and capture stdout."""
        inputs = iter(commands)
        with patch("builtins.input", side_effect=inputs), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            from app import run
            run()
            return mock_out.getvalue()

    def test_exit_command_stops_loop(self):
        out = self._run(["exit"])
        self.assertIn("Goodbye", out)

    def test_quit_command_stops_loop(self):
        out = self._run(["quit"])
        self.assertIn("Goodbye", out)

    def test_eof_stops_loop(self):
        with patch("builtins.input", side_effect=EOFError), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            from app import run
            run()
            self.assertIn("Goodbye", mock_out.getvalue())

    def test_empty_input_ignored(self):
        out = self._run(["", "   ", "exit"])
        self.assertIn("Goodbye", out)
        # No separator printed for blank lines
        self.assertEqual(out.count("Intent"), 0)

    def test_calculate_local_action(self):
        out = self._run(["calculate 2 + 3", "exit"])
        self.assertIn("CALCULATE", out)
        self.assertIn("LOCAL", out)
        self.assertIn("SUCCESS", out)
        self.assertIn("5", out)

    @patch("actions.apps.subprocess.Popen")
    def test_open_app_local_action(self, mock_popen):
        mock_popen.return_value = MagicMock()
        out = self._run(["open notepad", "exit"])
        self.assertIn("OPEN_APP", out)
        self.assertIn("SUCCESS", out)

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_open_url_local_action(self, _):
        out = self._run(["open https://example.com", "exit"])
        self.assertIn("OPEN_URL", out)
        self.assertIn("SUCCESS", out)

    def test_llm_task_not_executed(self):
        out = self._run(["summarize my notes", "exit"])
        self.assertIn("LLM", out)
        self.assertIn("not yet implemented", out)
        # Must not claim SUCCESS
        self.assertNotIn("SUCCESS", out)

    def test_unknown_command_handled_gracefully(self):
        out = self._run(["xyzzy frobulate the quux", "exit"])
        self.assertIn("NONE", out)
        self.assertNotIn("SUCCESS", out)


if __name__ == "__main__":
    unittest.main()
