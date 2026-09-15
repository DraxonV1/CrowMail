"""
Crowmail Python SDK Client
"""

from __future__ import annotations
import secrets
import string
from typing import Any, Optional
from urllib.parse import quote, urlencode

import requests

from crowmail.errors import APIError, AuthenticationError, CrowmailError, RateLimitError

DEFAULT_PROXY_BASE = "https://crowmail.sbs/api/mail"
DEFAULT_API_BASE = "https://api.crowmail.sbs"
DEFAULT_REFERRER = "https://crowmail.sbs/en"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36"
)


class CrowmailClient:
    """Client for interacting with Crowmail API."""

    def __init__(
        self,
        token: Optional[str] = None,
        proxy_mode: bool = True,
        proxy_base: str = DEFAULT_PROXY_BASE,
        api_base: str = DEFAULT_API_BASE,
        timeout: int = 15,
        session: Optional[requests.Session] = None,
        proxies: Optional[dict[str, str]] = None,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.token = token
        self.proxy_mode = proxy_mode
        self.proxy_base = proxy_base.rstrip("/")
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.proxies = proxies
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self._owns_session = session is None

    def __enter__(self) -> CrowmailClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP session if owned."""
        if self._owns_session:
            self.session.close()

    @staticmethod
    def generate_password(length: int = 12) -> str:
        """Generate a random secure alphanumeric password."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def _get_headers(self, auth: bool = True) -> dict[str, str]:
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache",
            "sec-ch-ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": self.user_agent,
            "referrer": DEFAULT_REFERRER,
            "referrerPolicy": "strict-origin-when-cross-origin",
        }
        if self.proxy_mode:
            headers["x-api-provider-base-url"] = self.api_base

        if auth and self.token:
            headers["authorization"] = f"Bearer {self.token}"

        return headers

    def _build_url(self, path: str, params: Optional[dict[str, Any]] = None) -> tuple[str, Optional[dict[str, Any]]]:
        query_str = f"?{urlencode(params)}" if params else ""
        full_endpoint = f"{path}{query_str}"

        if self.proxy_mode:
            encoded_endpoint = quote(full_endpoint, safe="")
            url = f"{self.proxy_base}?endpoint={encoded_endpoint}"
            return url, None
        else:
            url = f"{self.api_base}{path}"
            return url, params

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        auth: bool = True,
    ) -> Any:
        url, query_params = self._build_url(path, params)
        headers = self._get_headers(auth=auth)

        try:
            resp = self.session.request(
                method=method,
                url=url,
                json=json,
                params=query_params,
                headers=headers,
                timeout=self.timeout,
                proxies=self.proxies,
            )
        except requests.RequestException as exc:
            raise CrowmailError(f"Network error: {exc}") from exc

        # Parse response body
        try:
            data = resp.json() if resp.content else {}
        except Exception:
            data = {"raw_text": resp.text}

        if resp.status_code in (401, 403):
            msg = (
                data.get("message")
                or data.get("detail")
                or data.get("error")
                or "Unauthorized"
            )
            raise AuthenticationError(msg)

        if resp.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if not resp.ok:
            msg = (
                data.get("message")
                or data.get("detail")
                or data.get("error")
                or f"HTTP error {resp.status_code}"
            )
            raise APIError(message=msg, status_code=resp.status_code, response_data=data)

        return data

    def create_account(self, address: str, password: str, expires_in: int = 0) -> dict[str, Any]:
        """
        Create a new Crowmail account.
        Endpoint: POST /accounts
        """
        payload = {
            "address": address,
            "password": password,
            "expiresIn": expires_in,
        }
        return self._request("POST", "/accounts", json=payload, auth=False)

    def login(self, address: str, password: str) -> str:
        """
        Authenticate and obtain a JWT bearer token.
        Endpoint: POST /token
        """
        payload = {
            "address": address,
            "password": password,
        }
        data = self._request("POST", "/token", json=payload, auth=False)
        token = data.get("token")
        if not token:
            raise CrowmailError(f"Login failed: token not in response {data}")
        self.token = token
        return token

    def get_me(self) -> dict[str, Any]:
        """
        Get current account details.
        Endpoint: GET /me
        """
        return self._request("GET", "/me", auth=True)

    def change_password(self, old_password: str, new_password: str) -> dict[str, Any]:
        """
        Change account password.
        Endpoint: PATCH /accounts/me/password
        """
        payload = {
            "old_password": old_password,
            "new_password": new_password,
        }
        return self._request("PATCH", "/accounts/me/password", json=payload, auth=True)

    def get_domains(self, page: int = 1) -> dict[str, Any]:
        """
        List available domains.
        Endpoint: GET /domains?page=...
        """
        params = {"page": page} if page else None
        return self._request("GET", "/domains", params=params, auth=False)

    def get_messages(self, page: int = 1) -> dict[str, Any]:
        """
        List received messages.
        Endpoint: GET /messages?page=...
        """
        params = {"page": page} if page else None
        return self._request("GET", "/messages", params=params, auth=True)

    def get_message(self, message_id: str) -> dict[str, Any]:
        """
        Get specific message details by ID.
        Endpoint: GET /messages/{id}
        """
        return self._request("GET", f"/messages/{message_id}", auth=True)

    def delete_message(self, message_id: str) -> dict[str, Any]:
        """
        Delete a specific message by ID.
        Endpoint: DELETE /messages/{id}
        """
        return self._request("DELETE", f"/messages/{message_id}", auth=True)

    def delete_account(self) -> dict[str, Any]:
        """
        Delete current account.
        Endpoint: DELETE /accounts/me
        """
        return self._request("DELETE", "/accounts/me", auth=True)
