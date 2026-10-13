"""
tests/test_end_to_end.py
========================
Integration tests: natural-language input → router → registry → result.

These tests verify that Person 1's router and Person 2's action layer
work together correctly through the full LOCAL execution path.  No
applications are actually launched, no browser windows are opened, and
no LLM calls are made.
"""

import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import core.config as cfg
from actions.registry import execute
from core.schemas import ResultStatus, Route, TaskRequest
from router.task_router import route


class TestRouterToRegistry(unittest.TestCase):
    """Route a natural-language request then execute via the registry."""

    # --- open_app ---

    @patch("actions.apps.subprocess.Popen")
    def test_open_notepad_end_to_end(self, mock_popen):
        mock_popen.return_value = MagicMock()
        decision = route(TaskRequest(raw_input="open Notepad"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertFalse(r.used_llm)

    @patch("actions.apps.subprocess.Popen")
    def test_launch_calculator_end_to_end(self, mock_popen):
        mock_popen.return_value = MagicMock()
        decision = route(TaskRequest(raw_input="start Calculator"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    # --- open_url ---

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_open_url_end_to_end(self, _):
        decision = route(TaskRequest(raw_input="open https://github.com"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertFalse(r.used_llm)

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_open_google_website_end_to_end(self, _):
        decision = route(TaskRequest(raw_input="open Google website"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    # --- calculate ---

    def test_calculate_end_to_end(self):
        decision = route(TaskRequest(raw_input="calculate 10 + 5"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 15)
        self.assertFalse(r.used_llm)

    def test_calculate_precedence_end_to_end(self):
        decision = route(TaskRequest(raw_input="perform 5 + 5 x 10 - 20"))
        self.assertEqual(decision.route, Route.LOCAL)
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 35)

    def test_calculate_spoken_times_end_to_end(self):
        decision = route(TaskRequest(raw_input="calculate 5 times 10"))
        r = execute(decision.action_name, decision.validated_args)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 50)

    # --- file_search ---

    def test_file_search_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "report.pdf").touch()
            orig = cfg.FILE_SEARCH_ROOT
            cfg.FILE_SEARCH_ROOT = tmp
            try:
                decision = route(TaskRequest(raw_input="find report.pdf on my computer"))
                self.assertEqual(decision.route, Route.LOCAL)
                r = execute(decision.action_name, decision.validated_args)
                self.assertEqual(r.status, ResultStatus.SUCCESS)
                self.assertTrue(any("report.pdf" in p for p in r.output))
                self.assertFalse(r.used_llm)
            finally:
                cfg.FILE_SEARCH_ROOT = orig

    # --- LLM route never reaches registry ---

    def test_llm_task_not_dispatched_locally(self):
        """LLM tasks must not be routed to the local registry."""
        decision = route(TaskRequest(raw_input="summarize the meeting notes"))
        self.assertEqual(decision.route, Route.LLM)
        self.assertIsNone(decision.action_name)
        # Attempting to execute with None action_name returns ERROR, not a crash.
        r = execute(decision.action_name or "", decision.validated_args or {})
        self.assertEqual(r.status, ResultStatus.ERROR)

    # --- Router contract fields ---

    def test_routing_decision_has_all_fields(self):
        decision = route(TaskRequest(raw_input="calculate 1 + 1"))
        self.assertIsNotNone(decision.intent)
        self.assertIsNotNone(decision.route)
        self.assertIsNotNone(decision.action_name)
        self.assertIsNotNone(decision.validated_args)
        self.assertIsInstance(decision.explanation, str)
        self.assertGreater(decision.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
