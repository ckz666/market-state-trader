"""
Storage — persists entry candidates with full MarketState + outcomes.
"""
import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional

import mst_config as config


@dataclass
class Candidate:
    timestamp: str
    direction: str
    price: float
    context: str
    context_confidence: float
    decision: str
    decision_reason: str
    market_state: Optional[dict] = None
    outcome_15m: Optional[float] = None
    outcome_30m: Optional[float] = None
    outcome_1h: Optional[float] = None
    outcome_4h: Optional[float] = None
    outcome_fill_times: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        return d


class CandidateLogger:
    OUTCOME_WINDOWS = {"15m": 15*60, "30m": 30*60, "1h": 60*60, "4h": 4*60*60}

    def __init__(self):
        self.candidates: list[Candidate] = []
        self._load()

    def add(self, c: Candidate):
        self.candidates.append(c)
        if len(self.candidates) > 5000:
            self.candidates = self.candidates[-5000:]
        self._save()

    def update_outcomes(self, current_price: float):
        now = datetime.now(timezone.utc)
        changed = False
        for c in self.candidates:
            try:
                cts = datetime.fromisoformat(c.timestamp)
                if cts.tzinfo is None:
                    cts = cts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
            age = (now - cts).total_seconds()
            if age < 0: continue
            for window_name, window_sec in self.OUTCOME_WINDOWS.items():
                attr = f"outcome_{window_name}"
                if getattr(c, attr) is not None: continue
                if age < window_sec: continue
                ret = (current_price - c.price) / c.price
                if c.direction == "short":
                    ret = -ret
                setattr(c, attr, round(ret, 6))
                c.outcome_fill_times[window_name] = now.isoformat()
                changed = True
        if changed:
            self._save()

    def recent(self, limit: int = 50) -> list[dict]:
        return [c.to_dict() for c in self.candidates[-limit:]]

    def summary(self) -> dict:
        total = len(self.candidates)
        with_4h = [c for c in self.candidates if c.outcome_4h is not None]
        wins_4h = sum(1 for c in with_4h if c.outcome_4h > 0)
        # Per-context breakdown
        ctx_stats = {}
        for c in self.candidates:
            ctx = c.context
            if ctx not in ctx_stats:
                ctx_stats[ctx] = {"total": 0, "with_4h": 0, "wins_4h": 0, "sum_4h": 0.0}
            ctx_stats[ctx]["total"] += 1
            if c.outcome_4h is not None:
                ctx_stats[ctx]["with_4h"] += 1
                if c.outcome_4h > 0:
                    ctx_stats[ctx]["wins_4h"] += 1
                ctx_stats[ctx]["sum_4h"] += c.outcome_4h
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
        os.makedirs(config.DATA_DIR, exist_ok=True)
        data = {
            "candidates": [c.to_dict() for c in self.candidates[-2000:]],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = config.CANDIDATES_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, config.CANDIDATES_FILE)

    def _load(self):
        if not os.path.exists(config.CANDIDATES_FILE):
            return
        try:
            with open(config.CANDIDATES_FILE) as f:
                data = json.load(f)
            for d in data.get("candidates", []):
                self.candidates.append(Candidate(
                    timestamp=d["timestamp"], direction=d.get("direction", "long"),
                    price=d["price"], context=d.get("context", "unknown"),
                    context_confidence=d.get("context_confidence", 0),
                    decision=d.get("decision", "hold"),
                    decision_reason=d.get("decision_reason", ""),
                    market_state=d.get("market_state"),
                    outcome_15m=d.get("outcome_15m"),
                    outcome_30m=d.get("outcome_30m"),
                    outcome_1h=d.get("outcome_1h"),
                    outcome_4h=d.get("outcome_4h"),
                    outcome_fill_times=d.get("outcome_fill_times", {}),
                ))
        except Exception:
            pass
