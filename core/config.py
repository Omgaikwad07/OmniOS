
"""Configuration for the OmniOS LLM handler."""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile",
)

LLM_TIMEOUT_SECONDS = 30
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 100
MAX_DOCUMENT_CHARS = 60_000
MAX_OUTPUT_TOKENS = 1500
