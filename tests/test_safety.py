"""
tests/test_safety.py
====================
Security-focused tests for the OmniOS Windows Action Layer.

Verifies that injection attempts, path-traversal attacks, dangerous URL
schemes, and attempts to execute arbitrary Python via the calculator are
all rejected before any system call is made.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

import core.config as cfg
from actions.apps import open_app
from actions.calculator import calculate
from actions.file_search import file_search
from actions.registry import execute
from actions.urls import open_url
from core.schemas import ResultStatus


class TestAppLaunchSafety(unittest.TestCase):

    def test_shell_injection_in_app_name_refused(self):
        r = open_app("notepad & del /f /q C:\\*")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_path_traversal_in_app_name_refused(self):
        r = open_app("../../Windows/System32/cmd.exe")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_arbitrary_exe_path_refused(self):
        r = open_app("C:\\malware\\evil.exe")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_subprocess_not_called_for_unknown_app(self):
        with patch("actions.apps.subprocess.Popen") as mock_popen:
            open_app("UnknownApp")
            mock_popen.assert_not_called()

    def test_shell_true_never_used(self):
        """Popen must never be called with shell=True."""
        with patch("actions.apps.subprocess.Popen") as mock_popen:
            mock_popen.return_value.__class__ = type(mock_popen.return_value)
            open_app("notepad")
            if mock_popen.called:
                _, kwargs = mock_popen.call_args
                self.assertFalse(kwargs.get("shell", False))


class TestUrlSafety(unittest.TestCase):

    def test_file_scheme_refused(self):
        self.assertEqual(open_url("file:///etc/passwd").status, ResultStatus.REFUSED)

    def test_javascript_scheme_refused(self):
        self.assertEqual(open_url("javascript:alert(document.cookie)").status, ResultStatus.REFUSED)

    def test_data_scheme_refused(self):
        self.assertEqual(open_url("data:text/html,<script>evil()</script>").status, ResultStatus.REFUSED)

    def test_vbscript_scheme_refused(self):
        self.assertEqual(open_url("vbscript:Execute(\"CreateObject...\")" ).status, ResultStatus.REFUSED)

    def test_mailto_scheme_refused(self):
        self.assertEqual(open_url("mailto:victim@example.com").status, ResultStatus.REFUSED)

    def test_webbrowser_not_called_for_bad_scheme(self):
        with patch("actions.urls.webbrowser.open") as mock_wb:
            open_url("file:///C:/secret.txt")
            mock_wb.assert_not_called()

    def test_webbrowser_not_called_for_bare_string(self):
        with patch("actions.urls.webbrowser.open") as mock_wb:
            open_url("rm -rf /")
            mock_wb.assert_not_called()


class TestCalculatorSafety(unittest.TestCase):

    def test_import_refused(self):
        self.assertEqual(calculate("__import__('os')").status, ResultStatus.REFUSED)

    def test_exec_string_refused(self):
        # exec is a statement, not an expression — SyntaxError → REFUSED
        self.assertEqual(calculate("exec('import os')").status, ResultStatus.REFUSED)

    def test_eval_call_refused(self):
        self.assertEqual(calculate("eval('1+1')").status, ResultStatus.REFUSED)

    def test_open_call_refused(self):
        self.assertEqual(calculate("open('C:/secret.txt')").status, ResultStatus.REFUSED)

    def test_attribute_access_refused(self):
        self.assertEqual(calculate("os.system('dir')").status, ResultStatus.REFUSED)

    def test_name_variable_refused(self):
        self.assertEqual(calculate("x + 1").status, ResultStatus.REFUSED)

    def test_list_literal_refused(self):
        self.assertEqual(calculate("[1, 2, 3]").status, ResultStatus.REFUSED)

    def test_dict_literal_refused(self):
        self.assertEqual(calculate("{'a': 1}").status, ResultStatus.REFUSED)

    def test_string_literal_refused(self):
        self.assertEqual(calculate("'hello'").status, ResultStatus.REFUSED)

    def test_division_by_zero_error_not_exception(self):
        """Division by zero must return ERROR, not raise an unhandled exception."""
        r = calculate("1 / 0")
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_overflow_via_exponentiation_handled(self):
        """9**9**9 would allocate gigabytes — must be REFUSED before computing."""
        r = calculate("9 ** 9 ** 9")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_large_exponent_refused(self):
        """Exponent exceeding the safe limit must be REFUSED."""
        r = calculate("2 ** 9999")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_large_base_refused(self):
        """Base exceeding the safe limit must be REFUSED."""
        r = calculate("9999999 ** 2")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_normal_exponentiation_still_works(self):
        """Ordinary exponentiation within limits must still succeed."""
        r = calculate("2 ** 8")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 256)

    def test_float_exponentiation_still_works(self):
        """Float exponentiation is bounded by IEEE 754 and must succeed."""
        r = calculate("2.0 ** 10")
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        self.assertEqual(r.output, 1024)

    def test_nested_exponentiation_bypass_refused(self):
        """(2**20)**200 — computed base exceeds limit — must be refused."""
        r = calculate("(2 ** 20) ** 200")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_negative_exponent_allowed(self):
        """2**-1 is a safe float result and must not be refused."""
        r = calculate("2 ** -1")
        self.assertEqual(r.status, ResultStatus.SUCCESS)


class TestFileSearchSafety(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._orig = cfg.FILE_SEARCH_ROOT
        cfg.FILE_SEARCH_ROOT = self._tmp

    def tearDown(self):
        cfg.FILE_SEARCH_ROOT = self._orig
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_absolute_path_outside_root_refused(self):
        r = file_search("hosts", root="C:\\Windows\\System32")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_dotdot_traversal_refused(self):
        escape = os.path.join(self._tmp, "..", "..", "Windows")
        r = file_search("hosts", root=escape)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_drive_root_refused(self):
        r = file_search("secret", root="C:\\")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_no_file_contents_read(self):
        """file_search must never call open() on matched files."""
        import pathlib
        pathlib.Path(self._tmp, "data.txt").write_text("sensitive content")
        with patch("builtins.open") as mock_open:
            file_search("data", root=self._tmp)
            mock_open.assert_not_called()


class TestRegistrySafety(unittest.TestCase):

    def test_unknown_action_refused(self):
        r = execute("delete_files", {})
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_registry_injection_via_action_name_refused(self):
        r = execute("calculate; import os", {"expression": "1"})
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_extra_args_refused(self):
        r = execute("calculate", {"expression": "1+1", "__class__": "evil"})
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_none_action_name_error(self):
        r = execute(None, {})
        self.assertEqual(r.status, ResultStatus.ERROR)


if __name__ == "__main__":
    unittest.main()
