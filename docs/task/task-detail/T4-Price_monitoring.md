## T4: Price Monitoring – Phase 1 Task Breakdown

### Scope & Assumptions (Phase 1)

- Cover core, production-lean price monitoring for **all discovered `TradingPairConfig` routes**, but **without** full-blown circuit-breakers, backoff strategies, or sophisticated caching.
- Use the existing discovery output (`PairDiscoveryService` + `TradingPairConfig[]`) and config plumbing (`ConfigService`, `config.yaml`) as **given**; T4 **does not** modify discovery or config schema.
- Treat DEX quoting as an **abstract dependency**: Phase 1 focuses on the `PriceMonitor` interface and orchestration, while concrete DEX quote implementations are aligned with T5.
- Maintain 1s loop semantics by ensuring `PriceMonitor` is efficient and composable in the Orchestrator (non-blocking per pair, able to handle multiple pairs/routes per tick).

### Phase 1 Goals

1. Define a clear, testable `PriceMonitor` contract aligned with `arch_general.md` and `TradingPairConfig`.
2. Implement a Nest-based `PriceMonitorModule` / `PriceMonitorService` under `src/price_monitor/` that can fetch dual-venue prices for any discovered pair/route.
3. Integrate `PriceMonitor` cleanly with discovery outputs (consume `TradingPairConfig` only, no raw config access).
4. Provide unit and light integration tests showing stable, multi-pair price fetching suitable for a 1s orchestrator loop.

---

### Task Breakdown (Phase 1)

Effort scale: **XS / S / M / L / XL**  
Priority: **P0 (must-have)**, **P1 (nice-to-have for Phase 1)**, **P2 (later phases)**

- [P0] **T4.1: Refine `PriceMonitor` interface & DTOs**  
	- Effort: **S**  
	- Dependencies: T3b discovery types (`TradingPairConfig`, `Prices`).  
	- Description: Review `arch_general.md` and current `common/types` to confirm the `PriceMonitor` contract: `getPairPrices(pair: TradingPairConfig): Promise<Prices>`. Ensure `Prices` semantics are explicit (base per quote on M and N) and that no discovery-specific details leak into `PriceMonitor` (it should depend only on `TradingPairConfig` + config for timeouts if needed). Document this in code comments and/or a short note in this file.
	- Implementation steps (prep for coding session):  
		1. **Locate or define core types** – In `src/common/types.ts` (or the shared domain types module), ensure the following interfaces exist and match `arch_general.md`:  
			- `export interface Prices { priceM: number; priceN: number; }` where both fields represent **base per quote** prices on venues M and N respectively.  
			- `export interface TradingPairConfig { id: PairId; baseToken: string; quoteToken: string; chainM: ChainId; dexJ: string; chainN: ChainId; dexK: string; /* plus risk/position fields as already defined */ }` (reuse existing definition, only align doc comments with discovery semantics).  
			- `export interface PriceMonitor { getPairPrices(pair: TradingPairConfig): Promise<Prices>; }` as the single, canonical entrypoint for price fetching per pair/route.  
		2. **Clarify semantic contracts in comments** – Add JSDoc-style comments on `Prices` and `PriceMonitor` that specify:  
			- `priceM` = base/quote on chain M, DEX J, corresponding to `(chainM, dexJ)` in the `TradingPairConfig`.  
			- `priceN` = base/quote on chain N, DEX K, corresponding to `(chainN, dexK)` in the `TradingPairConfig`.  
			- `getPairPrices` **must not** mutate the `TradingPairConfig` and must treat it as an immutable description of a route discovered at startup.  
		3. **Enforce discovery boundary** – Verify that `PriceMonitor` depends only on `TradingPairConfig` and generic config (e.g., timeouts from `ConfigService`), **not** on raw `tokens`/`chains` slices. Note this explicitly in the interface comments so later implementers do not re-derive routes inside `PriceMonitor`.  
		4. **Align with discovery IDs** – In the `TradingPairConfig` documentation, reference the `id` encoding from T3b (e.g., `base~quote~dexJ+chainM~dexK+chainN`) so the same identifier is consistently used across discovery, price monitoring, orchestrator logs, and risk control. No change to the actual `id` type is needed; just ensure the semantic description is present in one central place.  
		5. **Confirm import/export surface** – Ensure `Prices`, `TradingPairConfig`, and `PriceMonitor` are exported from the shared types module used by Orchestrator, DEX adapters, and RiskManager. Check that future `PriceMonitorService` (T4.2/T4.3) will implement the `PriceMonitor` interface rather than inventing a parallel type.  
		6. **Record decisions in this doc** – Add a short note in this T4 file (or cross-link to `arch_general.md`) summarizing: (a) `Prices` is the only DTO returned by `PriceMonitor` for a given pair, (b) `TradingPairConfig` is the only input, and (c) all per-pair overrides (e.g., risk/slippage) live on `TradingPairConfig` and are **not** duplicated inside `Prices` or `PriceMonitor`.

- [P0] **T4.2: Scaffold `PriceMonitorModule` and `PriceMonitorService`**  
	- Effort: **S**  
	- Dependencies: T3 project bootstrapping; Nest app baseline.  
	- Description: Create `price-monitor.module.ts` and `price-monitor.service.ts` under `src/price_monitor/`. Wire `PriceMonitorService` as an injectable that depends on `LoggerService`, `ConfigService`, and an abstraction for DEX quotes (e.g. a `DexQuoteProvider` or using existing `DexAdapter` interface). Export `PriceMonitorService` from the module so Orchestrator can inject it.

- [P0] **T4.3: Implement core `getPairPrices` for dual-venue routes**  
	- Effort: **M**  
	- Dependencies: T4.1, T4.2, T5 (minimal quote capability in DEX adapters or temporary stub).  
	- Description: In `PriceMonitorService`, implement `getPairPrices(pair: TradingPairConfig)` that: (1) resolves the venue on M: `(chainM, dexJ)` and on N: `(chainN, dexK)` from the pair; (2) calls into a DEX quote abstraction to obtain `priceM` and `priceN` (base per quote) for both venues; (3) returns a `Prices` object. Handle same-chain vs cross-chain pairs uniformly. Keep error handling simple (fail fast with a clear error if an adapter or quote is missing); advanced retries are out of scope for Phase 1.
	- Implementation step: 
		1. Ensure `PriceMonitorService` implements `PriceMonitor` with `getPairPrices(pair: TradingPairConfig): Promise<Prices>`.
		2. Inject `DexQuoteProvider` (and `LoggerService`) into `PriceMonitorService` via the constructor, keeping any `ConfigService` usage minimal for T4.3.
		3. From the input `TradingPairConfig`, build two `DexQuoteRequest`s: one for venue M `(chainM, dexJ)` and one for venue N `(chainN, dexK)` using the pair’s `baseToken` and `quoteToken`.
		4. Call `DexQuoteProvider.getQuote` for both venues concurrently (e.g. `Promise.all`), without branching for same-chain vs cross-chain pairs.
		5. Validate that the returned `priceM` and `priceN` are finite, positive numbers; if not, throw a clear error describing the invalid quote and venue.
		6. Let provider errors bubble but wrap them with contextual information (pair id, chainId, dexKey) so failures are easy to diagnose; do not add retries or fallbacks in this phase.
		7. Return a `Prices` object `{ priceM, priceN }` and do not mutate the incoming `TradingPairConfig`.


- [P0] **T4.4: Define per-tick price fetch strategy for multiple pairs**  
	- Effort: **S**  
	- Dependencies: T4.3, T8 orchestrator design.  
	- Description: Decide and document how the orchestrator should call `PriceMonitor` for multiple `TradingPairConfig`s within an interval (default 1s), e.g. `Promise.all` per batch, limit concurrency if needed, and ensure that per-pair failures do not block others. Provide a small helper or example function (e.g. `getPricesForPairs(pairs: TradingPairConfig[]): Promise<Map<PairId, Prices>>`) to make orchestrator wiring straightforward.
	- Implementation steps (prep for coding session):  
		1. **Define multi-pair helper signature** – In `src/price_monitor/price-monitor.service.ts`, add a method `getPricesForPairs(pairs: TradingPairConfig[], options?: { maxConcurrent?: number; }): Promise<{ prices: Map<PairId, Prices>; errors: Map<PairId, Error>; }>` that will be used by `OrchestratorService` per tick. Keep this helper focused on orchestration of `getPairPrices` calls and do not add any risk or execution logic.
		2. **Start with naive concurrent implementation** – Implement `getPricesForPairs` by mapping each `TradingPairConfig` to a `Promise` that calls `this.getPairPrices(pair)` and tagging results by `pair.id`. Use `Promise.all` over this list for the initial implementation, relying on the existing per-pair validation and error handling in `getPairPrices`.
		3. **Design configurable concurrency guard** – Extend the helper to *accept* an optional `maxConcurrent` parameter (from `options`) that will cap the number of in-flight `getPairPrices` calls. For T4.4, document this option and its intended usage (e.g., wiring to a future `ops.maxPriceMonitorConcurrency` config value) but it is acceptable to leave the actual semaphore/queue implementation for performance-focused tasks.
		4. **Return structured success and error maps** – Ensure `getPricesForPairs` does **not** throw when some pairs fail. Instead, build two `Map`s: `prices` containing successful `{ pairId -> Prices }` entries, and `errors` containing `{ pairId -> Error }` entries for pairs where `getPairPrices` rejected. This allows the orchestrator to skip only failed pairs in a tick while still using successful quotes.
		5. **Keep `PriceMonitor` contract minimal** – Do not add `getPricesForPairs` to the public `PriceMonitor` interface for now; keep it as a convenience method on `PriceMonitorService` used by the orchestrator. The canonical contract remains `getPairPrices(pair: TradingPairConfig): Promise<Prices>` per T4.1/T4.3.

- [P0] **T4.5: Unit tests for `PriceMonitorService`**  
	- Effort: **M**  
	- Dependencies: T4.1–T4.3.  
	- Description: Add Jest specs under `src/price_monitor/` that mock the DEX quote abstraction and verify: (1) correct mapping from `TradingPairConfig` fields to quote requests (chain/dex, base, quote); (2) correct assembly of `Prices` for same-chain and cross-chain routes; (3) meaningful error when a venue quote is unavailable. Use small in-memory `TradingPairConfig` fixtures and do not depend on real `config.yaml`.
	- Implementation steps (prep for coding session):  
		1. **Create a dedicated spec file** – Add `src/price_monitor/price-monitor.service.spec.ts` for unit tests that instantiate `PriceMonitorService` directly (no Nest testing module), importing the real `TradingPairConfig` / `Prices` types and the `PriceMonitorService` class.
		2. **Set up test fixtures and mocks** – Define small in-memory `TradingPairConfig` fixtures for: (a) a same-chain route (e.g. `chainM === chainN`, different `dexJ`/`dexK`), and (b) a cross-chain route (`chainM !== chainN`). For each test, construct a `DexQuoteProvider` mock via `jest.fn()` that can return configured prices or throw. Use a minimal `ConfigService` stub (or a simple object cast) and a lightweight `LoggerService` mock that records calls without touching real IO.
		3. **Verify request mapping to `DexQuoteProvider`** – In a test like “maps `TradingPairConfig` to two DexQuoteRequests”, configure the `DexQuoteProvider` mock to resolve with dummy numbers and call `getPairPrices(fixturePair)`. Assert that `getQuote` was called twice with `DexQuoteRequest` objects whose `chainId`/`dexKey`/`baseToken`/`quoteToken` match `(chainM, dexJ)` and `(chainN, dexK)` from the fixture `TradingPairConfig`.
		4. **Verify successful `Prices` assembly** – Add a test where the `DexQuoteProvider` mock returns distinct numeric prices (e.g. `1.23` for M and `0.98` for N). Assert that `getPairPrices` resolves to a `Prices` object `{ priceM, priceN }` with the exact values from the mock, and that the method does not mutate the input `TradingPairConfig` (e.g. by checking selected fields before/after the call).
		5. **Verify validation and error messaging for invalid prices** – Add tests where the mock returns invalid values (e.g. `0`, negative, or `NaN`) for M or N. Assert that `getPairPrices` rejects with an `Error` whose message includes the `pair.id` and the offending venue (`chainId` / `dexKey`), and that the corresponding `logger.error` mock was called with the structured context (including `pairId`, `venue`, and `request`).
		6. **Verify wrapped provider errors** – Add a test where `DexQuoteProvider.getQuote` rejects (e.g. `new Error('upstream failure')`) for one of the venues. Assert that `getPairPrices` rejects with a new `Error` whose message contains the `pair.id` and both venues, and whose `cause` (if inspected via type guard or cast) preserves the original error message. Confirm that the logger was invoked once with the combined failure context.
		7. **Unit-test `getPricesForPairs` orchestration** – For multi-pair behavior, use `jest.spyOn` on `PriceMonitorService.prototype.getPairPrices` (or override it on the instance) to avoid re-mocking `DexQuoteProvider` logic. Add tests that: (a) when all pairs succeed, `getPricesForPairs` resolves with a `prices` `Map` containing all `pair.id` keys and an empty `errors` `Map`; (b) when some pairs reject, `getPricesForPairs` still resolves (does not throw), with successful pairs in `prices` and failed ones in `errors`; (c) when called with an empty `pairs` array, it resolves to empty `prices`/`errors` maps and does not call `getPairPrices`. Treat `options.maxConcurrent` as an input parameter only—verify that passing valid or invalid values does not change correctness (all pairs still end up in either `prices` or `errors`) without asserting on actual concurrency timing.

- [P0] **T4.6: Integration test – discovery + `ConfigService` + `PriceMonitor`**  
	- Effort: **M**  
	- Dependencies: T3b discovery integration tests, T4.2–T4.3.  
	- Description: Extend the existing discovery+config integration tests (or add a new spec under `test/price_monitor/`) to build a Nest testing module that includes `ConfigService`, `PairDiscoveryService`, a mock DEX quote provider, and `PriceMonitorService`. Assert that for at least one real `TradingPairConfig` from the current `config.yaml`, `getPairPrices` returns the expected `Prices` derived from the mock quotes and that the wiring does not touch raw config directly.

- [P1] **T4.7: Basic logging & timing metrics around price fetch**  
	- Effort: **S**  
	- Dependencies: T4.3, `LoggerService`.  
	- Description: In `PriceMonitorService`, add structured logs for: start/end of price fetch per pair, total duration, and any failures. Keep logs at a level compatible with the existing logging strategy (`info` for success summaries, `warn`/`error` for failures). Optionally record simple timing metrics (e.g., log duration fields) to support the “<300ms avg fetch per chain/DEX” success criterion.
	- Implementation steps (prep for coding session):  
		1. **Add per-pair timing in `getPairPrices`** – At the top of `getPairPrices`, capture a `startMs = Date.now()` and derive `durationMs = Date.now() - startMs` on every return or throw path so that each price fetch for a given `pair.id` has an associated latency measurement in milliseconds.
		2. **Log start/end events for successful fetches** – Emit a lightweight “start” log (e.g. `debug` level) when a pair-price fetch begins with `pairId` and venue identifiers, and an `info`-level “success” log when both quotes are validated, including at minimum `pairId`, `durationMs`, `priceM`, `priceN`, and the `(chainM, dexJ)` / `(chainN, dexK)` venues in the structured context.
		3. **Include timing on all failure logs** – For both validation failures (invalid `priceM`/`priceN`) and provider/adapter errors caught in the `try/catch`, extend the existing `logger.error` payloads to also carry `durationMs` (time until failure) alongside `pairId`, the relevant venue or requests, and the error message so that slow or failing venues can be distinguished from fast successes.
		4. **Add batch-level summary in `getPricesForPairs`** – Optionally capture `batchStartMs = Date.now()` at the beginning of `getPricesForPairs` and log a single `info`-level summary when all workers complete, with fields such as `totalPairs`, `successCount`, `errorCount`, `maxConcurrent`, and `durationMs` (batch wall-clock time), without duplicating per-pair details already logged by `getPairPrices`.
		5. **Keep logging configuration-agnostic for now** – Do not introduce new config keys or sampling logic in T4.7; rely on existing `LoggerService` level controls and keep the added logs small and structured so they can be filtered or down-leveled later when T14 (observability) or T4.8 introduces more advanced behavior.
		6. **Align or extend unit tests where appropriate** – Once logging and timing fields are wired, review `price-monitor.service.spec.ts` to ensure that new logs do not break existing expectations (e.g. error call counts) and, if valuable, add a small number of assertions that confirm `durationMs` is present and numeric in at least one success and one failure scenario.

- [P1] **T4.8: Config-driven timeouts for price requests**  
	- Effort: **M**  
	- Dependencies: T4.3, `ConfigService` (`ops` or dedicated price config).  
	- Description: Introduce a basic timeout mechanism for price requests (e.g., using `Promise.race` with a timeout value from config). If a DEX quote exceeds the timeout, treat it as a failure for that venue and log it. Do not yet implement retries or backoff; those belong to later reliability tasks (T12).

- [P1] **T4.9: Error classification and minimal fallbacks**  
	- Effort: **S**  
	- Dependencies: T4.3, T4.5.  
	- Description: Classify common error types from the DEX quote abstraction (e.g., network errors vs. “no liquidity” vs. misconfiguration) and ensure `PriceMonitor` surfaces them clearly to Orchestrator/RiskManager. Implement minimal fallbacks such as skipping only the failed pair in a tick instead of failing the whole price loop. Full circuit-breakers and retry policies are deferred to T12.

---

### Out of Scope / Later Phases (Not Phase 1)

- Full **rate-limit handling** and adaptive request scheduling across many DEXes and chains (tie-in with T12: Performance & reliability).
- **Circuit-breakers** and advanced retry/backoff policies for flaky DEX or RPC providers.
- **Price caching** and cross-tick reuse of quotes to reduce load.
- Integration with external **aggregator APIs** or secondary data sources beyond direct DEX adapters.
- Rich **metrics export** (Prometheus, dashboards) beyond basic logging—these relate to T14 (Observability).

These items should be revisited after Phase 1 once basic price monitoring is wired through Orchestrator and validated in integration tests.

