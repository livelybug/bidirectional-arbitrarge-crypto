## [P0] T3-11: Orchestrator loop (stub)

### 1. Goals
- Spin up the orchestrator interval using `ops.loopIntervalMs`, ensuring the loop starts/stops with the Nest lifecycle.
- For every discovered `TradingPairConfig`, fetch mock prices, compute forward/backward profitability (net of fees), and consult the risk engine for execution decisions.
- Honor a config-driven dry-run flag (default true) so all read actions still run/log normally while write/transaction actions are skipped.
- Emit structured logs per tick and per pair (heartbeat, prices, profit deltas, decision reasons) to prove control flow end-to-end.

### 2. Files & Touchpoints
- `src/orchestrator/orchestrator.service.ts`: primary implementation (loop orchestration, decision logic, dry-run guard, logging structure).
- `src/utils/config/config.types.ts` & `config.yaml`: extend `OpsConfig` with `dryRun: boolean` default true; expose via `ConfigService` getter.
- `src/orchestrator/orchestrator.module.ts`: no change expected beyond ensuring providers wired (already done).
- `test/orchestrator/orchestrator.service.spec.ts` (new): fake timers validating cadence and dry-run behavior.

### 3. Implementation Steps
1. **Config flag**
	- Add `dryRun: boolean` to `OpsConfig`, set default true inside schema + `config.yaml`.
	- Expose via `ConfigService.getOpsConfig()` so orchestrator can branch.
2. **Loop wiring**
	- Ensure `onModuleInit` reads `loopIntervalMs`, logs startup payload (interval, pair count, dryRun).
	- Convert `setInterval` handler into `runTick` that awaits price monitor and risk decisions sequentially, capturing opId per pair.
3. **Price + profit sampling**
	- Use existing `PriceMonitor.getPairPrices` mock; compute forward/backward profit bps minus `fees.totalFeeRateBps`.
	- Capture metrics in logs (`priceM`, `priceN`, `forwardBps`, `backwardBps`).
4. **Risk consultation**
	- For each direction call `riskManager.shouldExecute` with computed context; handle ok vs reason cases, logging at `info` or `debug` accordingly.
5. **Dry-run enforcement**
	- If `dryRun` true, still perform all read-side work (price monitor, fee/risk calculations) and emit the data into logs.
	- Skip any write-side actions (DEX swaps, bridge calls, wallet mutations) and log structured placeholders like `{ action: 'swapQuoteToBase', skipped: true, dryRun: true }` to show intent.
	- Leave TODO hook for future live execution path and unit tests toggling the flag.
6. **Error handling**
	- Wrap per-pair work in try/catch; include opId in error logs; continue loop even if a pair fails.
7. **Shutdown**
	- Ensure `onModuleDestroy` clears timers to avoid leaks (already scaffolded, verify still correct).

### 4. Testing Strategy
- Create Jest test with fake timers to assert:
  - `runTick` gets invoked per `loopIntervalMs`.
  - `PriceMonitor.getPairPrices` and `RiskManager.shouldExecute` called per pair/direction.
  - When dry-run enabled, no adapter/bridge mocks are invoked, but logs (use spies) reflect decision path.
- Include regression for dry-run flag toggle to ensure loop would attempt execution when disabled (future-proof via TODO expectation).

### 5. Definition of Done
- App boot logs heartbeat every `loopIntervalMs`, including tick-level price/decision logs.
- Dry-run flag present in config, defaults to true, and orchestrator respects it.
- Unit test covering loop cadence + dry-run behavior passes.
- `pnpm lint && pnpm test` stay green after changes.
