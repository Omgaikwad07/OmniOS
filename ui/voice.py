"""
ui/voice.py
===========
Thin adapter around the project's existing voice capture
(``test_router_voice.listen_for_command``).

The microphone control is only *enabled* when the speech stack is really
importable (SpeechRecognition + PyAudio); otherwise the UI shows it disabled
with an honest reason.  Capture runs in a worker thread and the transcript is
delivered through a callback that the caller must marshal onto the Tk thread.
Note: the existing recogniser (``recognize_google``) sends audio to Google's
web speech API, so it needs an internet connection.
"""
from __future__ import annotations

import importlib.util
import threading
from typing import Callable, Optional


def _has(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def availability() -> tuple[bool, str]:
    """Return ``(available, reason_if_not)``."""
    if not _has("speech_recognition"):
        return False, "SpeechRecognition is not installed"
    if not _has("pyaudio"):
        return False, "PyAudio is not installed"
    return True, ""


def listen_async(
    on_done: Callable[[Optional[str], Optional[str]], None],
    listen: Optional[Callable[[], Optional[str]]] = None,
) -> threading.Thread:
    """Capture one phrase in a daemon thread.

    ``on_done(text, error)`` is called from the worker thread: ``text`` is the
    transcript (or None), ``error`` a short message (or None).  ``listen`` can
    be injected for tests.
    """

    def _work() -> None:
        try:
            fn = listen
            if fn is None:
                from test_router_voice import listen_for_command as fn  # type: ignore
            text = fn()
            if text:
                on_done(text, None)
            else:
                on_done(None, "Didn't catch that — try again")
        except Exception as exc:  # microphone missing, no network, ...
            on_done(None, f"Voice input failed: {type(exc).__name__}")

    t = threading.Thread(target=_work, name="OmniOSVoice", daemon=True)
    t.start()
    return t
