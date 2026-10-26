"""
Tests for ContentService: content eligibility, provenance, and quiz validation.
Covers:
  - Fabricated fallback removal (fetch_live_source returns None on total failure)
  - Source content sufficiency validation
  - Quiz structural validation (options, answer membership, minimum count)
  - Malformed AI output rejection
  - Source URL preservation through the pipeline
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.content_service import (
    validate_source_content,
    validate_quiz_structure,
    strip_html_and_clean,
    ContentService,
)


# ---------------------------------------------------------------------------
# Unit Tests: validate_source_content
# ---------------------------------------------------------------------------

class TestValidateSourceContent:
    def test_rejects_none(self):
        assert validate_source_content(None, "Python") is False

    def test_rejects_empty_string(self):
        assert validate_source_content("", "Python") is False

    def test_rejects_short_content(self):
        assert validate_source_content("Python is a language.", "Python") is False

    def test_rejects_fabricated_boilerplate(self):
        text = "Authoritative reference material and foundational principles for Python. " * 10
        assert validate_source_content(text, "Python") is False

    def test_rejects_disambiguation_stub(self):
        text = "Python may refer to: a snake, a programming language, etc. " * 10
        assert validate_source_content(text, "Python") is False

    def test_rejects_topically_irrelevant_content(self):
        """Long content about cooking should not pass for a 'Python' skill."""
        text = ("Cooking is the art of preparing food. Heat transforms raw ingredients into "
                "delicious meals through various techniques such as boiling, roasting, and frying. ") * 5
        assert validate_source_content(text, "Python") is False

    def test_accepts_substantial_relevant_content(self):
        text = ("Python is a high-level programming language known for its readability. "
                "It supports multiple paradigms including procedural, object-oriented, and functional. "
                "Python's standard library provides modules for file I/O, networking, and data processing. "
                "The language uses indentation to define code blocks rather than curly braces. ") * 2
        assert validate_source_content(text, "Python") is True


# ---------------------------------------------------------------------------
# Unit Tests: validate_quiz_structure
# ---------------------------------------------------------------------------

class TestValidateQuizStructure:
    def test_rejects_non_list(self):
        assert validate_quiz_structure("not a list") == []

    def test_rejects_fewer_than_3_valid(self):
        quizzes = [
            {"question": "What is Python?", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "ok"},
        ]
        assert validate_quiz_structure(quizzes) == []

    def test_rejects_wrong_option_count(self):
        quizzes = [
            {"question": "Q" * 15, "options": ["A", "B", "C"], "answer": "A", "explanation": "x"},
        ] * 5
        assert validate_quiz_structure(quizzes) == []

    def test_rejects_answer_not_in_options(self):
        quizzes = [
            {"question": "Q" * 15, "options": ["A", "B", "C", "D"], "answer": "E", "explanation": "x"},
        ] * 5
        assert validate_quiz_structure(quizzes) == []

    def test_rejects_duplicate_options(self):
        quizzes = [
            {"question": "Q" * 15, "options": ["A", "A", "C", "D"], "answer": "A", "explanation": "x"},
        ] * 5
        assert validate_quiz_structure(quizzes) == []

    def test_rejects_short_question(self):
        quizzes = [
            {"question": "Q?", "options": ["A", "B", "C", "D"], "answer": "A", "explanation": "x"},
        ] * 5
        assert validate_quiz_structure(quizzes) == []

    def test_accepts_valid_quizzes(self):
        quizzes = [
            {
                "question": f"What is the purpose of concept {i} in Python?",
                "options": [f"Opt {i}A", f"Opt {i}B", f"Opt {i}C", f"Opt {i}D"],
                "answer": f"Opt {i}A",
                "explanation": f"Explanation for question {i}.",
            }
            for i in range(5)
        ]
        result = validate_quiz_structure(quizzes)
        assert len(result) == 5
        for q in result:
            assert q["answer"] in q["options"]


# ---------------------------------------------------------------------------
# Unit Tests: strip_html_and_clean
# ---------------------------------------------------------------------------

class TestStripHtmlAndClean:
    def test_strips_tags(self):
        assert strip_html_and_clean("<p>Hello <b>World</b></p>") == "Hello World"

    def test_unescapes_entities(self):
        # After unescape, &lt; &gt; becomes < > which the tag stripper removes.
        # This is correct behavior: the function strips HTML, not preserves angle brackets.
        assert strip_html_and_clean("&amp;") == "&"
        assert strip_html_and_clean("Hello &amp; World") == "Hello & World"

    def test_handles_empty(self):
        assert strip_html_and_clean("") == ""
        assert strip_html_and_clean(None) == ""


# ---------------------------------------------------------------------------
# Integration Tests: fetch_live_source_for_skill
# ---------------------------------------------------------------------------

class TestFetchLiveSourceFallbackRemoval:
    @pytest.mark.asyncio
    async def test_returns_none_when_all_sources_fail(self):
        """When every external source returns nothing usable, the function must return None
        instead of fabricating a Wikipedia URL with generic boilerplate text."""
        cs = ContentService()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            # All HTTP calls return 404
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {}
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await cs.fetch_live_source_for_skill("InventedNonsenseSkill12345", "Technical Skills")
            assert result is None, "Must return None when no adequate source exists, not a fabricated fallback."


class TestFetchLiveSourceUrlPreservation:
    @pytest.mark.asyncio
    async def test_wikipedia_preserves_real_url(self):
        """When Wikipedia returns a valid article, the real page URL must be preserved."""
        cs = ContentService()

        real_extract = ("Python is a high-level, general-purpose programming language. "
                        "Its design philosophy emphasizes code readability with the use "
                        "of significant indentation. Python is dynamically typed and "
                        "garbage-collected. It supports multiple programming paradigms. ") * 3

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            wiki_response = MagicMock()
            wiki_response.status_code = 200
            wiki_response.json.return_value = {
                "type": "standard",
                "title": "Python (programming language)",
                "extract": real_extract,
                "content_urls": {
                    "desktop": {"page": "https://en.wikipedia.org/wiki/Python_(programming_language)"}
                },
            }

            # Dev.to returns 404 (is_tech path), Wikipedia succeeds
            devto_response = MagicMock()
            devto_response.status_code = 404

            async def route_get(url, **kwargs):
                if "dev.to" in url:
                    return devto_response
                return wiki_response

            mock_client.get = AsyncMock(side_effect=route_get)

            result = await cs.fetch_live_source_for_skill("Python", "Technical Skills")
            assert result is not None
            assert result["source_url"] == "https://en.wikipedia.org/wiki/Python_(programming_language)"
            assert "Python" in result["raw_text"]


# ---------------------------------------------------------------------------
# Integration Tests: generate_dynamic_lesson_for_skill
# ---------------------------------------------------------------------------

class TestGenerateDynamicLessonFailsHonestly:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_source_found(self):
        """If fetch_live_source returns None, generate_dynamic_lesson must return None."""
        cs = ContentService()
        cs.fetch_live_source_for_skill = AsyncMock(return_value=None)

        result = await cs.generate_dynamic_lesson_for_skill(
            skill_id="skill-123",
            skill_name="QuantumEthicsArchitecture",
            category="Domain Knowledge",
            career_title="Quantum Ethicist",
        )
        assert result is None


class TestAtomizeRejectsMalformedAiOutput:
    @pytest.mark.asyncio
    async def test_rejects_empty_quiz_from_ai(self):
        """If the AI returns no quizzes, atomize_and_create_quiz must return None."""
        cs = ContentService()
        cs.ai_service.generate_json = AsyncMock(return_value={
            "summary_bullets": "• Point one\n• Point two\n• Point three",
            "difficulty_level": 2,
            "quizzes": [],
        })

        raw_item = {
            "title": "Test Lesson",
            "source_url": "https://example.com/test",
            "skill_name": "Python",
            "raw_text": ("Python is a programming language. " * 30),
        }
        result = await cs.atomize_and_create_quiz(raw_item)
        assert result is None
