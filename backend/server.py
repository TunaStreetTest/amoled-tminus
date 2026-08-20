"""T-MINUS LAN contract. T-0 from Launch Library 2."""

from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from launches import LaunchWindow

window = LaunchWindow()
app = FastAPI(title="T-MINUS", version="0.1.0")


class StepBody(BaseModel):
    dir: int = Field(default=1)


def _payload(events: list[dict], idx: int) -> dict:
    event = events[idx]
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
