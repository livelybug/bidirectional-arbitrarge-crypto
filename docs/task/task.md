# Project Plan: Cross-Chain Bi-Directional Arbitrage Bot (v1.0)

1. Project Scope & Objectives
   - Scope: Implement a TypeScript arbitrage bot that executes bi-directional cross-chain cycles using DEXs and bridges, with risk management, logging, and operational gas reserves.
   - Objectives:
     - Continuous 1s price monitoring and profit evaluation (forward/backward).
     - Full-amount execution with configurable caps; bridge back 90–95%; retain 3% profit for gas.
     - Robust risk, slippage, fee handling; reliable bridging and settlement logging.
     - Modular codebase matching FRD structure; behavioral parity with Python reference.

2. High-Level Phases
   2.1. Planning & Design
   2.2. Development
   2.3. Testing & Validation
   2.4. Deployment & Operations
   2.5. Post-Deployment Optimization

3. On-Chain Implementation Follow-Up
  - Principle: For every abstract component or interface (e.g., PriceMonitor, DexAdapter, BridgeAdapter, Wallet utilities, RiskManager, Orchestrator), there must be at least one concrete implementation exercised against a live blockchain network—first on testnets, then via carefully scoped mainnet trials—to validate assumptions about latency, error modes, fees, and slippage.
  - Approach:
    - Prioritize read-only interactions on testnets (quotes, balances, fee estimates) to validate configuration, schemas, and adapter contracts before sending any real transactions.
    - Progress to tiny-amount swaps and bridge transfers under strict caps and manual operator oversight, using the existing risk and logging infrastructure to observe real behavior.
    - For each Phase 2 sub-task under T3c–T8, treat on-chain runs and their logs/tx hashes as required artifacts before considering the corresponding abstraction “production-ready”.

4. Key Tasks per Phase
  4.1. Planning & Design
   - T1: Requirements finalization
     - Align FRD with architecture; confirm thresholds, fee model, caps.
     - Deliverable: Signed-off FRD and architecture notes.
     - Success: No open requirement gaps.
   - T2: Solution architecture
     - Define module interfaces (price_monitor, dex, bridge, risk_control, utils).
     - Deliverable: Module interface specs + sequence diagrams.
     - Success: Stakeholder approval.

  4.2. Development
  - T3: Project bootstrapping
     - Initialize TypeScript project; add package.json, linting, logging infra.
     - Deliverable: Repo scaffold; build passes.
     - Success: CI green.
     - Implementation detail: (docs/task/task-detail/T3- Project_bootstrapping.md)
  - T3b: Pair & route discovery
     - Implement ConfigService-backed discovery of trading pairs and arbitrage routes at startup using:
       - Global base/quote token lists from `tokens` config.
       - Per-chain `tokenList` (token inventories) and `dexList` (supported DEXes) from `chains` config.
     - Build in-memory `TradingPairConfig` + route entries `(chainM, dexJ) → (chainN, dexK)` for all token pairs that appear on at least two venues (same-chain or cross-chain).
     - Enforce fast-fail on misconfigured tokens (base/quote tokens missing from all chain `tokenList`s).
     - Deliverable: Discovery service/module + tests; documented contract for Orchestrator and PriceMonitor.
     - Success: Deterministic list of eligible pairs/routes computed at startup; invalid config surfaces as clear errors.
     - Implementation detail: (docs/task/task-detail/T3b-Pair&route discovery.md)
   - T3c: Wallet & config utilities
     - Secure wallet handling; config.yaml parsing with Zod-backed schema; logger.
     - Implement typed config accessors for:
       - Global `tokens` (base/quote lists) and per-chain `tokenList`/`dexList`.
       - Bridge, risk, fees, ops, logging, wallets.
     - Ensure config schema matches `arch_general.md` and `schema_validation.md` (no static trading pairs; discovery is runtime-only).
     - Deliverable: utils/wallet.ts, utils/logger.ts; config.yaml; config.types.ts + config.schema.ts.
     - Success: Secrets not in code; logs structured and complete; `config.yaml` validates and supports dynamic pair/route discovery.
     - Phase 2: Live RPC and wallet smoke tests
       - Connect wallet utilities to at least one public RPC endpoint per supported chain (testnets first), load a non-production key from keystore/env, and perform read-only balance and nonce checks plus a single low-value test transaction per chain.
       - Verification: confirm that key management, RPC selection, and basic signing/broadcast flows work as expected, and that misconfiguration (bad RPC URL, wrong chainId) fails fast with clear errors.
   - T4: Price monitoring
     - Implement API-based quotes for dynamically discovered trading pairs (base/quote) across configured DEX J/K (same-chain or cross-chain).
     - Integrate with discovery outputs: `PriceMonitor` consumes `TradingPairConfig` to fetch `priceM` and `priceN` per pair/route.
     - Maintain 1s loop semantics for price fetching while allowing multiple pairs/routes to be evaluated per tick.
     - Deliverable: price_monitor.ts with dual-venue fetch per pair + rate-limit handling.
    - Success: Stable price feed, <300ms avg fetch per chain/DEX; supports multiple pairs concurrently.
    - Phase 2: On-chain price monitoring
       - Wire `PriceMonitor` to real DEX/read-only RPC calls (e.g. Uniswap V3 / PancakeSwap V3 pools) on at least one supported test env per chain, verifying prices, latencies, and error modes against FRD assumptions.
       - Verification: run the price loop against live test env pools for a representative `TradingPairConfig[]`, capture structured logs and sample outputs, and compare against a Python or SDK reference implementation; later, repeat read-only queries on mainnet with production RPCs.
  - T5: DEX integrations
     - Uniswap V3 swaps (buy/sell with slippage cap) and PancakeSwap V3 as primary DEX adapters, with Velodrome V2 as an additional template venue. PriceMonitor consumes quotes via a `(chainId, dexKey)` adapter registry (DexQuoteProvider) and uses only the quote path; execution paths share the same adapters with slippage caps enforced.
     - Deliverable: dex/uniswap_v3.ts, dex/pancakeswap.ts with unit tests.
     - Success: Accurate quote vs execution delta within configured slippage (≤3%).
     - Phase 2: On-chain DEX adapter validation (testnets → guarded mainnet)
       - Implement real read-only integrations for `DexAdapter` (pool lookups, on-chain quoting) against Uniswap V3 (Arbitrum/Base testnets) and PancakeSwap V3 (BSC testnet), using SDKs or direct RPC calls with configured pool addresses and fee tiers.
       - Execute tiny-amount test swaps on testnets for a small set of routes, validating that `estimate*` methods bound actual execution prices within configured slippage and that swap receipts contain real tx hashes and final amounts.
       - Verification: for each adapter, produce a short run log and summary (quotes vs executed prices, slippage, failures) and, once stable on testnets, perform a limited number of guarded mainnet swaps with minimal notional and strict risk caps.
  - T6: Bridge integration
     - Stargate bridging (TokenA, USDT) with fee estimation and settlement polling.
     - Deliverable: bridge/stargate.ts.
     - Success: Confirmed settlement logs with accurate post-bridge balances.
     - Phase 2: On-chain bridge trials (testnets → guarded mainnet)
       - Integrate the `BridgeAdapter` with a live Stargate (or equivalent) deployment on testnets, exercising fee estimation, submit, and settlement polling flows for small USDT amounts between two supported chains.
       - Verification: record transferIds, settlement statuses, and final balances for a sample of testnet bridge operations; once behavior is well understood, perform one or more guarded mainnet bridge tests with hard-coded low amounts and explicit operator approval.
  - T7: Risk management
     - Implement min profit threshold, stop-loss, position caps, slippage, fee model.
     - Deliverable: risk_control.ts.
     - Success: Correct gatekeeping across scenarios; caps enforce limits.
     - Phase 2: On-chain risk & PnL validation
       - Replay a small set of real on-chain trades (from testnet/mainnet runs of the orchestrator) through the RiskManager, confirming that historical decisions (execute vs skip) would match actual realized PnL after fees, slippage, and bridge costs.
       - Verification: produce a short “risk vs realized PnL” report for selected test runs, highlighting any cases where abstract thresholds need tuning based on real execution behavior.
  - T8: Main orchestrator
     - Implement 1s loop that:
       - At startup, pulls discovered `TradingPairConfig`+route entries from discovery service.
       - On each tick, iterates over all candidate pairs/routes, fetches prices via PriceMonitor, and evaluates forward/backward profitability.
       - Delegates to RiskManager with per-pair `PairRuntimeState` and global state; collects candidate `ExecutionPlan`s.
       - Selects at most one plan per tick (e.g., highest expected profit that passes risk checks) to simplify exposure and funding races.
       - Executes the chosen plan, including 90–95% rebalance and 3% gas reserve behavior.
     - Deliverable: src/main.ts orchestrator wiring + integration with discovery, price_monitor, dex, bridge, risk_control.
     - Success: End-to-end dry-run succeeds; correct fund cycling across multiple pairs/routes; at most one execution per tick.
     - Phase 2: Live-chain orchestrator smoke tests
       - Run the full 1s loop against a testnet-only configuration (testnet chains, test pools, test bridge) with very small notional sizes, confirming that quotes, executions, and bridge operations can complete end-to-end under real network conditions.
       - Verification: capture a short continuous run (e.g. 15–60 minutes) with structured logs for decisions, swaps, bridges, and PnL, and review for unexpected failures, latency spikes, or risk violations before any mainnet activation.

   4.3. Testing & Validation
   - T10: Unit & integration tests
     - Test profit calc, slippage, fee aggregation, bridge flows.
     - Deliverable: Test suite with coverage report.
     - Success: ≥80% coverage; key paths validated.
   - T11: Simulation and replay
     - Backtest using recorded prices; validate thresholds and PnL math.
     - Deliverable: Simulation scripts/results.
     - Success: PnL within expected ranges; no false-positive executions.
   - T12: Performance & reliability
     - Load tests on 1s loop; error handling, retries/backoff; rate-limit compliance.
     - Deliverable: Perf report; resilience checklist.
     - Success: Stable 24h run without crash; controlled retries.

   4.4. Deployment & Operations
   - T13: Deployment packaging
     - Build scripts, containerization (optional), environment configs.
     - Deliverable: Deployable artifact; runbook.
     - Success: Repeatable deployments; config-driven.
   - T14: Observability
     - Logging enrichment; metrics for executions, fees, profits, bridge durations.
     - Deliverable: Log format + dashboards (optional).
     - Success: Operators can trace end-to-end cycles quickly.

   4.5. Post-Deployment Optimization
   - T15: Threshold tuning
     - Adjust profit threshold (1.5–2.2%) based on live performance.
     - Deliverable: Tuning report; config updates.
     - Success: Improved execution quality without excess churn.
   - T16: Supported platforms expansion
     - Add Hop/Synapse bridges; Velodrome; Sushi/QuickSwap routes.
     - Deliverable: New adapters + tests.
     - Success: Stable cross-chain operations on added routes.
   - T17: Safety enhancements
     - Dynamic gas estimation; API redundancy; fail-safe pausing.
     - Deliverable: Features + documentation.
     - Success: Reduced failure rates; faster recovery.

1. Deliverables
   - D1: Final FRD and architecture docs (T1–T2).
   - D2: TS codebase modules (T3–T9).
   - D3: Test suite and simulation reports (T10–T12).
   - D4: Deployment artifacts and runbook (T13).
   - D5: Observability and dashboards (T14).
   - D6: Tuning and expansion updates (T15–T16).
   - D7: Safety features and docs (T17).

2. Success Criteria
   - Planning & Design: Approved FRD; clear interfaces; no open questions.
   - Development: CI green; modules pass unit tests; orchestrator performs full cycle.
   - Testing & Validation: ≥80% coverage; backtests consistent with expected PnL; stable 24h soak.
   - Deployment & Operations: One-click deploy; configurable per environment; logs enable root-cause analysis.
   - Post-Deployment Optimization: Demonstrated profit capture with controlled risk; expanded chain/DEX support without regressions.

## Todos
*  Extend Orchestrator/PriceMonitor to handle multiple candidate routes per token pair (e.g. (J1–K1), (J2–K1), (J1–K2)) and select at most one execution plan per tick based on expected profit and risk constraints.
*  Add per-pair risk/fee override support (optional fields on `TradingPairConfig`) and ensure RiskManager respects both global and per-pair settings.
*  Plan per-pair overrides and future extensions:
   - Keep discovery as the single source of truth for the universe of arbitrageable routes (`TradingPairConfig[]`) derived from `tokens` and `chains`; per-pair overrides should **decorate or constrain** this universe, not introduce new pairs.
   - Attach optional override fields directly to `TradingPairConfig` (and its config representation) for at least:
     - `minProfitRateBps` – tighten or loosen the execution threshold for a specific pair relative to global `risk.minProfitRateBps`.
     - `slippageBps` – per-pair slippage cap that can differ from global `risk.slippageBps`.
     - `positionCaps` – per-pair caps (reusing `PositionCaps`) that can be stricter than global `risk.positionCaps`.
   - Treat future candidates (for later phases) as additional optional fields, e.g. per-pair bridge preferences, DEX allowlists/denylists, or per-route pause flags, without changing the core discovery flow.
   - In Orchestrator/RiskManager, resolve **effective** parameters for each pair via a pure helper, using the rule: "use per-pair override if present, otherwise fall back to global `risk`/`fees`/`ops`", so behavior stays testable and overrides cannot silently widen global limits.