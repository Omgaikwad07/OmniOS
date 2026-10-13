"""
tests/test_voice.py
===================
Tests for the OmniOS voice input interface and its integration with the
application pipeline and local action handlers.

All microphone interactions, speech recognition API calls, and OS process
spawns are strictly mocked. No real hardware or external network access
is required.
"""

from __future__ import annotations

from io import StringIO
import pathlib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import speech_recognition as sr

import core.config as cfg
from core.schemas import ResultStatus, Route
from test_router_voice import display_result, listen_for_command, main as voice_main
from app import process_command, run


class TestVoiceSpeechRecognition(unittest.TestCase):
    """Unit tests for the speech recognition listening function."""

    def test_listen_for_command_success(self):
        mock_rec = MagicMock(spec=sr.Recognizer)
        mock_mic = MagicMock()
        mock_audio = MagicMock()
        mock_rec.listen.return_value = mock_audio
        mock_rec.recognize_google.return_value = "calculate 10 + 5"

        text = listen_for_command(mock_rec, mock_mic)

        self.assertEqual(text, "calculate 10 + 5")
        mock_rec.listen.assert_called_once()
        mock_rec.recognize_google.assert_called_once_with(mock_audio)

    def test_listen_for_command_wait_timeout_graceful(self):
        mock_rec = MagicMock(spec=sr.Recognizer)
        mock_mic = MagicMock()
        mock_rec.listen.side_effect = sr.WaitTimeoutError("Timed out waiting for phrase")

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            text = listen_for_command(mock_rec, mock_mic)
            self.assertIsNone(text)
            self.assertIn("No speech detected", mock_out.getvalue())

    def test_listen_for_command_unknown_value_graceful(self):
        mock_rec = MagicMock(spec=sr.Recognizer)
        mock_mic = MagicMock()
        mock_rec.recognize_google.side_effect = sr.UnknownValueError()

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            text = listen_for_command(mock_rec, mock_mic)
            self.assertIsNone(text)
            self.assertIn("Could not understand audio", mock_out.getvalue())

    def test_listen_for_command_request_error_graceful(self):
        mock_rec = MagicMock(spec=sr.Recognizer)
        mock_mic = MagicMock()
        mock_rec.recognize_google.side_effect = sr.RequestError("Network dropped")

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            text = listen_for_command(mock_rec, mock_mic)
            self.assertIsNone(text)
            self.assertIn("Speech API error: Network dropped", mock_out.getvalue())

    def test_listen_for_command_mic_init_error_graceful(self):
        with patch("speech_recognition.Microphone", side_effect=OSError("No audio device")), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            text = listen_for_command(recognizer=MagicMock(), mic=None)
            self.assertIsNone(text)
            self.assertIn("Microphone initialization error", mock_out.getvalue())

    def test_listen_for_command_empty_transcription(self):
        mock_rec = MagicMock(spec=sr.Recognizer)
        mock_mic = MagicMock()
        mock_rec.recognize_google.return_value = "   "

        text = listen_for_command(mock_rec, mock_mic)
        self.assertIsNone(text)


class TestVoicePipelineExecution(unittest.TestCase):
    """Verifies recognized voice commands execute actions through the real pipeline."""

    def setUp(self):
        self._stdout_patch = patch("sys.stdout", new_callable=StringIO)
        self.mock_stdout = self._stdout_patch.start()

    def tearDown(self):
        self._stdout_patch.stop()

    def test_voice_command_calculate_execution(self):
        decision, result = display_result("calculate 15 * 4")

        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "calculate")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        self.assertEqual(result.output, 60)
        self.assertFalse(result.used_llm)

    @patch("actions.apps.subprocess.Popen")
    def test_voice_command_open_app_execution(self, mock_popen):
        mock_popen.return_value = MagicMock()
        decision, result = display_result("open notepad")

        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "open_app")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        mock_popen.assert_called_once()

    @patch("actions.urls.webbrowser.open", return_value=True)
    def test_voice_command_open_url_execution(self, mock_open):
        decision, result = display_result("open https://example.com")

        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "open_url")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, ResultStatus.SUCCESS)
        mock_open.assert_called_once_with("https://example.com")

    def test_voice_command_file_search_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "presentation.pdf").touch()
            orig = cfg.FILE_SEARCH_ROOT
            cfg.FILE_SEARCH_ROOT = tmp
            try:
                decision, result = display_result("find presentation.pdf on my computer")
                self.assertEqual(decision.route, Route.LOCAL)
                self.assertEqual(decision.action_name, "file_search")
                self.assertIsNotNone(result)
                self.assertEqual(result.status, ResultStatus.SUCCESS)
                self.assertTrue(any("presentation.pdf" in p for p in result.output))
            finally:
                cfg.FILE_SEARCH_ROOT = orig

    @patch("core.config.GROQ_API_KEY", "")
    def test_voice_command_llm_route_never_executes_actions(self):
        decision, result = display_result("summarize my meeting notes")

        self.assertEqual(decision.route, Route.LLM)
        self.assertIsNone(decision.action_name)
        self.assertIsNone(result)

    def test_voice_command_unknown_route_handled(self):
        decision, result = display_result("something completely unrecognizable")

        self.assertEqual(decision.route, Route.NONE)
        self.assertIsNone(decision.action_name)
        self.assertIsNone(result)

    def test_voice_command_safety_check_refusal(self):
        """Dangerous commands spoken by voice must be blocked by safety checks."""
        decision, result = display_result("calculate __import__('os')")

        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "calculate")
        self.assertIsNotNone(result)
        self.assertEqual(result.status, ResultStatus.REFUSED)


class TestAppVoiceIntegration(unittest.TestCase):
    """Tests voice triggering and voice mode inside the app CLI."""

    @patch("test_router_voice.listen_for_command")
    def test_app_voice_command_executes_action(self, mock_listen):
        mock_listen.return_value = "calculate 7 * 8"
        inputs = iter(["voice", "exit"])

        with patch("builtins.input", side_effect=inputs), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            run()
            output = mock_out.getvalue()

            self.assertIn("Listening for voice command...", output)
            self.assertIn('(heard: "calculate 7 * 8")', output)
            self.assertIn("CALCULATE", output)
            self.assertIn("SUCCESS", output)
            self.assertIn("56", output)
            self.assertIn("Goodbye", output)

    @patch("test_router_voice.listen_for_command")
    def test_app_voice_command_with_unrecognized_speech(self, mock_listen):
        mock_listen.return_value = None  # speech recognition failed or timed out
        inputs = iter(["voice", "calculate 2 + 2", "exit"])

        with patch("builtins.input", side_effect=inputs), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            run()
            output = mock_out.getvalue()

            self.assertIn("Listening for voice command...", output)
            self.assertIn("CALCULATE", output)
            self.assertIn("4", output)
            self.assertIn("Goodbye", output)

    @patch("test_router_voice.listen_for_command")
    def test_app_voice_command_saying_exit(self, mock_listen):
        mock_listen.return_value = "exit"
        inputs = iter(["voice"])

        with patch("builtins.input", side_effect=inputs), \
             patch("sys.stdout", new_callable=StringIO) as mock_out:
            run()
            output = mock_out.getvalue()

            self.assertIn("Listening for voice command...", output)
            self.assertIn("Goodbye.", output)

    @patch("test_router_voice.listen_for_command")
    def test_app_voice_mode_continuous_execution(self, mock_listen):
        mock_listen.side_effect = ["calculate 10 + 20", "exit"]

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            run(voice_mode=True)
            output = mock_out.getvalue()

            self.assertIn("OmniOS (voice)> Speak a command", output)
            self.assertIn("CALCULATE", output)
            self.assertIn("30", output)
            self.assertIn("Goodbye", output)


class TestTestRouterVoiceMain(unittest.TestCase):
    """Tests the test_router_voice.py main loop with mocked speech input."""

    @patch("speech_recognition.Microphone")
    @patch("speech_recognition.Recognizer")
    @patch("test_router_voice.listen_for_command")
    def test_voice_main_executes_and_exits(self, mock_listen, mock_rec_cls, mock_mic_cls):
        mock_mic = MagicMock()
        mock_mic_cls.return_value = mock_mic
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_listen.side_effect = ["calculate 9 * 9", "exit"]

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            voice_main()
            output = mock_out.getvalue()

            self.assertIn("=== OmniOS Voice Interface ===", output)
            self.assertIn('(heard: "calculate 9 * 9")', output)
            self.assertIn("CALCULATE", output)
            self.assertIn("81", output)
            self.assertIn("Exiting. Goodbye!", output)

    @patch("speech_recognition.Microphone")
    @patch("speech_recognition.Recognizer")
    @patch("test_router_voice.listen_for_command")
    def test_voice_main_keyboard_interrupt(self, mock_listen, mock_rec_cls, mock_mic_cls):
        mock_mic = MagicMock()
        mock_mic_cls.return_value = mock_mic
        mock_rec = MagicMock()
        mock_rec_cls.return_value = mock_rec
        mock_listen.side_effect = KeyboardInterrupt()

        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            voice_main()
            output = mock_out.getvalue()

            self.assertIn("Interrupted. Goodbye!", output)


if __name__ == "__main__":
    unittest.main()
