"""Resilient httpx client for the FPL API.

Retry/backoff + timeout + a descriptive User-Agent live here once, since the
FBref client (Phase 5) will follow the same shape against a stricter
rate limit. See ARCHITECTURE.md#rate-limit-etiquette.
"""

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from fpl_engine.ingestion.fpl.models import BootstrapPayload, EntryPicksPayload, Fixture

BASE_URL = "https://fantasy.premierleague.com/api"
USER_AGENT = "fpl-engine/0.1 (personal project; https://github.com/)"

_retry = retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)


class FplClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 15.0) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FplClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @_retry
    def _get(self, path: str) -> dict:
        response = self._client.get(path)
        response.raise_for_status()
        return response.json()

    def get_bootstrap(self) -> BootstrapPayload:
        return BootstrapPayload.model_validate(self._get("/bootstrap-static/"))

    def get_fixtures(self) -> list[Fixture]:
        payload = self._get("/fixtures/")
        return [Fixture.model_validate(item) for item in payload]

    def get_entry_picks(self, entry_id: int, event_id: int) -> EntryPicksPayload:
        return EntryPicksPayload.model_validate(
            self._get(f"/entry/{entry_id}/event/{event_id}/picks/")
        )
