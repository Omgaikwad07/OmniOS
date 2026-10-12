"""
tests/test_router.py
====================
Unit tests for the classifier and task router (Member 1 scope).

All tests are deterministic — no API keys, network access, or
actual Windows actions are required.
"""

import ast
import unittest

from core.schemas import Intent, Route, TaskRequest
from router.classifier import classify
from router.task_router import route


def _safe_eval_math(expr: str):
    """Safely evaluate arithmetic expressions via AST traversal without eval()."""
    node = ast.parse(expr, mode="eval").body

    def _eval(n):
        if isinstance(n, ast.Constant):
            return n.value
        elif isinstance(n, ast.BinOp):
            left = _eval(n.left)
            right = _eval(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            elif isinstance(n.op, ast.Sub):
                return left - right
            elif isinstance(n.op, ast.Mult):
                return left * right
            elif isinstance(n.op, ast.Div):
                return left / right
            raise ValueError(f"Unsupported operator: {n.op}")
        raise ValueError(f"Unsupported node: {n}")

    return _eval(node)


# ===================================================================
# Classifier tests
# ===================================================================

class TestClassifier(unittest.TestCase):
    """Tests for ``router.classifier.classify``."""

    # ---- OPEN_APP ----

    def test_open_app_basic(self):
        result = classify("open Notepad")
        self.assertEqual(result.intent, Intent.OPEN_APP)
        self.assertGreaterEqual(result.confidence, 0.70)

    def test_open_app_launch(self):
        result = classify("launch Chrome")
        self.assertEqual(result.intent, Intent.OPEN_APP)

    def test_open_app_start(self):
        result = classify("start Calculator")
        self.assertEqual(result.intent, Intent.OPEN_APP)

    def test_open_my_photo_not_app(self):
        result = classify("open my photo")
        self.assertNotEqual(result.intent, Intent.OPEN_APP)
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    # ---- OPEN_URL ----

    def test_open_url_explicit_https(self):
        result = classify("open https://google.com")
        self.assertEqual(result.intent, Intent.OPEN_URL)
        self.assertGreaterEqual(result.confidence, 0.85)

    def test_open_url_domain(self):
        result = classify("go to github.com")
        self.assertEqual(result.intent, Intent.OPEN_URL)

    def test_open_url_visit(self):
        result = classify("visit stackoverflow.com")
        self.assertEqual(result.intent, Intent.OPEN_URL)

    def test_open_google_website_is_url(self):
        result = classify("open Google website")
        self.assertEqual(result.intent, Intent.OPEN_URL)
        self.assertNotEqual(result.intent, Intent.OPEN_APP)

    # ---- CALCULATE ----

    def test_calculate_expression(self):
        result = classify("calculate 2 + 3 * 4")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_what_is(self):
        result = classify("what is 100 / 5")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_bare_expression(self):
        result = classify("15 + 27")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_word_form(self):
        result = classify("calculate 5 plus 3")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_perform(self):
        result = classify("perform 10 + 2")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_perform_complex_expression(self):
        result = classify("perform 5 + 5 x 10 - 20")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_spoken_times(self):
        result = classify("calculate 5 times 10")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_standalone_x(self):
        result = classify("5 x 10")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_spoken_into(self):
        result = classify("calculate 2 + 10 into 70 - 5 / 10")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_calculate_into_standalone(self):
        result = classify("10 into 70")
        self.assertEqual(result.intent, Intent.CALCULATE)

    def test_into_in_ordinary_text_not_calculate(self):
        result = classify("look into my files")
        self.assertNotEqual(result.intent, Intent.CALCULATE)

    def test_calculate_not_resume(self):
        """'resume' must not trigger CALCULATE via substring 'sum'."""
        result = classify("search my resume on my desktop")
        self.assertNotEqual(result.intent, Intent.CALCULATE)
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    def test_calculate_not_computer(self):
        """'computer' must not trigger CALCULATE via substring 'compute'."""
        result = classify("search for my photo in my computer")
        self.assertNotEqual(result.intent, Intent.CALCULATE)
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    # ---- FILE_SEARCH ----

    def test_file_search_find_file(self):
        result = classify("find the file report.pdf on my computer")
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    def test_file_search_locate(self):
        result = classify("locate document.docx")
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    def test_file_search_search_for(self):
        result = classify("search for notes.txt")
        self.assertEqual(result.intent, Intent.FILE_SEARCH)

    # ---- LLM_TASK ----

    def test_llm_summarize(self):
        result = classify("summarize this article about climate change")
        self.assertEqual(result.intent, Intent.LLM_TASK)

    def test_llm_explain(self):
        result = classify("explain quantum computing to me")
        self.assertEqual(result.intent, Intent.LLM_TASK)

    def test_llm_translate(self):
        result = classify("translate this paragraph to French")
        self.assertEqual(result.intent, Intent.LLM_TASK)

    def test_llm_write(self):
        result = classify("write a poem about the ocean")
        self.assertEqual(result.intent, Intent.LLM_TASK)

    def test_search_live_news_tell_me_is_llm(self):
        result = classify("search for live news and tell me what is going on")
        self.assertEqual(result.intent, Intent.LLM_TASK)
        self.assertNotEqual(result.intent, Intent.FILE_SEARCH)

    def test_update_resume_using_word_file_is_llm(self):
        result = classify("update my resume using Word file")
        self.assertEqual(result.intent, Intent.LLM_TASK)
        self.assertNotEqual(result.intent, Intent.FILE_SEARCH)

    # ---- UNKNOWN / edge cases ----

    def test_unknown_empty_string(self):
        result = classify("")
        self.assertEqual(result.intent, Intent.UNKNOWN)

    def test_unknown_whitespace(self):
        result = classify("   ")
        self.assertEqual(result.intent, Intent.UNKNOWN)

    def test_unknown_gibberish(self):
        result = classify("asdfghjkl")
        self.assertEqual(result.intent, Intent.UNKNOWN)

    def test_unknown_low_confidence(self):
        result = classify("asdfghjkl")
        self.assertLessEqual(result.confidence, 0.50)

    def test_ambiguous_returns_something(self):
        """An ambiguous request should still return a valid intent."""
        result = classify("do something with my files")
        self.assertIsInstance(result.intent, Intent)
        self.assertGreater(result.confidence, 0.0)


# ===================================================================
# Router tests
# ===================================================================

class TestTaskRouter(unittest.TestCase):
    """Tests for ``router.task_router.route``."""

    # ---- LOCAL routing ----

    def test_route_open_app_local(self):
        decision = route(TaskRequest(raw_input="open Notepad"))
        self.assertEqual(decision.intent, Intent.OPEN_APP)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "open_app")
        self.assertIsNotNone(decision.validated_args)
        self.assertIn("app_name", decision.validated_args)

    def test_route_open_url_local(self):
        decision = route(TaskRequest(raw_input="open https://example.com"))
        self.assertEqual(decision.intent, Intent.OPEN_URL)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "open_url")
        self.assertIn("url", decision.validated_args)

    def test_route_calculate_local(self):
        decision = route(TaskRequest(raw_input="calculate 10 + 5"))
        self.assertEqual(decision.intent, Intent.CALCULATE)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "calculate")
        self.assertIn("expression", decision.validated_args)

    def test_route_file_search_local(self):
        decision = route(TaskRequest(
            raw_input="find the file budget.xlsx on my computer",
        ))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "file_search")
        self.assertIn("query", decision.validated_args)

    # ---- LLM routing ----

    def test_route_llm_summarize(self):
        decision = route(TaskRequest(
            raw_input="summarize the meeting notes",
        ))
        self.assertEqual(decision.intent, Intent.LLM_TASK)
        self.assertEqual(decision.route, Route.LLM)
        self.assertIsNone(decision.action_name)

    def test_route_llm_explain(self):
        decision = route(TaskRequest(
            raw_input="explain the theory of relativity",
        ))
        self.assertEqual(decision.route, Route.LLM)

    # ---- NONE routing (unknown) ----

    def test_route_unknown_none(self):
        decision = route(TaskRequest(raw_input="xyzzy"))
        self.assertEqual(decision.intent, Intent.UNKNOWN)
        self.assertEqual(decision.route, Route.NONE)
        self.assertIsNone(decision.action_name)

    def test_route_empty_input(self):
        decision = route(TaskRequest(raw_input=""))
        self.assertEqual(decision.route, Route.NONE)

    # ---- Explanation field ----

    def test_decision_has_explanation(self):
        decision = route(TaskRequest(raw_input="open Notepad"))
        self.assertIsInstance(decision.explanation, str)
        self.assertTrue(len(decision.explanation) > 0)

    # ---- Confidence propagation ----

    def test_confidence_propagated(self):
        decision = route(TaskRequest(raw_input="calculate 1 + 1"))
        self.assertGreater(decision.confidence, 0.0)
        self.assertLessEqual(decision.confidence, 1.0)

    # ---- Argument extraction specifics ----

    def test_app_name_extracted(self):
        decision = route(TaskRequest(raw_input="launch Firefox"))
        self.assertEqual(
            decision.validated_args.get("app_name"), "Firefox",
        )

    def test_url_extracted_with_scheme(self):
        decision = route(TaskRequest(
            raw_input="open https://docs.python.org",
        ))
        self.assertEqual(
            decision.validated_args.get("url"), "https://docs.python.org",
        )

    def test_url_extracted_bare_domain(self):
        decision = route(TaskRequest(raw_input="go to github.com"))
        url = decision.validated_args.get("url", "")
        self.assertTrue(url.startswith("https://"))

    def test_expression_extracted(self):
        decision = route(TaskRequest(raw_input="what is 42 * 2"))
        expr = decision.validated_args.get("expression", "")
        self.assertIn("42", expr)

    def test_file_query_extracted(self):
        decision = route(TaskRequest(
            raw_input="find report.pdf on my computer",
        ))
        query = decision.validated_args.get("query", "")
        self.assertIn("report.pdf", query)

    def test_file_query_search_resume_desktop(self):
        decision = route(TaskRequest(
            raw_input="search for my resume in my desktop",
        ))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "file_search")
        query = decision.validated_args.get("query", "")
        self.assertEqual(query, "resume")
        self.assertNotIn("search", query)
        self.assertNotIn("desktop", query)

    def test_route_open_google_website_local(self):
        decision = route(TaskRequest(raw_input="open Google website"))
        self.assertEqual(decision.intent, Intent.OPEN_URL)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "open_url")
        self.assertEqual(decision.validated_args.get("url"), "https://www.google.com")

    def test_route_live_news_tell_me_llm(self):
        decision = route(TaskRequest(
            raw_input="search for live news and tell me what is going on",
        ))
        self.assertEqual(decision.intent, Intent.LLM_TASK)
        self.assertEqual(decision.route, Route.LLM)
        self.assertIsNone(decision.action_name)

    def test_route_update_resume_llm(self):
        decision = route(TaskRequest(
            raw_input="update my resume using Word file",
        ))
        self.assertEqual(decision.intent, Intent.LLM_TASK)
        self.assertEqual(decision.route, Route.LLM)
        self.assertIsNone(decision.action_name)

    def test_route_perform_expression_normalized(self):
        decision = route(TaskRequest(raw_input="perform 5 + 5 x 10 - 20"))
        self.assertEqual(decision.intent, Intent.CALCULATE)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "calculate")
        expr = decision.validated_args.get("expression")
        self.assertEqual(expr, "5 + 5 * 10 - 20")

    def test_calculate_operator_precedence_and_arithmetic(self):
        decision = route(TaskRequest(raw_input="perform 5 + 5 x 10 - 20"))
        expr = decision.validated_args.get("expression", "")
        # Safely evaluate using AST traversal without eval()
        result = _safe_eval_math(expr)
        # Operator precedence: 5 + (5 * 10) - 20 = 5 + 50 - 20 = 35 (not (5+5)*10-20 = 80)
        self.assertEqual(result, 35)

    def test_calculate_spoken_times_extracted(self):
        decision = route(TaskRequest(raw_input="calculate 5 times 10"))
        self.assertEqual(decision.validated_args.get("expression"), "5 * 10")
        self.assertEqual(_safe_eval_math(decision.validated_args.get("expression")), 50)

    def test_file_query_named_file(self):
        decision = route(TaskRequest(raw_input="open my photo named Om JPG"))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "file_search")
        query = decision.validated_args.get("query", "")
        self.assertEqual(query, "Om JPG")
        self.assertNotIn("photo", query)
        self.assertNotIn("named", query)

    def test_file_query_named_file_on_desktop(self):
        decision = route(TaskRequest(raw_input="open my photo named Om JPG on my desktop"))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.validated_args.get("query"), "Om JPG")
        self.assertEqual(decision.validated_args.get("location"), "desktop")

    def test_file_query_desktop_search(self):
        decision = route(TaskRequest(raw_input="search desktop for notes.txt"))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.validated_args.get("query"), "notes.txt")
        self.assertEqual(decision.validated_args.get("location"), "desktop")

    def test_route_calculate_spoken_into_extracted(self):
        decision = route(TaskRequest(raw_input="calculate 2 + 10 into 70 - 5 / 10"))
        self.assertEqual(decision.intent, Intent.CALCULATE)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "calculate")
        expr = decision.validated_args.get("expression")
        self.assertEqual(expr, "2 + 10 * 70 - 5 / 10")
        self.assertEqual(_safe_eval_math(expr), 701.5)

    def test_file_query_named_file_in_gallery_documents(self):
        decision = route(TaskRequest(raw_input="search my photo named Om JPG in gallery documents"))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.action_name, "file_search")
        query = decision.validated_args.get("query", "")
        self.assertEqual(query, "Om JPG")
        self.assertNotIn("gallery", query)
        self.assertNotIn("documents", query)
        self.assertEqual(decision.validated_args.get("location"), "gallery documents")

    def test_file_query_preserves_documents_in_filename(self):
        decision = route(TaskRequest(raw_input="find tax documents on my desktop"))
        self.assertEqual(decision.intent, Intent.FILE_SEARCH)
        self.assertEqual(decision.route, Route.LOCAL)
        self.assertEqual(decision.validated_args.get("query"), "tax documents")
        self.assertEqual(decision.validated_args.get("location"), "desktop")


if __name__ == "__main__":
    unittest.main()
