"""
Market State Trader — Web UI + API.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from main import MarketStateTrader
import mst_config as config

trader: MarketStateTrader = None
_ws_clients: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global trader
    trader = MarketStateTrader()
    task = asyncio.create_task(_broadcast_loop())
    yield
    task.cancel()
    if trader.running:
        await trader.stop()


app = FastAPI(title="Market State Trader", lifespan=lifespan)


async def _broadcast_loop():
    while True:
        if trader:
            status = trader.status()
            dead = []
            for ws in _ws_clients:
                try:
                    await ws.send_json({"type": "status", "data": status})
                except Exception:
                    dead.append(ws)
            for ws in dead:
                if ws in _ws_clients:
                    _ws_clients.remove(ws)
        await asyncio.sleep(5)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    _ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


# ── Status ──
@app.get("/api/status")
def get_status():
    if not trader: return {"running": False}
    return trader.status()


# ── Control ──
class StartRequest(BaseModel):
    interval: int = config.CYCLE_INTERVAL

@app.post("/api/start")
async def start_trader(req: StartRequest = None):
    global trader
    if req is None:
        req = StartRequest()
    if trader.running:
        return {"status": "already_running"}
    config.CYCLE_INTERVAL = req.interval
    asyncio.create_task(trader.loop())
    return {"status": "started"}


@app.post("/api/stop")
async def stop_trader():
    if not trader or not trader.running:
        return {"status": "not_running"}
    await trader.stop()
    return {"status": "stopped"}


# ── Candidates ──
@app.get("/api/candidates")
def get_candidates(limit: int = 50):
    if not trader: return {"candidates": [], "summary": {}}
    return {
        "candidates": trader.logger.recent(limit),
        "summary": trader.logger.summary(),
    }


# ── Trades ──
@app.get("/api/trades")
def get_trades(limit: int = 50):
    if not trader: return []
    return list(reversed(trader.paper.trade_history[-limit:]))


# ── Log ──
@app.get("/api/log")
def get_log(limit: int = 50):
    if not trader: return []
    return list(reversed(trader.log[-limit:]))


# ── Analysis (Phase 2) ──
@app.get("/api/analysis")
def get_analysis():
    from analysis import context_summary
    return context_summary("data/candidates.json")


@app.get("/api/analysis/report")
def get_analysis_report():
    from analysis import full_report
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        full_report("data/candidates.json")
    return {"report": buf.getvalue()}


# ── UI ──
@app.get("/", response_class=HTMLResponse)
def index():
    path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "<h1>Market State Trader</h1><p>UI template not found.</p>"
