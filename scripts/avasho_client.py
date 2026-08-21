#!/usr/bin/env python3
"""Small synchronous client for Avasho Large's async TTS workflow."""

from __future__ import annotations

import json
import random
import re
import secrets
import socket
import time
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any


class AvashoError(RuntimeError):
    pass


@dataclass(frozen=True)
class AvashoResult:
    job_id: str
    audio: bytes
    timestamps: list[dict[str, Any]]


class AvashoClient:
    base_url = "https://partai.gw.isahab.ir/avasho/avasho-large"
    max_words_per_request = 1000

    def __init__(self, token: str, csrf_token: str = "", session_cookie: str = "",
                 timeout_seconds: float = 120.0, request_attempts: int = 6):
        if not token.strip():
            raise AvashoError("AVASHO_GATEWAY_TOKEN is empty")
        self._token = token.strip()
        self._csrf_token = csrf_token.strip()
        self._session_cookie = session_cookie.strip()
        self._timeout_seconds = timeout_seconds
        self._request_attempts = request_attempts
        self._cookie_jar = CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookie_jar)
        )
        if not self._csrf_token or not self._session_cookie:
            self._bootstrap_session()
        # بعضی gatewayهای Avasho پاسخ bootstrap را بدون cookie/header برمی‌گردانند
        # اما در POST فقط الگوی double-submit CSRF را می‌سنجند. در این حالت
        # یک جفتِ موقتِ هم‌ارز می‌سازیم تا workflow پیش از ارسال درخواست متوقف
        # نشود؛ اگر gateway به نشست واقعی نیاز داشته باشد، خطای HTTP خود سرویس
        # با جزئیات در لاگ ثبت خواهد شد.
        if not self._csrf_token:
            self._csrf_token = secrets.token_urlsafe(32)
        if not self._session_cookie:
            self._session_cookie = (
                f"XSRF-TOKEN={urllib.parse.quote(self._csrf_token, safe='')}"
            )

    def _cookie_header(self) -> str:
        return "; ".join(
            f"{cookie.name}={cookie.value}" for cookie in self._cookie_jar
        )

    @staticmethod
    def _csrf_from_response(headers: Any, raw: bytes, cookies: CookieJar) -> str:
        for key in ("x-csrf-token", "x-xsrf-token", "csrf-token", "x-csrf"):
            value = headers.get(key) if headers is not None else None
            if isinstance(value, str) and value.strip():
                return value.strip()
        for cookie in cookies:
            if cookie.name.lower() in {"xsrf-token", "x-xsrf-token", "csrf", "csrf-token", "csrftoken", "_csrf"}:
                return urllib.parse.unquote(cookie.value).strip('"')
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ""

        def find_csrf(value: Any) -> str:
            if isinstance(value, dict):
                for key, item in value.items():
                    normalized = str(key).replace("-", "_").lower()
                    if normalized in {"csrf", "csrf_token", "xsrf_token", "x_csrf_token"} and isinstance(item, str) and item.strip():
                        return item.strip()
                    found = find_csrf(item)
                    if found:
                        return found
            if isinstance(value, list):
                for item in value:
                    found = find_csrf(item)
                    if found:
                        return found
            return ""

        return find_csrf(decoded)

    def _bootstrap_session(self) -> None:
        """Create a short-lived gateway session and extract its matching CSRF token."""
        for path in ("", "/", "/csrf", "/csrf-token"):
            request = urllib.request.Request(
                f"{self.base_url}{path}",
                method="GET",
                headers={
                    "gateway-token": self._token,
                    "accept": "application/json, text/plain, */*",
                    "x-request-id": f"abtin-bootstrap-{int(time.time() * 1000)}",
                },
            )
            raw = b""
            headers = None
            try:
                with self._opener.open(request, timeout=self._timeout_seconds) as response:
                    raw = response.read()
                    headers = response.headers
            except urllib.error.HTTPError as error:
                raw = error.read()
                headers = error.headers
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError):
                continue

            if not self._session_cookie:
                self._session_cookie = self._cookie_header()
            if not self._csrf_token:
                self._csrf_token = self._csrf_from_response(headers, raw, self._cookie_jar)
            if self._session_cookie and self._csrf_token:
                return

    @property
    def _auth_headers(self) -> dict[str, str]:
        # همهٔ درخواست‌ها، به‌خصوص POST، با نشست یکسان و توکن همسان فرستاده
        # می‌شوند تا اعتبارسنجی CSRF سمت سرویس رد نشود.
        return {
            "gateway-token": self._token,
            "cookie": self._session_cookie,
            "x-csrf-token": self._csrf_token,
            "x-xsrf-token": self._csrf_token,
            "origin": self.base_url,
            "referer": f"{self.base_url}/",
            "user-agent": "AbtinMapsVoiceBuilder/1.0",
        }

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[bytes, str]:
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(1, self._request_attempts + 1):
            request = urllib.request.Request(
                f"{self.base_url}{path}", data=payload, method=method,
                headers={
                    **self._auth_headers,
                    "accept": "application/json, audio/mpeg, audio/*",
                    "x-request-id": f"abtin-{int(time.time() * 1000)}-{attempt}",
                    **({"content-type": "application/json; charset=utf-8"} if payload else {}),
                },
            )
            try:
                with self._opener.open(request, timeout=self._timeout_seconds) as response:
                    return response.read(), response.headers.get_content_type()
            except urllib.error.HTTPError as error:
                if error.code not in {408, 425, 429, 500, 502, 503, 504}:
                    detail = error.read().decode("utf-8", errors="replace")
                    raise AvashoError(f"Avasho HTTP {error.code}: {detail}") from error
                last_error = error
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError) as error:
                last_error = error
            if attempt < self._request_attempts:
                delay = min(45.0, 2 ** (attempt - 1)) + random.uniform(0.0, 0.8)
                print(f"Avasho request {method} {path} failed (attempt {attempt}/{self._request_attempts}); retrying in {delay:.1f}s", flush=True)
                time.sleep(delay)
        reason = getattr(last_error, "reason", last_error)
        raise AvashoError(f"Avasho connection failed after {self._request_attempts} attempts: {reason}") from last_error

    @staticmethod
    def _json(raw: bytes) -> dict[str, Any]:
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AvashoError("Avasho returned malformed JSON") from error
        if not isinstance(value, dict):
            raise AvashoError("Avasho response root is not an object")
        return value

    @staticmethod
    def _unwrap(value: dict[str, Any]) -> dict[str, Any]:
        node = value
        while isinstance(node.get("data"), dict):
            node = node["data"]
        return node

    @classmethod
    def _result(cls, node: dict[str, Any]) -> dict[str, Any] | None:
        response = node.get("aiResponse")
        result = response.get("result") if isinstance(response, dict) else None
        return result if isinstance(result, dict) else None

    def submit(self, text: str, speaker: str, speed: float) -> tuple[str, dict[str, Any] | None]:
        if not text.strip():
            raise AvashoError("Cannot synthesize empty text")
        if len(text.split()) > self.max_words_per_request:
            raise AvashoError("Avasho accepts at most 1000 words per request")
        raw, _ = self._request(
            "POST",
            "/request",
            {"text": text, "speaker": speaker, "speed": speed, "timestamp": True},
        )
        node = self._unwrap(self._json(raw))
        job_id = node.get("id")
        if not isinstance(job_id, str) or not job_id:
            raise AvashoError(f"Avasho request response has no id: {node}")
        return job_id, self._result(node)

    def track(self, job_id: str) -> dict[str, Any] | None:
        raw, _ = self._request("GET", f"/track/{job_id}")
        return self._result(self._unwrap(self._json(raw)))

    def download(self, job_id: str) -> bytes:
        raw, content_type = self._request("GET", f"/download/{job_id}")
        if content_type.startswith("audio/") or raw[:3] == b"ID3" or raw[:2] == b"\xff\xfb":
            return raw
        # A small number of API gateways return a JSON object with a temporary
        # URL instead of returning bytes directly; support that form too.
        node = self._unwrap(self._json(raw))
        url = node.get("download_url") or node.get("url") or node.get("file_url")
        if not isinstance(url, str) or not url:
            raise AvashoError("Avasho download did not return an MP3 or a download URL")
        last_error: Exception | None = None
        for attempt in range(1, self._request_attempts + 1):
            request = urllib.request.Request(url, headers=self._auth_headers)
            try:
                with self._opener.open(request, timeout=self._timeout_seconds) as response:
                    return response.read()
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionResetError) as error:
                last_error = error
            if attempt < self._request_attempts:
                time.sleep(min(45.0, 2 ** (attempt - 1)) + random.uniform(0.0, 0.8))
        reason = getattr(last_error, "reason", last_error)
        raise AvashoError(f"Avasho temporary download failed after {self._request_attempts} attempts: {reason}") from last_error

    def _split_for_requests(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self.max_words_per_request:
            return [text]
        # ترجیح با مرز جمله است؛ اگر جمله‌ای خیلی بلند بود، بدون ازدست‌رفتن متن
        # در مرز واژه تقسیم می‌شود تا هر فراخوانی با سقف مستندات سازگار بماند.
        chunks: list[str] = []
        current: list[str] = []
        for sentence in re.split(r"(?<=[.!؟])\s+", text):
            sentence_words = sentence.split()
            if len(current) + len(sentence_words) <= self.max_words_per_request:
                current.extend(sentence_words)
                continue
            if current:
                chunks.append(" ".join(current))
                current = []
            while len(sentence_words) > self.max_words_per_request:
                chunks.append(" ".join(sentence_words[:self.max_words_per_request]))
                sentence_words = sentence_words[self.max_words_per_request:]
            current.extend(sentence_words)
        if current:
            chunks.append(" ".join(current))
        return chunks

    def _synthesize_one(self, text: str, speaker: str, speed: float, poll_seconds: float, timeout_seconds: float) -> AvashoResult:
        job_id, result = self.submit(text, speaker, speed)
        deadline = time.monotonic() + timeout_seconds
        while result is None:
            if time.monotonic() >= deadline:
                raise AvashoError(f"Avasho job {job_id} did not finish before timeout")
            time.sleep(poll_seconds)
            result = self.track(job_id)
        timestamps = result.get("timestamps")
        return AvashoResult(
            job_id=job_id,
            audio=self.download(job_id),
            timestamps=timestamps if isinstance(timestamps, list) else [],
        )

    def synthesize(self, text: str, speaker: str, speed: float, poll_seconds: float = 1.0, timeout_seconds: float = 180.0) -> AvashoResult:
        results = [
            self._synthesize_one(part, speaker, speed, poll_seconds, timeout_seconds)
            for part in self._split_for_requests(text)
        ]
        if len(results) == 1:
            return results[0]
        offset = 0.0
        timestamps: list[dict[str, Any]] = []
        for result in results:
            for value in result.timestamps:
                if not isinstance(value, dict):
                    continue
                adjusted = dict(value)
                for key in ("start_time", "end_time"):
                    if isinstance(adjusted.get(key), (int, float)):
                        adjusted[key] = float(adjusted[key]) + offset
                timestamps.append(adjusted)
            offset = max((float(item.get("end_time", offset)) for item in timestamps if isinstance(item, dict)), default=offset)
        return AvashoResult(
            job_id=",".join(result.job_id for result in results),
            audio=b"".join(result.audio for result in results),
            timestamps=timestamps,
        )
