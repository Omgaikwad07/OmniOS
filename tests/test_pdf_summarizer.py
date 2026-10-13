    
from unittest.mock import patch

import pymupdf

from core.schemas import ResultStatus
from agent.pdf_summarizer import summarize_pdf


def create_test_pdf(path):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "OmniOS is an AI desktop assistant that routes tasks "
        "between local tools and language models."
    )
    document.save(str(path))
    document.close()


def test_consent_is_required(tmp_path):
    pdf = tmp_path / "sample.pdf"
    create_test_pdf(pdf)

    result = summarize_pdf(str(pdf))

    assert result.status == ResultStatus.REFUSED
    assert result.used_llm is False


@patch("agent.pdf_summarizer.generate_text")
def test_successful_summary(mock_generate, tmp_path):
    pdf = tmp_path / "sample.pdf"
    create_test_pdf(pdf)

    mock_generate.return_value = (
        "OmniOS routes tasks between local tools and AI models."
    )

    result = summarize_pdf(
        str(pdf),
        consent_to_external_processing=True,
    )

    assert result.status == ResultStatus.SUCCESS
    assert result.used_llm is True
    assert "OmniOS" in result.output
    mock_generate.assert_called_once()


@patch("agent.pdf_summarizer.generate_text")
def test_missing_pdf(mock_generate, tmp_path):
    result = summarize_pdf(
        str(tmp_path / "missing.pdf"),
        consent_to_external_processing=True,
    )

    assert result.status == ResultStatus.ERROR
    assert result.used_llm is False
    mock_generate.assert_not_called()
