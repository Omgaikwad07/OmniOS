
"""
core/exceptions.py
==================
Project-wide exception hierarchy for OmniOS.
"""


class OmniOSError(Exception):
    """Base exception for all OmniOS errors."""


class UnsupportedActionError(OmniOSError):
    """Raised when an action name is not in the registry."""


class ValidationError(OmniOSError):
    """Raised when action arguments fail validation."""


class LLMConfigurationError(OmniOSError):
    """LLM configuration is missing or invalid."""


class LLMRequestError(OmniOSError):
    """The LLM request failed."""


class PDFExtractionError(OmniOSError):
    """PDF text extraction failed."""


class DocumentLimitError(OmniOSError):
    """The PDF exceeds the supported limits."""

