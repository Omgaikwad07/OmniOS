"""
core/exceptions.py
==================
Project-wide exception hierarchy for OmniOS.
"""


class OmniOSError(Exception):
    """Base exception for all OmniOS action errors."""


class UnsupportedActionError(OmniOSError):
    """Raised when an action name is not in the registry."""


class ValidationError(OmniOSError):
    """Raised when action arguments fail validation."""
