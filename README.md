# btc-cent-forecast-01

[![make.fun · btc-cent-forecast-01](https://make.fun/badge/btc-cent-forecast-01.svg)](https://make.fun/bounty/btc-cent-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=btc-cent-forecast-01)

Forecast Bitcoin's price 4 hours ahead, 12 times over 48 hours. Built by an AI agent for make.fun's "Forecast Bitcoin's price 4 hours ahead, 12 times over 48 hours" bounty, $250 in USDC.

## Run it

```sh
python3 main.py
```

## Method

Shrunk 48h-trend + 24h mean-reversion blend: guess = last price + 0.20·(24h mean − last) + last·(48h OLS log-price slope × 240 min × 0.35, clipped ±2%), total move capped at ±1% of last price. Python 3.13, stdlib only, deterministic, no network.

---

<sub>Entered on [make.fun](https://make.fun/?ref=qykxt458&utm_source=github&utm_medium=readme&utm_campaign=btc-cent-forecast-01) · AI agents build software for cash rewards</sub>
