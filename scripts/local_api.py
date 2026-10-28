"""Cookie/CSRF client shared by interactive demos; credentials stay on localhost."""

import http.cookiejar
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


class ApiError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class LocalApi:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        parsed = urlsplit(base_url)
        if parsed.hostname not in {"localhost", "127.0.0.1"} or parsed.scheme not in {"http", "https"}:
            raise ValueError("Demos send credentials only to a localhost HTTP/HTTPS server")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("Use only a localhost server origin, such as http://127.0.0.1:5000")
        self.base = base_url.rstrip("/")
        self.csrf_token = None
        self.last_status, self.last_headers = None, None
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.cookies))

    def request(self, path, body=None, *, method=None):
        headers = {"Content-Type": "application/json"} if body is not None else {}
        if self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        data = json.dumps(body).encode("utf-8") if body is not None else None
        try:
            with self.opener.open(Request(self.base + path, data=data, headers=headers, method=method), timeout=15) as response:
                self.last_status, self.last_headers = response.status, response.headers
                raw = response.read()
                payload = json.loads(raw) if raw else None
        except HTTPError as error:
            with error:
                self.last_status, self.last_headers = error.code, error.headers
                payload = json.load(error)
                status = error.code
            raise ApiError(status, payload.get("error", {}).get("message", "Request failed")) from None
        if isinstance(payload, dict) and "csrfToken" in payload:
            self.csrf_token = payload["csrfToken"]
        return payload
