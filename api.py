"""
CardioSim v3.0 — FastAPI backend
Exposes the cardiovascular simulation as a JSON API consumed by the React frontend.
"""
from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from model import CLINICAL_PRESETS, STATE_LABELS, build_params
from metrics import run_sim

app = FastAPI(title="CardioSim API", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pool = ThreadPoolExecutor(max_workers=4)


class SimRequest(BaseModel):
    preset: str
    hr: float
    contract: float
    resist: float
    compl: float
    duration: float
    compare_preset: Optional[str] = None


def _arr(v):
    return v.tolist() if isinstance(v, np.ndarray) else v


def _serialize(r: dict | None) -> dict | None:
    if r is None:
        return None
    m = r["metrics"]
    return {
        "t":      r["t"].tolist(),
        "X":      r["X"].tolist(),
        "ecg":    r["ecg"].tolist(),
        "preset": r["preset"],
        "params": {k: (list(v) if k == "X0" else _arr(v))
                   for k, v in r["params"].items()},
        "metrics": {
            "co":       float(m["co"]),
            "sv":       float(m["sv"]),
            "sys":      float(m["sys"]),
            "dia":      float(m["dia"]),
            "map_val":  float(m["map_val"]),
            "pp":       float(m["pp"]),
            "lv_vol":   _arr(m["lv_vol"]),
            "lvp":      _arr(m["lvp"]),
            "lvof":     _arr(m["lvof"]),
            "lvp_full": _arr(m["lvp_full"]),
        },
        "rr": r["rr"].tolist() if r["rr"] is not None else None,
    }


def _run_sync(req: SimRequest):
    params = build_params(req.preset, req.hr, req.contract, req.resist, req.compl)
    r1 = run_sim(params, req.duration, req.preset)
    r2 = None
    if req.compare_preset and req.compare_preset in CLINICAL_PRESETS:
        info2 = CLINICAL_PRESETS[req.compare_preset]
        p2 = build_params(req.compare_preset, info2["hr"], info2["contract"],
                          info2["resist"], info2["compl"])
        r2 = run_sim(p2, req.duration, req.compare_preset)
    return r1, r2


@app.post("/api/simulate")
async def simulate(req: SimRequest):
    if req.preset not in CLINICAL_PRESETS:
        raise HTTPException(400, "Unknown preset")
    loop = asyncio.get_event_loop()
    r1, r2 = await loop.run_in_executor(_pool, _run_sync, req)
    if r1 is None:
        raise HTTPException(422, "Solver failed to converge — try increasing duration")
    return {"primary": _serialize(r1), "comparison": _serialize(r2)}


@app.get("/api/presets")
async def get_presets():
    return {
        name: {k: v for k, v in info.items() if k not in ("extra", "x0_overrides")}
        for name, info in CLINICAL_PRESETS.items()
    }


@app.get("/api/state-labels")
async def get_state_labels():
    return [{"name": n, "unit": u} for n, u in STATE_LABELS]


# Serve built React app in production
_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
