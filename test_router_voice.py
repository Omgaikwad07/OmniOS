"""Voice-based manual testing script and speech recognition module for OmniOS."""

from __future__ import annotations

from typing import Any, Optional, Tuple
import speech_recognition as sr
from core.schemas import ExecutionResult, RoutingDecision, TaskRequest
from router.classifier import classify
from router.task_router import route

SEPARATOR = "-" * 50


def listen_for_command(
    recognizer: Optional[sr.Recognizer] = None,
    mic: Optional[Any] = None,
    timeout: float = 8,
    phrase_time_limit: float = 10,
) -> Optional[str]:
    """Capture a single voice command from the microphone and transcribe it.

    Parameters
    ----------
    recognizer : sr.Recognizer, optional
        Speech recognizer instance. Created if not provided.
    mic : sr.Microphone, optional
        Microphone instance. Created if not provided.
    timeout : float
        Seconds to wait for speech to start before timing out.
    phrase_time_limit : float
        Maximum seconds for a single phrase.

    Returns
    -------
    str | None
        The transcribed speech text, or None if no speech detected,
        unintelligible, microphone error, or empty.
    """
    if recognizer is None:
        recognizer = sr.Recognizer()

    if mic is None:
        try:
            mic = sr.Microphone()
        except Exception as e:
            print(f"  Microphone initialization error: {e}")
            return None

    try:
        with mic as source:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        text = recognizer.recognize_google(audio)
        if text and text.strip():
            return text.strip()
        return None
    except sr.WaitTimeoutError:
        print("  No speech detected. Try again.")
        return None
    except sr.UnknownValueError:
        print("  Could not understand audio. Try again.")
        return None
    except sr.RequestError as e:
        print(f"  Speech API error: {e}")
        return None
    except Exception as e:
        print(f"  Microphone error: {e}")
        return None


def display_result(text: str) -> Tuple[RoutingDecision, Optional[ExecutionResult]]:
    """Process recognized speech through the OmniOS application pipeline.

    Connects voice input to the real execution flow, routing the command
    and executing approved local actions via the action registry while
    preserving safety checks and pipeline formatting.
    """
    from app import process_command
    return process_command(text)


def main() -> None:
    recognizer = sr.Recognizer()
    try:
        mic = sr.Microphone()
    except Exception as e:
        print(f"  Microphone error: {e}")
        return

    print("\n=== OmniOS Voice Interface ===")
    print('Speak a command to execute it. Say "exit" to quit.\n')

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Microphone ready.\n")
    except Exception as e:
        print(f"  Microphone calibration error: {e}")
        return

    while True:
        print("Listening...")
        try:
            text = listen_for_command(recognizer, mic)
            if not text:
                continue

            print(f"  (heard: \"{text}\")")

            if text.strip().lower() in {"exit", "quit"}:
                print("\nExiting. Goodbye!")
                break

            display_result(text)

        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break


if __name__ == "__main__":
    main()
