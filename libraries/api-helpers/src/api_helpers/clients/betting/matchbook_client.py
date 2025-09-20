from zoneinfo import ZoneInfo
import pandas as pd
import requests
import json
from typing import Any


class MatchbookClient:

    def __init__(
        self,
        username: str,
        password: str,
        base_urls: dict | None = None,
        user_agent: str = "api-doc-test-client",
        default_service: str = "bpapi",
        timeout: float | None = 15.0,
    ):
        self.username = username
        self.password = password
        self.base_urls = base_urls or {
            "bpapi": "https://api.matchbook.com/bpapi/rest",
            "edge": "https://api.matchbook.com/edge/rest",
        }
        self.default_service = default_service
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json",
                "User-Agent": user_agent,
                "content-type": "application/json;charset=UTF-8",
            }
        )
        self.token = None

    def _build_url(self, service: str, path: str) -> str:
        base = self.base_urls[service].rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def login(self):
        r = self.session.post(
            self._build_url("bpapi", "security/session"),
            json={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )
        r.raise_for_status()
        self.token = r.json()["session-token"]
        self.session.headers["session-token"] = self.token
        return self.token

    def logout(self):
        try:
            self.session.delete(
                self._build_url("bpapi", "security/session"),
                timeout=self.timeout,
            )
        finally:
            self.token = None
            self.session.headers.pop("session-token", None)

    def _needs_reauth(self, r):
        if r.status_code in (401, 403):
            return True
        try:
            body = r.json()
            if isinstance(body, dict):
                text = json.dumps(body)
                if "AUTHENTICATION_REQUIRED" in text or "INVALID_SESSION" in text:
                    return True
        except Exception:
            if "AUTHENTICATION_REQUIRED" in r.text or "INVALID_SESSION" in r.text:
                return True
        return False

    def request(
        self,
        method: str,
        path: str,
        *,
        service: str | None = None,
        retries: int = 1,
        ensure_login: bool = True,
        params: dict | None = None,
        json: Any = None,
        data: Any = None,
        headers: dict | None = None,
        files: dict | None = None,
        **kwargs,
    ):
        if ensure_login and not self.token:
            self.login()

        url = (
            path
            if path.startswith("http")
            else self._build_url(service or self.default_service, path)
        )
        if "timeout" not in kwargs and self.timeout is not None:
            kwargs["timeout"] = self.timeout

        r = self.session.request(
            method.upper(),
            url,
            params=params,
            json=json,
            data=data,
            headers=headers,  # merged with session headers by requests
            files=files,
            **kwargs,
        )
        if self._needs_reauth(r) and retries > 0:
            self.login()
            return self.request(
                method,
                path,
                service=service,
                retries=retries - 1,
                ensure_login=False,
                params=params,
                json=json,
                data=data,
                headers=headers,
                files=files,
                **kwargs,
            )
        return r

    def get(
        self,
        path: str,
        *,
        service: str | None = None,
        params: dict | None = None,
        **kwargs,
    ):
        return self.request("GET", path, service=service, params=params, **kwargs)

    def post(
        self,
        path: str,
        *,
        service: str | None = None,
        json: Any = None,
        data: Any = None,
        **kwargs,
    ):
        return self.request(
            "POST", path, service=service, json=json, data=data, **kwargs
        )

    def delete(self, path: str, *, service: str | None = None, **kwargs):
        return self.request("DELETE", path, service=service, **kwargs)


class MatchbookHorseRacingData:

    HORSE_RACING_SPORT_ID = "24735152712200"

    def __init__(self, client: MatchbookClient):
        self.client = client

    def _fetch_horseracing_events_by_tag(
        self, tag_url_names: str = "uk", include_prices: bool = True
    ) -> list[dict]:
        params = {
            "sport-ids": self.HORSE_RACING_SPORT_ID,
            "tag-url-names": tag_url_names,
            "states": "open,suspended",  # include suspended to see more markets
            "include-prices": include_prices,
            "odds-type": "DECIMAL",
            "price-depth": 3,
            "per-page": 200,
            "offset": 0,
        }
        events: list[dict] = []
        while True:
            r = self.client.get("events", service="edge", params=params)
            r.raise_for_status()
            data = r.json()
            page = data.get("events", []) or []
            events.extend(page)
            if not page or len(events) >= int(data.get("total", 0)):
                break
            params["offset"] += params["per-page"]
        return events

    def create_market_data(self):

        events = self._fetch_horseracing_events_by_tag(tag_url_names="uk")

        rows = []
        for e in events:
            course = next(
                (
                    t.get("name")
                    for t in e.get("meta-tags", []) or []
                    if t.get("type") == "LOCATION"
                ),
                None,
            )
            race_time = (
                pd.to_datetime(e["start"], utc=True)
                .tz_convert(ZoneInfo("Europe/London"))
                .tz_localize(None)
            )
            for m in e.get("markets", []) or []:
                mname = (m.get("name") or "").strip()
                is_win = mname.upper() == "WIN"
                is_place = mname.lower().startswith("place")
                if not (is_win or is_place):
                    continue
                for r in m.get("runners", []) or []:
                    prices = r.get("prices", []) or []
                    backs = [p for p in prices if p.get("side") == "back"]
                    lays = [p for p in prices if p.get("side") == "lay"]
                    best_back = (
                        max(backs, key=lambda p: p["decimal-odds"]) if backs else None
                    )
                    best_lay = (
                        min(lays, key=lambda p: p["decimal-odds"]) if lays else None
                    )
                    rows.append(
                        {
                            "event_id": e["id"],
                            "course": course,
                            "race_time": race_time,
                            "market_id": m["id"],
                            "market_name": mname,  # "WIN" or "Place (n)"
                            "runner_id": r["id"],
                            "runner_name": r["name"],
                            "best_back_odds": (
                                best_back["decimal-odds"] if best_back else None
                            ),
                            "best_back_available": (
                                best_back["available-amount"] if best_back else None
                            ),
                            "best_lay_odds": (
                                best_lay["decimal-odds"] if best_lay else None
                            ),
                            "best_lay_available": (
                                best_lay["available-amount"] if best_lay else None
                            ),
                        }
                    )

        df = pd.DataFrame(rows)
        df["runner_name"] = (
            df["runner_name"]
            .str.replace(r"^\s*\d+\s*\.?\s*", "", regex=True)
            .str.strip()
        )

        return (
            df.filter(
                items=[
                    "event_id",
                    "course",
                    "race_time",
                    "market_id",
                    "market_name",
                    "runner_id",
                    "runner_name",
                    "best_back_odds",
                    "best_back_available",
                    "best_lay_odds",
                    "best_lay_available",
                ]
            )
            .sort_values(
                ["race_time", "course", "event_id", "market_name", "runner_name"]
            )
            .reset_index(drop=True)
        )
