"""
Crowmail SDK Exceptions
"""

class CrowmailError(Exception):
    """Base exception for Crowmail SDK."""
    pass

class AuthenticationError(CrowmailError):
    """Raised when authentication fails (invalid credentials or expired token)."""
    pass

class RateLimitError(CrowmailError):
    """Raised when API rate limit is exceeded."""
    pass

class APIError(CrowmailError):
    """Raised when an API request returns an error response."""
    def __init__(self, message: str, status_code: int = 0, response_data: dict | None = None):
        super().__init__(f"[{status_code}] {message}" if status_code else message)
        self.status_code = status_code
        self.response_data = response_data or {}
