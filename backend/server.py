"""T-MINUS LAN contract. T-0 from Launch Library 2."""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from launches import LaunchWindow

window = LaunchWindow()
app = FastAPI(title="T-MINUS", version="0.1.0")

# Pre-cropped 368x168 baseline-JPEG vehicle art, produced separately
# (files/tminus/gen_vehicle_art.py, not owned by this backend). Resolution
# order is: a file matching the launch's vehicle slug, otherwise nothing --
# the device keeps showing its own vector art. The Launch Library press
# photo is deliberately never used as a fallback (daylight/sky/ground, wrong
# for a black panel).
VEHICLES_DIR = "/home/tunas/DesktopShare/files/tminus/vehicles"


class StepBody(BaseModel):
    dir: int = Field(default=1)


def _art_path(slug: str | None) -> str | None:
    if not slug:
        return None
    path = os.path.join(VEHICLES_DIR, f"{slug}.jpg")
    return path if os.path.isfile(path) else None


def _payload(events: list[dict], idx: int) -> dict:
    event = events[idx]
    has_art = _art_path(event.get("art_slug")) is not None
    return {
        "id": event["id"],
        "vehicle": event["vehicle"],
        "mission": event["mission"],
        "pad": event["pad"],
        "t0_unix": event["t0_unix"],
        "server_unix": int(time.time()),
        "status": event["status"],
        "idx": idx,
        "count": len(events),
        # Device-facing image route, or None for a clean miss (no generated
        # art for this vehicle yet). Never the raw LL2 photo URL.
        "img": f"/tminus/img/{event['id']}.jpg" if has_art else None,
    }


@app.get("/health")
def health() -> dict:
    return {"ok": True, "app": "tminus"}


@app.get("/tminus/now")
def now() -> dict:
    try:
        events, idx = window.snapshot()
    except Exception as e:
        raise HTTPException(502, f"launch window failed: {e}") from e
    return _payload(events, idx)


@app.post("/tminus/step")
def step(body: StepBody) -> dict:
    try:
        events, idx = window.step(1 if body.dir >= 0 else -1)
    except Exception as e:
        raise HTTPException(502, f"launch window failed: {e}") from e
    return _payload(events, idx)


@app.get("/tminus/img/{launch_id}.jpg")
def img(launch_id: str) -> Response:
    """Panel-sized vehicle art for one launch. Serves the pre-cropped file
    as-is (already 368x168 baseline JPEG) -- no on-request resizing needed."""
    try:
        events, _ = window.snapshot()
    except Exception as e:
        raise HTTPException(502, f"launch window failed: {e}") from e
    event = next((e for e in events if e["id"] == launch_id), None)
    if event is None:
        raise HTTPException(404, "unknown launch id")
    path = _art_path(event.get("art_slug"))
    if not path:
        raise HTTPException(404, "no art for this vehicle")
    with open(path, "rb") as f:
        data = f.read()
    return Response(content=data, media_type="image/jpeg")
