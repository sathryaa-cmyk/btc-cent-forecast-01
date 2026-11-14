"""btc-cent-forecast-01 entry: shrunk 48h-trend + 24h mean-reversion blend.

Forecasts the BTC (cbBTC/USDC, Orca) close 240 minutes after each checkpoint
from the 4,320 one-minute closes up to the checkpoint.

Method (a small, bounded adjustment to persistence, chosen on the kit's
practice cases plus hourly replay checkpoints cut from the same recording):
  guess = last + 0.20 * (mean24h - last) + last * trend_move
where trend_move is the OLS slope of log price over the last 48 hours,
extrapolated 240 minutes and damped to 35% (clipped to +/-2%), and the
total move is capped at +/-1% of the last price.

Why: on the practice replay, short-horizon trend extrapolation alone and
mean reversion alone each beat persistence on some checkpoints and lose on
others; the blend beats persistence on all three validation sets (the 5
official practice cases with known answers, 64 hourly checkpoints, and 16
4h-spaced checkpoints), while neighbouring parameters give nearly the same
score, so the choice is not a knife-edge fit. The move cap bounds the
downside if the final 48h window runs in a different regime: the worst a
wrong signal can do is add ~1% to one case's error.

Protocol (per RULES.txt): read every <id>.in in $MAKEFUN_INPUT_DIR
(default /input), write <id>.out to $MAKEFUN_OUTPUT_DIR (default /output)
as {"forecasts": [{"case": <id>, "price": <guess>}]}, price rounded to the
grid's 5 decimals and kept inside (0, 10,000,000). Stdlib only, no network,
deterministic: the same case always yields the same bytes.
"""

import json
import math
import os
import statistics
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999

# Tuned constants (see module docstring; validated on the practice replay).
MEAN_LOOKBACK_MIN = 1440          # 24 h mean for the reversion anchor
MEAN_WEIGHT = 0.20                # pull toward the 24 h mean
TREND_LOOKBACK_MIN = 2880         # 48 h window for the OLS log-price slope
TREND_DAMP = 0.35                 # extrapolate the 48 h slope at 35%
TREND_CAP = 0.02                  # cap the trend move at +/-2%
TOTAL_MOVE_CAP = 0.01             # cap the total move at +/-1% of last price
HORIZON_MIN = 240


def price5(x):
    """Keep a price on the grid's 5 decimals and inside (0, 10,000,000)."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def trend_move(prices):
    """Damped 240-minute move implied by the OLS slope of log price over the
    last TREND_LOOKBACK_MIN minutes, as a fraction of the last price."""
    window = prices[-TREND_LOOKBACK_MIN:]
    n = len(window)
    if n < 2:
        return 0.0
    logs = [math.log(v) for v in window]
    mean_i = (n - 1) / 2.0
    mean_log = sum(logs) / n
    sxx = sum((i - mean_i) ** 2 for i in range(n))
    if sxx == 0:
        return 0.0
    sxy = sum((i - mean_i) * (logs[i] - mean_log) for i in range(n))
    slope = sxy / sxx  # log-return per minute
    move = slope * HORIZON_MIN * TREND_DAMP
    return max(-TREND_CAP, min(TREND_CAP, move))


def forecast(prices):
    """One forecast for the close HORIZON_MIN minutes after the last price.

    Pure arithmetic on the given closes: no randomness, no I/O, no clock,
    so two runs on the same case write the same bytes.
    """
    if not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not math.isfinite(last) or last <= 0:
        raise ValueError("last price is not a positive finite number")
    mean24 = statistics.fmean(prices[-MEAN_LOOKBACK_MIN:])
    move = MEAN_WEIGHT * (mean24 - last) + last * trend_move(prices)
    cap = TOTAL_MOVE_CAP * last
    move = max(-cap, min(cap, move))
    guess = price5(last + move)
    assert math.isfinite(guess) and 0 < guess < 10_000_000
    return guess


def main():
    in_dir = Path(INPUT_DIR)
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for p in in_dir.iterdir() if p.name.endswith(".in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        case = json.loads(path.read_text(encoding="utf-8"))
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{path.name} does not hold exactly one market")
        prices = markets[0].get("prices")
        if not isinstance(prices, list) or not prices:
            raise ValueError(f"{path.name} market has no prices")
        guess = forecast([float(v) for v in prices])
        out = {"forecasts": [{"case": case_id, "price": guess}]}
        (out_dir / f"{case_id}.out").write_text(
            json.dumps(out) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
