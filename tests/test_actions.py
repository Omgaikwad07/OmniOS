"""
tests/test_actions.py
=====================
Unit tests for the Windows Action Layer (Person 2 scope).

All tests are deterministic — no applications are actually launched,
no browser windows are opened, and no real filesystem paths outside
temporary directories are accessed.
"""

import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import core.config as cfg
from actions.apps import open_app
from actions.calculator import calculate
from actions.file_search import file_search
from actions.registry import execute
from actions.urls import open_url
from core.schemas import ResultStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _TempDirMixin:
    """Creates a temporary directory scoped to each test and patches
    FILE_SEARCH_ROOT so file_search never touches real user files."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._orig_root = cfg.FILE_SEARCH_ROOT
        cfg.FILE_SEARCH_ROOT = self._tmp

    def tearDown(self):
        cfg.FILE_SEARCH_ROOT = self._orig_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _touch(self, *rel_parts):
        p = pathlib.Path(self._tmp, *rel_parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        return str(p)


# ===========================================================================
# 1 & 2 — Application launcher
# ===========================================================================

class TestOpenApp(unittest.TestCase):

    @patch("actions.apps.subprocess.Popen")
    def test_launch_notepad_success(self, mock_popen):
        """Approved app returns SUCCESS and does not raise."""
        mock_popen.return_value = MagicMock()
        r = open_app("Notepad")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertIn("Notepad", r.output)
        mock_popen.assert_called_once()

    @patch("actions.apps.subprocess.Popen")
    def test_launch_calculator_success(self, mock_popen):
        mock_popen.return_value = MagicMock()
        r = open_app("calculator")
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.apps.subprocess.Popen")
    def test_launch_case_insensitive(self, mock_popen):
        """App name matching is case-insensitive."""
        mock_popen.return_value = MagicMock()
        r = open_app("NOTEPAD")
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    def test_unsupported_app_refused(self):
        r = open_app("Chrome")
        self.assertEqual(r.status, ResultStatus.REFUSED)
        self.assertIn("Chrome", r.error)

    def test_unsupported_app_lists_supported(self):
        r = open_app("VLC")
        self.assertIn("calculator", r.error.lower())

    def test_empty_app_name_error(self):
        r = open_app("")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_non_string_app_name_error(self):
        r = open_app(None)
        self.assertEqual(r.status, ResultStatus.ERROR)

    @patch("actions.apps.subprocess.Popen", side_effect=FileNotFoundError)
    def test_exe_not_found_returns_error(self, _):
        """If the exe is missing on this Windows edition, return ERROR."""
        r = open_app("notepad")
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("not found", r.error.lower())

    @patch("actions.apps.subprocess.Popen", side_effect=OSError("access denied"))
    def test_os_error_returns_error(self, _):
        r = open_app("notepad")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_result_used_llm_false(self):
        r = open_app("UnknownApp")
        self.assertFalse(r.used_llm)


# ===========================================================================
# 3 & 4 — URL opener
# ===========================================================================

class TestOpenUrl(unittest.TestCase):

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_https_url_success(self, mock_wb):
        r = open_url("https://example.com")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        mock_wb.assert_called_once_with("https://example.com")

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_http_url_success(self, mock_wb):
        r = open_url("http://example.com")
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_url_with_path_and_query(self, mock_wb):
        r = open_url("https://example.com/search?q=hello")
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    def test_file_scheme_refused(self):
        r = open_url("file:///C:/Windows/win.ini")
        self.assertEqual(r.status, ResultStatus.REFUSED)
        self.assertIn("file", r.error.lower())

    def test_javascript_scheme_refused(self):
        r = open_url("javascript:alert(1)")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_data_scheme_refused(self):
        r = open_url("data:text/html,<h1>x</h1>")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_ftp_scheme_refused(self):
        r = open_url("ftp://files.example.com")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_vbscript_scheme_refused(self):
        r = open_url("vbscript:msgbox(1)")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_bare_string_refused(self):
        r = open_url("not-a-url")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_no_host_refused(self):
        r = open_url("https://")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_empty_url_error(self):
        r = open_url("")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_non_string_url_error(self):
        r = open_url(None)
        self.assertEqual(r.status, ResultStatus.ERROR)

    @patch("actions.urls.webbrowser.open", return_value=False)
    def test_webbrowser_failure_returns_error(self, _):
        r = open_url("https://example.com")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_result_used_llm_false(self):
        r = open_url("javascript:x")
        self.assertFalse(r.used_llm)


# ===========================================================================
# 5, 6 & 7 — Calculator
# ===========================================================================

class TestCalculate(unittest.TestCase):

    # --- Successful arithmetic ---

    def test_addition(self):
        r = calculate("2 + 3")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 5)

    def test_subtraction(self):
        r = calculate("10 - 4")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 6)

    def test_multiplication(self):
        r = calculate("3 * 7")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 21)

    def test_true_division(self):
        r = calculate("10 / 4")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 2.5)

    def test_modulo(self):
        r = calculate("10 % 3")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 1)

    def test_exponentiation(self):
        r = calculate("2 ** 8")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 256)

    def test_operator_precedence(self):
        """5 + 5 * 10 - 20 = 35, not 80."""
        r = calculate("5 + 5 * 10 - 20")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 35)

    def test_parentheses_override_precedence(self):
        r = calculate("(2 + 3) * 4")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 20)

    def test_unary_minus(self):
        r = calculate("-5 + 3")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, -2)

    def test_decimal_values(self):
        r = calculate("3.14 * 2")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(r.output, 6.28, places=5)

    def test_integer_result_not_float(self):
        """10 / 2 should return 5, not 5.0."""
        r = calculate("10 / 2")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 5)
        self.assertIsInstance(r.output, int)

    # --- Division / modulo by zero ---

    def test_division_by_zero_error(self):
        r = calculate("10 / 0")
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("zero", r.error.lower())

    def test_modulo_by_zero_error(self):
        r = calculate("10 % 0")
        self.assertEqual(r.status, ResultStatus.ERROR)

    # --- Malformed expressions ---

    def test_empty_expression_error(self):
        r = calculate("")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_syntax_error_refused(self):
        r = calculate("2 +* 3")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_too_long_expression_refused(self):
        r = calculate("1 + " * 60 + "1")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    # --- Blocked AST nodes ---

    def test_function_call_refused(self):
        r = calculate("__import__('os')")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_builtin_call_refused(self):
        r = calculate("open('file.txt')")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_name_node_refused(self):
        r = calculate("1 + x")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_attribute_access_refused(self):
        r = calculate("os.getcwd()")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_string_constant_refused(self):
        r = calculate("'hello'")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_result_used_llm_false(self):
        r = calculate("1 + 1")
        self.assertFalse(r.used_llm)

    # --- Exponentiation resource limits (regression) ---

    def test_exponentiation_within_limits(self):
        r = calculate("2 ** 8")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 256)

    def test_large_exponent_refused(self):
        r = calculate("2 ** 9999")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_large_base_refused(self):
        r = calculate("9999999 ** 2")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_nested_exponentiation_refused(self):
        """9**9**9 must be refused before any large integer is constructed."""
        r = calculate("9 ** 9 ** 9")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_computed_base_exceeding_limit_refused(self):
        """(2**10) ** 200 — base is a computed int > _MAX_INT_BASE? No: 1024 < 1_000_000.
        But (2**20) ** 200 — base 1_048_576 > 1_000_000 — must be refused."""
        r = calculate("(2 ** 20) ** 200")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_negative_base_exponentiation(self):
        """(-2) ** 3 is a legitimate calculation and must succeed."""
        r = calculate("(-2) ** 3")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, -8)

    def test_negative_exponent_float_result(self):
        """2 ** -1 = 0.5 — negative exponent produces float, must succeed."""
        r = calculate("2 ** -1")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertAlmostEqual(r.output, 0.5)

    def test_float_exponentiation_still_works(self):
        """Float exponentiation is bounded by IEEE 754 — must succeed."""
        r = calculate("2.0 ** 10")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 1024)


# ===========================================================================
# 8, 9 & 10 — File search
# ===========================================================================

class TestFileSearch(_TempDirMixin, unittest.TestCase):

    def test_exact_filename_match(self):
        self._touch("report.pdf")
        r = file_search("report.pdf", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertTrue(any("report.pdf" in p for p in r.output))

    def test_partial_name_match(self):
        self._touch("budget_2024.xlsx")
        r = file_search("budget", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertTrue(any("budget" in p for p in r.output))

    def test_case_insensitive_match(self):
        self._touch("Notes.TXT")
        r = file_search("notes", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertTrue(any("Notes.TXT" in p for p in r.output))

    def test_match_in_subdirectory(self):
        self._touch("subdir", "deep_file.txt")
        r = file_search("deep_file", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertTrue(any("deep_file.txt" in p for p in r.output))

    def test_no_match_returns_empty_list(self):
        r = file_search("nonexistent_xyz_abc", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, [])

    def test_no_match_has_informative_message(self):
        r = file_search("nonexistent_xyz_abc", root=self._tmp)
        self.assertIsNotNone(r.error)
        self.assertIn("nonexistent_xyz_abc", r.error)

    def test_multiple_matches_returned(self):
        self._touch("file_a.txt")
        self._touch("file_b.txt")
        r = file_search("file_", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertGreaterEqual(len(r.output), 2)

    def test_missing_directory_error(self):
        r = file_search("anything", root=os.path.join(self._tmp, "does_not_exist"))
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_empty_query_error(self):
        r = file_search("", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_non_string_query_error(self):
        r = file_search(None, root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_path_traversal_outside_root_refused(self):
        """A root outside FILE_SEARCH_ROOT must be refused."""
        r = file_search("passwd", root="C:\\Windows\\System32")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_path_traversal_dotdot_refused(self):
        """A root using .. to escape the allowed boundary must be refused."""
        escape = os.path.join(self._tmp, "..", "..", "Windows")
        r = file_search("hosts", root=escape)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_result_paths_inside_root(self):
        """Every returned path must be inside the search root."""
        self._touch("safe.txt")
        r = file_search("safe", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        for p in r.output:
            self.assertTrue(
                os.path.realpath(p).startswith(os.path.realpath(self._tmp)),
                f"Path escaped root: {p}",
            )

    def test_result_used_llm_false(self):
        r = file_search("anything", root=self._tmp)
        self.assertFalse(r.used_llm)

    def test_patched_root_respected_at_call_time(self):
        """FILE_SEARCH_ROOT patched after import must be read at call time."""
        self._touch("calltime.txt")
        # cfg.FILE_SEARCH_ROOT is already set to self._tmp by setUp.
        r = file_search("calltime")  # no explicit root — uses cfg value
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertTrue(any("calltime.txt" in p for p in r.output))

    def test_result_paths_are_realpath_contained(self):
        """Every returned path must be inside the root when resolved."""
        self._touch("contained.txt")
        r = file_search("contained", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        real_root = os.path.realpath(self._tmp)
        for p in r.output:
            real_p = os.path.realpath(p)
            self.assertTrue(
                real_p.startswith(real_root + os.sep) or real_p == real_root,
                f"Path escaped root via realpath: {real_p}",
            )

    @patch("os.walk")
    def test_permission_error_on_root_returns_error(self, mock_walk):
        """PermissionError raised by os.walk on the root returns ERROR."""
        mock_walk.side_effect = PermissionError("Access denied")
        r = file_search("anything", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("ermission", r.error)


# ===========================================================================
# 11 & 12 — Action registry
# ===========================================================================

class TestRegistry(unittest.TestCase):

    def test_unknown_action_refused(self):
        r = execute("fly_to_moon", {})
        self.assertEqual(r.status, ResultStatus.REFUSED)
        self.assertIn("fly_to_moon", r.error)

    def test_unknown_action_lists_supported(self):
        r = execute("unknown_action", {})
        self.assertIn("calculate", r.error)

    def test_empty_action_name_error(self):
        r = execute("", {})
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_non_dict_args_error(self):
        r = execute("calculate", "bad_args")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_missing_required_arg_error(self):
        r = execute("calculate", {})
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("expression", r.error)

    def test_blank_required_arg_error(self):
        r = execute("open_app", {"app_name": "   "})
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_unexpected_arg_refused(self):
        r = execute("calculate", {"expression": "1+1", "inject": "x"})
        self.assertEqual(r.status, ResultStatus.REFUSED)
        self.assertIn("inject", r.error)

    @patch("actions.apps.subprocess.Popen")
    def test_open_app_dispatch_success(self, mock_popen):
        mock_popen.return_value = MagicMock()
        r = execute("open_app", {"app_name": "notepad"})
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_open_url_dispatch_success(self, _):
        r = execute("open_url", {"url": "https://example.com"})
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    def test_calculate_dispatch_success(self):
        r = execute("calculate", {"expression": "6 * 7"})
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 42)

    def test_file_search_dispatch_with_location_key(self):
        """location is router metadata — registry must accept and ignore it."""
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "notes.txt").touch()
            orig = cfg.FILE_SEARCH_ROOT
            cfg.FILE_SEARCH_ROOT = tmp
            try:
                r = execute("file_search", {"query": "notes", "location": "desktop"})
                self.assertEqual(r.status, ResultStatus.SUCCESS)
            finally:
                cfg.FILE_SEARCH_ROOT = orig

    def test_success_result_structure(self):
        r = execute("calculate", {"expression": "1 + 1"})
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertIsNotNone(r.output)
        self.assertIsNone(r.error)
        self.assertFalse(r.used_llm)

    def test_failure_result_structure(self):
        r = execute("calculate", {"expression": "1 / 0"})
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIsNotNone(r.error)
        self.assertFalse(r.used_llm)


# ===========================================================================
# 13 — Local execution never calls an LLM
# ===========================================================================

class TestNoLlmUsed(unittest.TestCase):
    """Every local action must return used_llm=False."""

    @patch("actions.apps.subprocess.Popen")
    def test_open_app_no_llm(self, mock_popen):
        mock_popen.return_value = MagicMock()
        self.assertFalse(open_app("notepad").used_llm)

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_open_url_no_llm(self, _):
        self.assertFalse(open_url("https://example.com").used_llm)

    def test_calculate_no_llm(self):
        self.assertFalse(calculate("1 + 1").used_llm)

    def test_file_search_no_llm(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig = cfg.FILE_SEARCH_ROOT
            cfg.FILE_SEARCH_ROOT = tmp
            try:
                self.assertFalse(file_search("x", root=tmp).used_llm)
            finally:
                cfg.FILE_SEARCH_ROOT = orig

    def test_registry_calculate_no_llm(self):
        r = execute("calculate", {"expression": "2 + 2"})
        self.assertFalse(r.used_llm)


if __name__ == "__main__":
    unittest.main()
