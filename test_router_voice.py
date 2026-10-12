"""Voice-based manual testing script for the OmniOS classifier and router."""

import speech_recognition as sr
from core.schemas import TaskRequest
from router.classifier import classify
from router.task_router import route

SEPARATOR = "-" * 50


def display_result(text: str) -> None:
    classification = classify(text)
    decision = route(TaskRequest(raw_input=text))

    print(f"\n{SEPARATOR}")
    print(f"  Recognized text : {text}")
    print(f"  Intent          : {classification.intent.value}")
    print(f"  Confidence      : {classification.confidence:.0%}")
    print(f"  Route           : {decision.route.value}")
    print(f"  Action name     : {decision.action_name or '—'}")
    print(f"  Arguments       : {decision.validated_args or '—'}")
    print(f"  Explanation     : {decision.explanation}")
    print(SEPARATOR)


def main() -> None:
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("\n=== OmniOS Voice Router Test ===")
    print('Speak a command to classify it. Say "exit" to quit.\n')

    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Microphone ready.\n")

    while True:
        print("Listening...")
        try:
            with mic as source:
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)

            text = recognizer.recognize_google(audio)
            print(f"  (heard: \"{text}\")")

            if text.strip().lower() == "exit":
                print("\nExiting. Goodbye!")
                break

            display_result(text)

        except sr.WaitTimeoutError:
            print("  No speech detected. Try again.")
        except sr.UnknownValueError:
            print("  Could not understand audio. Try again.")
        except sr.RequestError as e:
            print(f"  Speech API error: {e}")
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break


if __name__ == "__main__":
    main()
