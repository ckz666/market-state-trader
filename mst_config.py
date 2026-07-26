"""
Market State Trader — configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Exchange
EXCHANGE = os.getenv("EXCHANGE", "bitget")  # "bitget" | "binance"
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
CYCLE_INTERVAL = 60  # seconds between cycles

# Bitget
BITGET_API_KEY = os.getenv("BITGET_API_KEY", "")
BITGET_SECRET = os.getenv("BITGET_SECRET", "")
BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE", "")

# Paper trading
INITIAL_BALANCE = float(os.getenv("PAPER_BALANCE", "10000"))
MAX_LEVERAGE = int(os.getenv("MAX_LEVERAGE", "5"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "0.20"))
SL_ATR_MULT = 1.0
TP_ATR_MULT = 3.0
TAKER_FEE = 0.0006

# Context thresholds (from empirical analysis)
BB_EXTENDED = 1.00       # bb_position above this = extended
BB_FAVORABLE = 0.90      # bb_position below this = favorable entry
DIVERGENCE_THRESHOLD = 0.01  # trend_momentum_divergence above this = diverged
ADX_TRENDING = 25
MOMENTUM_STRONG = 0.50

# Storage
DATA_DIR = "data"
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.json")
TRADE_HISTORY_FILE = os.path.join(DATA_DIR, "trades.json")
STATE_FILE = os.path.join(DATA_DIR, "state.json")

# Server
HOST = "0.0.0.0"
PORT = 8081
