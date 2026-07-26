"""
Storage — persists entry candidates with full MarketState + outcomes.
"""
import bisect
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

import mst_config as config


@dataclass
class Candidate:
    timestamp: str                         # candle close time (ISO 8601 UTC) == the state's timestamp
    direction: str                         # "long" | "short" | "none"
    state_price: float                     # 1h candle close price → state/forward-return analysis
    execution_price: float                 # live price at decision time → trading/execution analysis
    context: str
    context_confidence: float
    decision: str
    decision_reason: str
    market_state: Optional[dict] = None
    source: str = "live"                   # "live" (real-time collector) | "backfill" (scripts/backfill.py)
    # Raw forward returns (dir-agnostic — not adjusted for long/short)
    forward_return_15m: Optional[float] = None
    forward_return_30m: Optional[float] = None
    forward_return_1h: Optional[float] = None
    forward_return_4h: Optional[float] = None
    # When the return was measured (actual wall-clock time)
    outcome_measured_at: dict = field(default_factory=dict)
    # Target measurement time (candle-close-aligned)
    outcome_target_time: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        return d


class CandidateLogger:
    OUTCOME_WINDOWS = {"15m": 15*60, "30m": 30*60, "1h": 60*60, "4h": 4*60*60}

    # One candidate per closed 1h candle → ~8760/year. 50,000 is ~5.7 years of
    # runway before the oldest candidates start rolling off — comfortably past
    # any realistic length of the data-collection phase, while keeping
    # candidates.json bounded (a few hundred MB at worst) instead of growing
    # forever. Both the in-memory list and the persisted file share this cap;
    # previously the file was capped at a much smaller 2000 regardless of this
    # constant, silently losing everything older than ~83 days.
    MAX_CANDIDATES = 50_000

    def __init__(self, file_path: Optional[str] = None):
        # Defaults to the live collector's file; scripts/backfill.py passes
        # its own path so it never touches candidates.json while the live
        # service may be reading/writing it concurrently.
        self.file_path = file_path or config.CANDIDATES_FILE
        self.candidates: list[Candidate] = []
        self._load()

    def add(self, c: Candidate):
        self.candidates.append(c)
        if len(self.candidates) > self.MAX_CANDIDATES:
            self.candidates = self.candidates[-self.MAX_CANDIDATES:]
        self._save()

    # How close a 1m close has to be to the exact target timestamp to count
    # as "the" price at that time — guards against silently using a much
    # later price (e.g. after the bot was offline) and mislabeling it.
    OUTCOME_TOLERANCE_SEC = 120

    # A miss only gets reported to the caller (for a log line) within this
    # many seconds of its target time — an old, still-pending miss from hours
    # ago would otherwise get re-reported every single cycle forever.
    FRESH_MISS_WINDOW_SEC = 5 * 60

    def update_outcomes(self, price_history: dict) -> dict:
        """price_history: {ts_ms: close_price} of 1m candles, e.g.
        MarketStateTrader.price_history. Measures each forward return at the
        exact target timestamp (state time + window) using the closest 1m
        close within OUTCOME_TOLERANCE_SEC — not "whatever price is live
        when the bot happens to check", which drifts with cycle timing and
        breaks entirely across downtime.

        Returns {"filled": [...], "fresh_misses": int} so the caller can log
        it — "filled" lists the returns just measured this call, "fresh_misses"
        counts targets whose time just passed with no 1m data close enough to
        trust (see FRESH_MISS_WINDOW_SEC), a live data-quality signal.
        """
        filled: list[dict] = []
        fresh_misses = 0
        if not price_history:
            return {"filled": filled, "fresh_misses": fresh_misses}
        sorted_ts = sorted(price_history.keys())
        now = datetime.now(timezone.utc)
        now_ms = int(now.timestamp() * 1000)
        tolerance_ms = self.OUTCOME_TOLERANCE_SEC * 1000
        fresh_ms = self.FRESH_MISS_WINDOW_SEC * 1000
        changed = False
        for c in self.candidates:
            try:
                cts = datetime.fromisoformat(c.timestamp)
                if cts.tzinfo is None:
                    cts = cts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            cts_ms = int(cts.timestamp() * 1000)
            for window_name, window_sec in self.OUTCOME_WINDOWS.items():
                attr = f"forward_return_{window_name}"
                if getattr(c, attr) is not None:
                    continue
                target_ms = cts_ms + window_sec * 1000
                if target_ms > now_ms:
                    continue  # target time hasn't happened yet
                idx = bisect.bisect_left(sorted_ts, target_ms)
                if idx >= len(sorted_ts) or sorted_ts[idx] - target_ms > tolerance_ms:
                    if now_ms - target_ms <= fresh_ms:
                        fresh_misses += 1
                    continue  # no 1m close near enough the target — leave pending
                target_price = price_history[sorted_ts[idx]]
                # Raw forward return — direction-agnostic, measured from the
                # state's own close price, not the live price at eval time.
                ret = (target_price - c.state_price) / c.state_price
                setattr(c, attr, round(ret, 6))
                c.outcome_measured_at[window_name] = now.isoformat()
                target_dt = datetime.fromtimestamp(target_ms / 1000, tz=timezone.utc)
                c.outcome_target_time[window_name] = target_dt.isoformat()
                filled.append({"state_ts": c.timestamp, "window": window_name, "return": round(ret, 6)})
                changed = True
        if changed:
            self._save()
        return {"filled": filled, "fresh_misses": fresh_misses}

    def recent(self, limit: int = 50) -> list[dict]:
        return [c.to_dict() for c in self.candidates[-limit:]]

    def summary(self) -> dict:
        total = len(self.candidates)
        with_4h = [c for c in self.candidates if c.forward_return_4h is not None]
        wins_4h = sum(1 for c in with_4h if c.forward_return_4h > 0)
        # Per-context breakdown
        ctx_stats = {}
        for c in self.candidates:
            ctx = c.context
            if ctx not in ctx_stats:
                ctx_stats[ctx] = {"total": 0, "with_4h": 0, "wins_4h": 0, "sum_4h": 0.0}
            ctx_stats[ctx]["total"] += 1
            if c.forward_return_4h is not None:
                ctx_stats[ctx]["with_4h"] += 1
                if c.forward_return_4h > 0:
                    ctx_stats[ctx]["wins_4h"] += 1
                ctx_stats[ctx]["sum_4h"] += c.forward_return_4h
        contexts = {}
        for ctx, s in ctx_stats.items():
            contexts[ctx] = {
                "total": s["total"],
                "with_4h": s["with_4h"],
                "win_rate": round(s["wins_4h"] / s["with_4h"], 4) if s["with_4h"] else None,
                "mean_return": round(s["sum_4h"] / s["with_4h"], 6) if s["with_4h"] else None,
            }
        return {
            "total": total,
            "with_outcome_4h": len(with_4h),
            "win_rate_4h": round(wins_4h / len(with_4h), 4) if with_4h else None,
            "by_context": contexts,
        }

    def _save(self):
        os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
        # self.candidates is already capped at MAX_CANDIDATES by add() — persist
        # all of it, not some smaller slice (that used to silently drop
        # anything older than 2000 candidates from disk, ~83 days in).
        data = {
            "candidates": [c.to_dict() for c in self.candidates],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = self.file_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.file_path)

    def _load(self):
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path) as f:
                data = json.load(f)
            for d in data.get("candidates", []):
                self.candidates.append(Candidate(
                    timestamp=d["timestamp"], direction=d.get("direction", "long"),
                    # pre-rename records only had a single "price" (the live
                    # execution price) — reuse it for both until fresh data arrives
                    state_price=d.get("state_price", d.get("price")),
                    execution_price=d.get("execution_price", d.get("price")),
                    context=d.get("context", "unknown"),
                    context_confidence=d.get("context_confidence", 0),
                    decision=d.get("decision", "hold"),
                    decision_reason=d.get("decision_reason", ""),
                    market_state=d.get("market_state"),
                    source=d.get("source", "live"),
                    # new field names (post-2026-07-26)
                    forward_return_15m=d.get("forward_return_15m", d.get("outcome_15m")),
                    forward_return_30m=d.get("forward_return_30m", d.get("outcome_30m")),
                    forward_return_1h=d.get("forward_return_1h", d.get("outcome_1h")),
                    forward_return_4h=d.get("forward_return_4h", d.get("outcome_4h")),
                    outcome_measured_at=d.get("outcome_measured_at", d.get("outcome_fill_times", {})),
                    outcome_target_time=d.get("outcome_target_time", {}),
                ))
        except Exception:
            pass
