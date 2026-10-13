# Exceptions

"""Custom exceptions for the OmniOS AI handler."""


class OmniOSError(Exception):
    """Base exception for OmniOS handler errors."""


class LLMConfigurationError(OmniOSError):
    """LLM configuration is missing or invalid."""


class LLMRequestError(OmniOSError):
    """The LLM request failed."""


class PDFExtractionError(OmniOSError):
    """PDF text extraction failed."""


class DocumentLimitError(OmniOSError):
    """The PDF exceeds the supported limits."""
