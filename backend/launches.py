"""Launch Library 2 upcoming window. T-0 is not a Grok guess."""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

import httpx

LL2_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/"
LL2_TTL_S = 15 * 60
LIMIT = 8
UA = "tunastreet-tminus/0.1 (+https://github.com/steven-matison/amoled-x-ember)"

PAD_PREFIX = (
    (re.compile(r"^Space Launch Complex\s+", re.I), "SLC-"),
    (re.compile(r"^Launch Complex\s+", re.I), "LC-"),
    (re.compile(r"^Rocket Lab Launch Complex\s+", re.I), "LC-"),
)

PLACE_HINTS = (
    ("Cape Canaveral", "Cape Canaveral"),
    ("Kennedy Space", "KSC"),
    ("Vandenberg", "Vandenberg"),
    ("Mahia", "Mahia"),
    ("Starbase", "Starbase"),
    ("Boca Chica", "Starbase"),
    ("Wallops", "Wallops"),
    ("Kourou", "Kourou"),
    ("Tanegashima", "Tanegashima"),
    ("Jiuquan", "Jiuquan"),
    ("Xichang", "Xichang"),
    ("Wenchang", "Wenchang"),
    ("Baikonur", "Baikonur"),
    ("Plesetsk", "Plesetsk"),
    ("Satish Dhawan", "Sriharikota"),
    ("Guiana", "Kourou"),
)


def _clip(text: str, limit: int) -> str:
    s = re.sub(r"\s+", " ", (text or "")).strip()
    if len(s) <= limit:
        return s
    cut = s[: max(limit - 1, 1)].rsplit(" ", 1)[0].rstrip(",;:·-–—")
    if not cut:
        cut = s[: max(limit - 1, 1)]
    return cut + "…"


def _abbrev_pad(name: str) -> str:
    s = name or ""
    for pat, repl in PAD_PREFIX:
        s = pat.sub(repl, s)
    return _clip(s, 16)


def _place(loc_name: str) -> str:
    s = loc_name or ""
    for needle, label in PLACE_HINTS:
        if needle.lower() in s.lower():
            return label
    if "," in s:
        s = s.split(",", 1)[0]
    return _clip(s, 22)


def _parse_net(net: str) -> int:
    if not net:
        raise ValueError("empty net")
    s = net.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def _normalize(raw: dict[str, Any]) -> dict[str, Any] | None:
    try:
        t0 = _parse_net(str(raw.get("net") or ""))
    except (TypeError, ValueError):
        return None
    pad = raw.get("pad") or {}
    loc = pad.get("location") or {}
    rocket = (raw.get("rocket") or {}).get("configuration") or {}
    status = raw.get("status") or {}
    mission = raw.get("mission") or {}
    name = str(raw.get("name") or "")
    mission_name = str(mission.get("name") or "")
    if not mission_name and "|" in name:
        mission_name = name.split("|", 1)[1].strip()
    pad_name = _abbrev_pad(str(pad.get("name") or ""))
    loc_name = _place(str(loc.get("name") or ""))
    pad_line = pad_name
    if loc_name and loc_name.lower() not in pad_name.lower():
        pad_line = f"{pad_name} · {loc_name}" if pad_name else loc_name
    vehicle = str(rocket.get("name") or rocket.get("full_name") or "LAUNCH")
    abbrev = str(status.get("abbrev") or status.get("name") or "TBD")
    return {
        "id": str(raw.get("id") or ""),
        "vehicle": _clip(vehicle, 24),
        "mission": _clip(mission_name or name, 36),
        "pad": _clip(pad_line, 40),
        "t0_unix": t0,
        "status": abbrev,
    }


def fetch_upcoming() -> list[dict[str, Any]]:
    with httpx.Client(timeout=20.0, headers={"User-Agent": UA}) as http:
        r = http.get(LL2_URL, params={"limit": LIMIT, "mode": "detailed"})
        r.raise_for_status()
        data = r.json()
    out: list[dict[str, Any]] = []
    for row in data.get("results") or []:
        event = _normalize(row)
        if event and event["id"]:
            out.append(event)
    if not out:
        raise RuntimeError("LL2 returned no usable launches")
    return out


def _next_idx(events: list[dict[str, Any]]) -> int:
    """First launch that hasn't lifted off yet.

    LL2's /upcoming/ window keeps a launch in the list after T-0 (it was
    returning a Falcon 9 that flew ~6 h earlier as row 0), so defaulting to
    row 0 puts a completed flight on the glass as the headline countdown.
    Past launches stay reachable with the back arrow; they just aren't the
    default view.
    """
    now = int(time.time())
    for i, e in enumerate(events):
        if e["t0_unix"] >= now:
            return i
    return 0


class LaunchWindow:
    """Upcoming launches, refreshed on a TTL. idx follows launch id across refreshes."""

    def __init__(self, ttl_s: float = LL2_TTL_S) -> None:
        self.ttl_s = ttl_s
        self._events: list[dict[str, Any]] = []
        self._current_id: str | None = None
        self._at = 0.0
        self._lock = threading.Lock()
        self._error: str | None = None

    def _refresh_locked(self, force: bool = False) -> None:
        now = time.time()
        if self._events and not force and (now - self._at) < self.ttl_s:
            return
        try:
            events = fetch_upcoming()
        except Exception as e:
            self._error = str(e)
            if not self._events:
                raise
            return
        self._error = None
        self._events = events
        self._at = now
        ids = [e["id"] for e in events]
        if self._current_id not in ids:
            self._current_id = ids[_next_idx(events)]

    def snapshot(self, force: bool = False) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            self._refresh_locked(force=force)
            events = [dict(e) for e in self._events]
            ids = [e["id"] for e in events]
            idx = ids.index(self._current_id) if self._current_id in ids else _next_idx(events)
            self._current_id = ids[idx]
            return events, idx

    def step(self, direction: int) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            self._refresh_locked()
            n = len(self._events)
            if n == 0:
                raise RuntimeError("no launches")
            ids = [e["id"] for e in self._events]
            idx = ids.index(self._current_id) if self._current_id in ids else 0
            idx = (idx + (1 if direction >= 0 else -1)) % n
            self._current_id = ids[idx]
            events = [dict(e) for e in self._events]
            return events, idx
