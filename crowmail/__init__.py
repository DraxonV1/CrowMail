"""
Crowmail Python SDK
"""

from crowmail.client import CrowmailClient
from crowmail.errors import (
    APIError,
    AuthenticationError,
    CrowmailError,
    RateLimitError,
)

__all__ = [
    "CrowmailClient",
    "CrowmailError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
]
