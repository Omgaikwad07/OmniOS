"""
tests/test_open_file.py
=======================
Unit and safety tests for actions/open_file.py.

os.startfile is mocked throughout — no real files are opened.
Temporary directories are used so no real user files are touched.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import tempfile
import unittest
from unittest.mock import patch

import core.config as cfg
from actions.open_file import open_file
from actions.registry import execute
from core.schemas import ResultStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _TempDirMixin:
    """Creates a temp dir and patches FILE_SEARCH_ROOT to point at it."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._orig_root = cfg.FILE_SEARCH_ROOT
        cfg.FILE_SEARCH_ROOT = self._tmp

    def tearDown(self):
        cfg.FILE_SEARCH_ROOT = self._orig_root
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _touch(self, *rel_parts) -> str:
        p = pathlib.Path(self._tmp, *rel_parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        return str(p)


# ===========================================================================
# Supported file types
# ===========================================================================

class TestSupportedExtensions(_TempDirMixin, unittest.TestCase):

    @patch("actions.open_file.os.startfile")
    def test_open_pdf(self, mock_sf):
        self._touch("report.pdf")
        r = open_file("report.pdf", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        mock_sf.assert_called_once()

    @patch("actions.open_file.os.startfile")
    def test_open_docx(self, mock_sf):
        self._touch("notes.docx")
        r = open_file("notes.docx", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_doc(self, mock_sf):
        self._touch("letter.doc")
        r = open_file("letter.doc", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_pptx(self, mock_sf):
        self._touch("slides.pptx")
        r = open_file("slides.pptx", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_ppt(self, mock_sf):
        self._touch("deck.ppt")
        r = open_file("deck.ppt", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_xlsx(self, mock_sf):
        self._touch("budget.xlsx")
        r = open_file("budget.xlsx", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_xls(self, mock_sf):
        self._touch("data.xls")
        r = open_file("data.xls", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_txt(self, mock_sf):
        self._touch("readme.txt")
        r = open_file("readme.txt", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_csv(self, mock_sf):
        self._touch("export.csv")
        r = open_file("export.csv", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_png(self, mock_sf):
        self._touch("photo.png")
        r = open_file("photo.png", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_jpg(self, mock_sf):
        self._touch("image.jpg")
        r = open_file("image.jpg", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_jpeg(self, mock_sf):
        self._touch("scan.jpeg")
        r = open_file("scan.jpeg", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_mp3(self, mock_sf):
        self._touch("song.mp3")
        r = open_file("song.mp3", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_open_mp4(self, mock_sf):
        self._touch("video.mp4")
        r = open_file("video.mp4", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)

    @patch("actions.open_file.os.startfile")
    def test_extension_case_insensitive(self, mock_sf):
        """PDF in uppercase must be accepted."""
        self._touch("REPORT.PDF")
        r = open_file("REPORT.PDF", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)


# ===========================================================================
# Missing files
# ===========================================================================

class TestMissingFile(_TempDirMixin, unittest.TestCase):

    def test_missing_file_returns_error(self):
        r = open_file("nonexistent.pdf", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("nonexistent.pdf", r.error)

    def test_missing_file_in_subdir_returns_error(self):
        r = open_file("deep/missing.txt", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    @patch("actions.open_file.os.startfile")
    def test_file_in_subdirectory_found_by_search(self, mock_sf):
        """Filename without path should be found by walking the root."""
        self._touch("subdir", "nested.pdf")
        r = open_file("nested.pdf", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        mock_sf.assert_called_once()


# ===========================================================================
# Invalid / disallowed extensions
# ===========================================================================

class TestInvalidExtensions(_TempDirMixin, unittest.TestCase):

    def test_exe_refused(self):
        r = open_file("malware.exe", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)
        self.assertIn(".exe", r.error)

    def test_bat_refused(self):
        r = open_file("script.bat", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_ps1_refused(self):
        r = open_file("attack.ps1", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_vbs_refused(self):
        r = open_file("macro.vbs", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_no_extension_refused(self):
        r = open_file("Makefile", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_py_refused(self):
        r = open_file("exploit.py", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_dll_refused(self):
        r = open_file("library.dll", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_refused_error_lists_allowed_extensions(self):
        r = open_file("bad.exe", root=self._tmp)
        self.assertIn(".pdf", r.error)


# ===========================================================================
# Path traversal / boundary enforcement
# ===========================================================================

class TestPathTraversal(_TempDirMixin, unittest.TestCase):

    def test_dotdot_traversal_refused(self):
        escape = os.path.join(self._tmp, "..", "..", "Windows", "win.ini")
        r = open_file(escape)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_absolute_path_outside_root_refused(self):
        r = open_file("C:\\Windows\\System32\\drivers\\etc\\hosts")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_root_outside_boundary_refused(self):
        r = open_file("hosts.txt", root="C:\\Windows\\System32")
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_root_dotdot_refused(self):
        escape_root = os.path.join(self._tmp, "..", "..", "Windows")
        r = open_file("win.ini", root=escape_root)
        self.assertEqual(r.status, ResultStatus.REFUSED)

    @patch("actions.open_file.os.startfile")
    def test_valid_subdir_root_allowed(self, mock_sf):
        """A root that is a subdirectory of FILE_SEARCH_ROOT is allowed."""
        sub = os.path.join(self._tmp, "docs")
        os.makedirs(sub, exist_ok=True)
        pathlib.Path(sub, "report.pdf").touch()
        r = open_file("report.pdf", root=sub)
        self.assertEqual(r.status, ResultStatus.SUCCESS)


# ===========================================================================
# Input validation
# ===========================================================================

class TestInputValidation(_TempDirMixin, unittest.TestCase):

    def test_empty_filename_error(self):
        r = open_file("", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_blank_filename_error(self):
        r = open_file("   ", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_none_filename_error(self):
        r = open_file(None, root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)

    def test_used_llm_always_false(self):
        r = open_file("anything.pdf", root=self._tmp)
        self.assertFalse(r.used_llm)


# ===========================================================================
# OS error handling
# ===========================================================================

class TestOsError(_TempDirMixin, unittest.TestCase):

    @patch("actions.open_file.os.startfile", side_effect=OSError("no app"))
    def test_startfile_oserror_returns_error(self, _):
        self._touch("report.pdf")
        r = open_file("report.pdf", root=self._tmp)
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("no app", r.error)


# ===========================================================================
# Registry integration
# ===========================================================================

class TestRegistryOpenFile(_TempDirMixin, unittest.TestCase):

    @patch("actions.open_file.os.startfile")
    def test_registry_dispatches_open_file(self, mock_sf):
        self._touch("report.pdf")
        r = execute("open_file", {"filename": "report.pdf", "root": self._tmp})
        self.assertEqual(r.status, ResultStatus.SUCCESS)
        mock_sf.assert_called_once()

    def test_registry_missing_filename_error(self):
        r = execute("open_file", {})
        self.assertEqual(r.status, ResultStatus.ERROR)
        self.assertIn("filename", r.error)

    def test_registry_unexpected_key_refused(self):
        r = execute("open_file", {"filename": "x.pdf", "inject": "bad"})
        self.assertEqual(r.status, ResultStatus.REFUSED)

    def test_registry_open_file_in_supported_list(self):
        r = execute("unknown_action_xyz", {})
        self.assertIn("open_file", r.error)


# ===========================================================================
# app.py integration — open_file triggered from FILE_SEARCH path
# ===========================================================================

class TestAppOpenFileIntegration(unittest.TestCase):

    def _run(self, commands):
        from io import StringIO
        inputs = iter(commands)
        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "builtins.input", side_effect=inputs
        ), __import__("unittest.mock", fromlist=["patch"]).patch(
            "sys.stdout", new_callable=StringIO
        ) as mock_out:
            import importlib, app as _app
            importlib.reload(_app)
            _app.run()
            return mock_out.getvalue()

    @patch("actions.open_file.os.startfile")
    def test_open_pdf_via_cli(self, mock_sf):
        import pathlib, tempfile, shutil
        tmp = tempfile.mkdtemp()
        pathlib.Path(tmp, "synopsis.pdf").touch()
        orig = cfg.FILE_SEARCH_ROOT
        cfg.FILE_SEARCH_ROOT = tmp
        try:
            out = self._run(["open synopsis.pdf", "exit"])
            self.assertIn("SUCCESS", out)
        finally:
            cfg.FILE_SEARCH_ROOT = orig
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
