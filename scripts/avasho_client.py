#!/usr/bin/env python3
"""Small synchronous client for Avasho Large's async TTS workflow."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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

    def __init__(self, token: str, timeout_seconds: float = 45.0):
        if not token.strip():
            raise AvashoError("AVASHO_GATEWAY_TOKEN is empty")
        self._token = token.strip()
        self._timeout_seconds = timeout_seconds

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[bytes, str]:
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={
                "gateway-token": self._token,
                "accept": "application/json, audio/mpeg, audio/*",
                **({"content-type": "application/json; charset=utf-8"} if payload else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return response.read(), response.headers.get_content_type()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise AvashoError(f"Avasho HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise AvashoError(f"Avasho connection failed: {error.reason}") from error

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
        if len(text) > 1000:
            raise AvashoError("Avasho accepts at most 1000 characters per request")
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
        request = urllib.request.Request(url, headers={"gateway-token": self._token})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                return response.read()
        except urllib.error.URLError as error:
            raise AvashoError(f"Avasho temporary download failed: {error.reason}") from error

    def synthesize(self, text: str, speaker: str, speed: float, poll_seconds: float = 1.0, timeout_seconds: float = 180.0) -> AvashoResult:
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
