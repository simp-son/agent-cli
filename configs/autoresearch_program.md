# Autoresearch Program: APEX Config Optimization

## Objective
Optimize the single entry threshold parameter for BTC-PERP mainnet trading by replaying
historical trades through the backtest harness and maximizing net PnL.

## Mutable File
`apex_config.json`

## Run Command
```
python3 scripts/backtest_apex.py --config apex_config.json --trades data/cli/trades.jsonl
```

## Target Metric
`net_pnl` (highest)

## Secondary Metrics (monitor but don't optimize directly)
- `win_rate` — should stay above 40%
- `fdr` — should stay below 30%
- `trades` — should stay above 5 (quality gate)
- `profit_factor` — should stay above 1.0

## Single Parameter: radar_score_threshold

| Parameter             | Min | Max | Step | Default |
|-----------------------|-----|-----|------|---------|
| radar_score_threshold | 120 | 280 | 10   | 170     |

All other parameters are fixed. Do not modify them.

## Research Directions

1. **High FDR (>30%)**: Raise `radar_score_threshold` toward 250 — filter low-quality entries.
2. **Low Win Rate (<40%)**: Raise `radar_score_threshold` toward 220 — require higher conviction.
3. **Too few trades**: Lower `radar_score_threshold` toward 140 — loosen entry criteria.
4. **Healthy metrics**: Try lowering `radar_score_threshold` toward 140 to capture more trades.
5. **Fee Drag Emergency**: Raise `radar_score_threshold` to [220, 280].

## Workflow

1. Start with current `apex_config.json` as baseline
2. Run backtest to get baseline metrics
3. Pick a direction based on the metrics
4. Change `radar_score_threshold` by one step (±10)
5. Re-run backtest and compare `net_pnl`
6. Keep if improved, revert if not
7. Repeat until no improvement found

## Quality Gates
- Must produce at least 5 round trips
- `profit_factor` must be > 1.0
- `fdr` must be < 50%
