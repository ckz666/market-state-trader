"""
Shadow recorder — observes what the RESEARCH candidates would do, live,
without trading anything.

Why this exists: the paper trader runs `context.classify()` ->
`strategy.decide()`, the original 5-regime engine. That is a completely
different strategy from the one the research pipeline validated
(`decision_rule_v1`), so its P&L says nothing about the research
candidates. This module runs the research rules in parallel, records
what they would have done, and — critically — captures the live order
book at each signal.

That last part is the point. The project's single largest unresolved
caveat (see data/reports/slippage_measurement.md) is that slippage was
measured in a calm market while the strategy fires ONLY at
Volatility==Q5, when spreads widen. That question cannot be answered
offline from klines. It can only be answered by looking at the book at
the moment a signal actually fires.

What is recorded per signal:
  - the frozen decision (`decision_rule_v1`: LPL==Q1 & Vol==Q5)
  - an order-book snapshot with measured slippage at several notionals
  - a shadow position held 24h (`decision_rule_v4`, the best candidate)
  - the Phase D recovery-state path (deep threshold -0.75%, w=120m),
    recorded as observation only — no exit is simulated, so the 24h
    outcome stays comparable to the backtests

NOTHING here is a parameter choice. Every threshold is loaded frozen
from data/frozen_params.json or is a constant published in the reports.
Live code must never re-fit.
"""
import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

import pandas as pd

FROZEN_PARAMS_PATH = "data/frozen_params.json"
SHADOW_STORE_PATH = "data/shadow_signals.json"

# All frozen, all published — see README_RESEARCH_SUMMARY.md
HOLD_MINUTES = 1440          # decision_rule_v4 (24h)
BASELINE_HOLD_MINUTES = 240  # decision_rule_v1 (4h), tracked side by side
DEEP_THRESHOLD = -0.0075     # Phase D §11
RECOVERY_TIMEOUT_MIN = 120   # Phase D §23 (Action Class II, w=120m)
SLIPPAGE_NOTIONALS = [1_000, 10_000, 100_000]
MAX_STORED = 2000


def _walk_book(levels, notional_usdt, mid):
    """VWAP slippage in bps for a market order walking `levels`."""
    remaining, cost, qty = notional_usdt, 0.0, 0.0
    for price, size in levels:
        take = min(remaining, price * size)
        q = take / price
        cost += q * price
        qty += q
        remaining -= take
        if remaining <= 0:
            break
    if remaining > 0 or qty == 0:
        return None
    return abs(cost / qty - mid) / mid * 10000


@dataclass
class ShadowPosition:
    """A hypothetical 24h long opened at a decision_rule_v1 signal."""
    signal_ts: str
    entry_ts: str
    entry_price: float
    exit_due_ts: str
    lpl_value: float
    lpl_quintile: str
    vol_value: float
    vol_quintile: str
    entry_slippage_bps: dict = field(default_factory=dict)
    entry_spread_bps: float = None
    # live path tracking
    current_price: float = None
    unrealized_pct: float = None
    mae_so_far_pct: float = 0.0
    mfe_so_far_pct: float = 0.0
    # Phase D observation (recorded, never acted on)
    deep_episode_started_ts: str = None
    deep_episodes_count: int = 0
    currently_deep: bool = False
    recovery_timeout_would_fire_ts: str = None
    # settled
    closed: bool = False
    exit_price: float = None
    exit_ts: str = None
    gross_return_pct: float = None
    baseline_4h_price: float = None
    baseline_4h_return_pct: float = None

    def to_dict(self):
        return asdict(self)


class ShadowRecorder:
    """Observation only. Never places or simulates an order."""

    def __init__(self, params_path=FROZEN_PARAMS_PATH, store_path=SHADOW_STORE_PATH):
        self.store_path = store_path
        self.params = None
        self.load_error = None
        try:
            with open(params_path) as f:
                self.params = json.load(f)
        except Exception as e:
            self.load_error = f"{type(e).__name__}: {e}"
        self.open_positions: list[ShadowPosition] = []
        self.closed_positions: list[dict] = []
        self.signals_seen = 0
        self._load()

    # ── frozen transforms ────────────────────────────────────────────
    def _lpl(self, bb_position: float, vwap_distance: float) -> float:
        p = self.params["lpl"]
        return ((bb_position - p["bb_mean"]) / p["bb_std"] +
                (vwap_distance - p["vwap_mean"]) / p["vwap_std"]) / 2

    @staticmethod
    def _quintile(value: float, edges: list) -> str:
        labels = ["Q1", "Q2", "Q3", "Q4", "Q5"]
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            if (value > lo or i == 0) and value <= hi:
                return labels[i]
        return labels[-1]

    def classify(self, state) -> dict | None:
        """Frozen decision_rule_v1 applied to a live MarketState."""
        if self.params is None:
            return None
        loc = state.state_1h.price_location
        lpl = self._lpl(loc.bb_position, loc.vwap_distance)
        vol = state.state_1h.volatility.atr_norm
        lpl_q = self._quintile(lpl, self.params["lpl_quintile_edges"])
        vol_q = self._quintile(vol, self.params["vol_quintile_edges"])
        decision = "no_signal"
        if lpl_q == "Q1" and vol_q == "Q5":
            decision = "long_candidate"
        elif lpl_q == "Q5" and vol_q == "Q5":
            decision = "avoid_long"
        return {"lpl": lpl, "lpl_q": lpl_q, "vol": vol, "vol_q": vol_q, "decision": decision}

    # ── the two hooks research_loop.py calls ──────────────────────────────────
    def on_new_state(self, state, live_price: float, order_book: dict | None) -> dict | None:
        """Called once per closed 1h candle. Opens a shadow position on a
        long_candidate. Option A: skipped while one is already open."""
        cls = self.classify(state)
        if cls is None or cls["decision"] != "long_candidate":
            return cls
        self.signals_seen += 1
        if self.open_positions:
            cls["skipped_option_a"] = True
            return cls

        now = pd.Timestamp.now("UTC")
        slip, spread = {}, None
        if order_book and order_book.get("bids") and order_book.get("asks"):
            bids, asks = order_book["bids"], order_book["asks"]
            mid = (bids[0][0] + asks[0][0]) / 2
            spread = (asks[0][0] - bids[0][0]) / mid * 10000
            for n in SLIPPAGE_NOTIONALS:
                b = _walk_book(asks, n, mid)
                if b is not None:
                    slip[str(n)] = round(b, 4)

        pos = ShadowPosition(
            signal_ts=state.timestamp.isoformat(),
            entry_ts=now.isoformat(),
            entry_price=live_price,
            exit_due_ts=(now + pd.Timedelta(minutes=HOLD_MINUTES)).isoformat(),
            lpl_value=round(cls["lpl"], 6), lpl_quintile=cls["lpl_q"],
            vol_value=round(cls["vol"], 6), vol_quintile=cls["vol_q"],
            entry_slippage_bps=slip,
            entry_spread_bps=round(spread, 4) if spread is not None else None,
            current_price=live_price, unrealized_pct=0.0,
        )
        self.open_positions.append(pos)
        self._save()
        cls["opened"] = True
        return cls

    def on_price(self, price: float):
        """Called every cycle. Updates paths, settles expired positions."""
        now = pd.Timestamp.now("UTC")
        changed = False
        for pos in list(self.open_positions):
            pos.current_price = price
            ret = (price - pos.entry_price) / pos.entry_price
            pos.unrealized_pct = round(ret * 100, 4)
            pos.mae_so_far_pct = round(min(pos.mae_so_far_pct, ret * 100), 4)
            pos.mfe_so_far_pct = round(max(pos.mfe_so_far_pct, ret * 100), 4)

            # Phase D recovery-state observation (never acted on)
            was_deep = pos.currently_deep
            pos.currently_deep = ret <= DEEP_THRESHOLD
            if pos.currently_deep and not was_deep:
                pos.deep_episodes_count += 1
                pos.deep_episode_started_ts = now.isoformat()
            elif not pos.currently_deep and was_deep:
                pos.deep_episode_started_ts = None
            if (pos.currently_deep and pos.deep_episode_started_ts
                    and pos.recovery_timeout_would_fire_ts is None):
                started = pd.Timestamp(pos.deep_episode_started_ts)
                if (now - started).total_seconds() / 60 >= RECOVERY_TIMEOUT_MIN:
                    pos.recovery_timeout_would_fire_ts = now.isoformat()
                    changed = True

            # 4h baseline snapshot, for the v1-vs-v4 comparison
            if pos.baseline_4h_price is None:
                entered = pd.Timestamp(pos.entry_ts)
                if (now - entered).total_seconds() / 60 >= BASELINE_HOLD_MINUTES:
                    pos.baseline_4h_price = price
                    pos.baseline_4h_return_pct = round(ret * 100, 4)
                    changed = True

            if now >= pd.Timestamp(pos.exit_due_ts):
                pos.closed = True
                pos.exit_price = price
                pos.exit_ts = now.isoformat()
                pos.gross_return_pct = round(ret * 100, 4)
                self.open_positions.remove(pos)
                self.closed_positions.append(pos.to_dict())
                changed = True
        if changed:
            self._save()

    # ── persistence / status ─────────────────────────────────────────
    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            with open(self.store_path, "w") as f:
                json.dump({
                    "updated": datetime.now(timezone.utc).isoformat(),
                    "signals_seen": self.signals_seen,
                    "open": [p.to_dict() for p in self.open_positions],
                    "closed": self.closed_positions[-MAX_STORED:],
                }, f, indent=2)
        except Exception:
            pass  # never let recording break the trading loop

    def _load(self):
        try:
            with open(self.store_path) as f:
                d = json.load(f)
            self.signals_seen = d.get("signals_seen", 0)
            self.closed_positions = d.get("closed", [])
            self.open_positions = [ShadowPosition(**p) for p in d.get("open", [])]
        except Exception:
            pass

    def status(self) -> dict:
        closed = self.closed_positions
        rets = [c["gross_return_pct"] for c in closed if c.get("gross_return_pct") is not None]
        base = [c["baseline_4h_return_pct"] for c in closed if c.get("baseline_4h_return_pct") is not None]
        spreads = [c["entry_spread_bps"] for c in closed + [p.to_dict() for p in self.open_positions]
                   if c.get("entry_spread_bps") is not None]
        return {
            "ready": self.params is not None,
            "load_error": self.load_error,
            "signals_seen": self.signals_seen,
            "open_count": len(self.open_positions),
            "closed_count": len(closed),
            "open": [p.to_dict() for p in self.open_positions],
            "recent_closed": closed[-20:][::-1],
            "summary": {
                "n_settled": len(rets),
                "win_rate": round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1) if rets else None,
                "median_24h_pct": round(sorted(rets)[len(rets)//2], 4) if rets else None,
                "mean_24h_pct": round(sum(rets)/len(rets), 4) if rets else None,
                "mean_4h_baseline_pct": round(sum(base)/len(base), 4) if base else None,
                "mean_entry_spread_bps": round(sum(spreads)/len(spreads), 4) if spreads else None,
            },
        }
