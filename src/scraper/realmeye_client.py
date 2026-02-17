from __future__ import annotations

import os
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


@dataclass
class RealmEyeClient:
    base_url: str = "https://www.realmeye.com"
    user_agent: str = "realm-requirements-sheet-bot/0.2"
    timeout_s: int = 30
    retries: int = 3
    backoff_s: float = 1.5
    polite_delay_s: float = 0.5

    def fetch(self, path_or_url: str) -> str:
        url = path_or_url if path_or_url.startswith("http") else f"{self.base_url}{path_or_url}"
        request = Request(url, headers={"User-Agent": self.user_agent})

        # Allow opt-out of environment proxy settings when they block requests.
        if os.getenv("REALMEYE_DISABLE_PROXY", "").lower() in {"1", "true", "yes"}:
            opener = build_opener(ProxyHandler({}))
        else:
            opener = build_opener()

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with opener.open(request, timeout=self.timeout_s) as response:
                    payload = response.read().decode("utf-8", errors="replace")
                time.sleep(self.polite_delay_s)
                return payload
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(self.backoff_s * attempt)

        hint = ""
        if last_error and "Tunnel connection failed" in str(last_error):
            hint = " Set REALMEYE_DISABLE_PROXY=1 to bypass proxy environment variables if your network allows direct egress."
        raise RuntimeError(f"Failed to fetch {url}.{hint}") from last_error
