# PDF Summarizer

"""PDF extraction and summarization for OmniOS."""

from pathlib import Path

import pymupdf

from core.config import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    MAX_DOCUMENT_CHARS,
)
from core.exceptions import (
    DocumentLimitError,
    LLMConfigurationError,
    LLMRequestError,
    PDFExtractionError,
)
from core.schemas import ExecutionResult, ResultStatus
from agent.llm_client import generate_text


SUMMARY_PROMPT = """
Summarize the supplied PDF for the user.

Include:
1. The main topic and purpose.
2. The key points and findings.
3. Important facts, figures, and conclusions.
4. A short final takeaway.

Use clear headings and concise language.
Do not invent facts absent from the document.
Mention when the extracted text is insufficient.
"""


def extract_pdf_text(pdf_path: str) -> str:
    """Extract selectable text from a PDF locally."""

    path = Path(pdf_path).expanduser()

    if not path.exists() or not path.is_file():
        raise PDFExtractionError("The selected PDF file does not exist.")

    if path.suffix.lower() != ".pdf":
        raise PDFExtractionError("The selected file must be a PDF.")

    if path.stat().st_size > MAX_PDF_BYTES:
        raise DocumentLimitError("The PDF exceeds the 10 MB size limit.")

    try:
        with pymupdf.open(str(path)) as document:
            if document.is_encrypted:
                raise PDFExtractionError(
                    "Password-protected PDFs are not supported."
                )

            if len(document) == 0:
                raise PDFExtractionError("The PDF has no pages.")

            if len(document) > MAX_PDF_PAGES:
                raise DocumentLimitError(
                    f"The PDF exceeds the {MAX_PDF_PAGES}-page limit."
                )

            text = "\n".join(
                page.get_text("text") for page in document
            ).strip()

    except (PDFExtractionError, DocumentLimitError):
        raise
    except Exception as exc:
        raise PDFExtractionError(
            f"Could not read the PDF: {exc}"
        ) from exc

    if not text:
        raise PDFExtractionError(
            "No extractable text was found. "
            "The PDF may contain scanned images."
        )

    if len(text) > MAX_DOCUMENT_CHARS:
        raise DocumentLimitError(
            "Extracted text exceeds the supported character limit."
        )

    return text


def summarize_pdf(
    pdf_path: str,
    consent_to_external_processing: bool = False,
) -> ExecutionResult:
    """Summarize a PDF, requiring consent before external processing."""

    if not consent_to_external_processing:
        return ExecutionResult(
            status=ResultStatus.REFUSED,
            output=None,
            error=(
                "Consent is required before sending PDF text "
                "to an external AI provider."
            ),
            used_llm=False,
        )

    try:
        # Extraction runs locally on the user's computer.
        document_text = extract_pdf_text(pdf_path)

        # The document is sent to the external LLM only after consent.
        summary = generate_text(
            prompt=SUMMARY_PROMPT,
            document_text=document_text,
        )

        return ExecutionResult(
            status=ResultStatus.SUCCESS,
            output=summary,
            error=None,
            used_llm=True,
        )

    except DocumentLimitError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            output=None,
            error=str(exc),
            used_llm=False,
        )

    except PDFExtractionError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            output=None,
            error=str(exc),
            used_llm=False,
        )

    except LLMConfigurationError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            output=None,
            error=str(exc),
            used_llm=False,
        )

    except LLMRequestError as exc:
        return ExecutionResult(
            status=ResultStatus.ERROR,
            output=None,
            error=str(exc),
            used_llm=True,
        )
