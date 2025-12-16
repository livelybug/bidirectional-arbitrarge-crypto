## T5: DEX Integrations – Task Breakdown (Phase 1)

Effort scale: **XS / S / M / L / XL**  
Priority: **P0 (must-have)**, **P1 (nice-to-have for Phase 1)**, **P2 (later)**

- [x] **[P0][S] Confirm DEX adapter contract, registry, and config wiring**  
	**Description:** Validate that `DexAdapter` in `dex-adapter.interface.ts` covers all quote/swap/balance operations needed by Orchestrator and RiskManager (buy/sell, slippage, balances). Ensure `DexModule` exports (`DEX_UNISWAP_V3`, `DEX_PANCAKESWAP_V3`, and any additional DEX tokens) match `chains.*.dexList.key` values and `TradingPairConfig.dexJ/dexK`. Confirm that the PriceMonitor/DexQuoteProvider wiring uses a simple adapter registry keyed by `(chainId, dexKey)` so that new DEXs can be plugged in without touching orchestrator or risk logic.  
	**Dependencies:** T2 (architecture interfaces), T3b (discovery types), `ConfigService`, `TradingPairConfig`, `DexModule`, `PriceMonitorService`.  
	**Effort:** S

- [x] **[P0][M] Harden Uniswap V3 adapter for quotes and swaps**  
	**Description:** Evolve `UniswapV3Service` to be production-lean: keep current deterministic stub behavior but clearly separate (a) pure quote path (for `PriceMonitor` / risk checks) from (b) swap path (execution), and make sure it fully honours the `DexAdapter` contract (slippageBps input, base/quote direction, numeric safety). Add structured logs (`debug` for estimates, `info` for swaps) including `chain`, `dexKey`, `baseToken`, `quoteToken`, amounts, and derived prices. Treat Uniswap as the canonical reference implementation for other DEX adapters.  
	**Dependencies:** Previous task; `dex/uniswap-v3.service.ts`, `LoggerService`, `ConfigService.getChainsConfig()`.  
	**Effort:** M

- [x] **[P0][M] Design and stub Pancakeswap adapter as second primary DEX**  
	**Description:** Introduce a `PancakeswapV3Service` class implementing `DexAdapter` with behavior initially mirroring `UniswapV3Service` (deterministic price derivation and stubbed swaps/balances). Wire it into `DexModule` with a dedicated token (e.g. `DEX_PANCAKESWAP_V3`) and document required `chains.*.dexList` entries and `TradingPairConfig.dexJ/dexK` values. Ensure its logging and error semantics match Uniswap so it can be used interchangeably by PriceMonitor and Orchestrator.  
	**Dependencies:** Existing `DexAdapter` design, `dex.module.ts`, `config.yaml` chains.dexList, task T5 goal (“extend for pancakeswap”).  
	**Effort:** M

- [x] **[P1][M] Harden Velodrome V2 adapter as an additional DEX example**  
	**Description:** Align `VelodromeV2Service` behavior and logging with `UniswapV3Service`: consistent price derivation semantics, slippageBps handling, and structured logs for estimate/swap/balance calls. Ensure `resolveChain('velodrome_v2')` matches at least one `chains.*.dexList.key` in `config.yaml` and that misconfigurations fail fast with clear errors. Treat Velodrome as a template for future DEX integrations beyond Uniswap and PancakeSwap.  
	**Dependencies:** Uniswap/PancakeSwap tasks; `dex/velodrome-v2.service.ts`, `config.yaml` chains.dexList, T3b fast-fail rules.  
	**Effort:** M

- [x] **[P0][S] Implement and wire DEX balance access for runtime state**  
	**Description:** Confirm `getBalanceBase` and `getBalanceQuote` implementations on Uniswap and PancakeSwap adapters (and any additional DEXs) can be used by Orchestrator/RiskManager to build `PairRuntimeState` (even if stubbed initially). Ensure logging includes `chain`, token symbol, and adapter key, and that failures are surfaced as meaningful errors (not silently returning zero).  
	**Dependencies:** `DexAdapter` interface, `PairRuntimeState` in `common/types.ts`, `WalletService` (from T9), T7/T8 design for runtime state.  
	**Effort:** S

- [x] **[P0][M] Integrate DEX adapters with PriceMonitor quote abstraction**  
	**Description:** Provide or extend a `DexQuoteProvider` implementation that delegates to the appropriate `DexAdapter` based on `DexQuoteRequest.chainId` and `dexKey`, using `UniswapV3Service` / `PancakeswapV3Service` (and optionally `VelodromeV2Service`) under the hood. Ensure mapping from `TradingPairConfig` → `DexQuoteRequest` (already used in `PriceMonitorService`) resolves to the right adapter and that missing adapters fail fast with clear errors. Keep the lookup logic generic so adding a new DEX only requires registering its adapter/token, not changing PriceMonitor code.  
	**Dependencies:** T4.3 (PriceMonitor core), `PriceMonitorService`, `DexAdapter`, `DEX_*` tokens, `ConfigService.getChainsConfig()`.  
	**Effort:** M

- [x] **[P0][M] Unit tests for Uniswap V3 and PancakeSwap adapters (and templates for others)**  
	**Description:** Add Jest specs under `src/dex/` (e.g. `uniswap-v3.service.spec.ts`, `pancakeswap-v3.service.spec.ts`) that construct adapters with mocked `ConfigService` and `LoggerService`. Cover: deterministic quote outputs for given (base, quote, amount); correct handling of invalid numeric inputs; fast-fail behavior when `config.chains` does not advertise the dex key; and simple swap receipt shape (`txHash`). Use these tests as the baseline pattern for additional DEX adapters such as Velodrome.  
	**Dependencies:** Uniswap/PancakeSwap tasks; Jest setup from T3; `ConfigService`, `LoggerService`.  
	**Effort:** M

- [ ] **[P0][M] Integration test: PriceMonitor + primary DEX adapters (same-chain and cross-chain)**  
	**Description:** Extend or add integration tests (e.g. under `test/dex/` or `test/price_monitor/`) that build a Nest testing module with `ConfigService`, `DexModule`, `PriceMonitorService`, and a test `config.yaml`. Assert that for at least one `TradingPairConfig` per primary adapter (Uniswap V3, PancakeSwap V3), `getPairPrices` returns prices derived from the concrete adapters (not just mocks), and that misconfiguration of `chains.*.dexList` triggers fail-fast errors. Optionally include Velodrome or other DEXs once wired.  
	**Dependencies:** T4.6 (integration test patterns), `PairDiscoveryService`, `DexModule`, `PriceMonitorService`.  
	**Effort:** M

- [x] **[P1][S] Align T5 docs and architecture references with concrete adapters**  
	**Description:** Update `docs/task/task.md` (T5 section) and `arch_general.md` DEX adapter descriptions to mention `UniswapV3Service`, `PancakeswapV3Service`, and additional examples such as `VelodromeV2Service`, ensuring naming matches `chains.*.dexList.key` and token constants in `common/tokens.ts`. Clarify that T5 provides both quote and execution paths with slippage caps and that PriceMonitor uses the quote path only.  
	**Dependencies:** All prior T5 subtasks; existing architecture docs; `common/tokens.ts`.  
	**Effort:** S

- [ ] **[P1][S] Document DEX plug-in pattern for future integrations**  
	**Description:** Add a short “How to add a new DEX” subsection to this file describing the steps: (1) implement a new `DexAdapter` class, (2) register it in `DexModule` with a `DEX_*` token, (3) add the DEX key to `config.yaml` under the relevant `chains.*.dexList`, (4) ensure `PairDiscoveryService` can emit `TradingPairConfig` entries with that `dexKey`, and (5) optionally add adapter-specific unit/integration tests following the Uniswap/PancakeSwap patterns. Emphasize that, with this pattern, no changes are required in Orchestrator, RiskManager, or PriceMonitor beyond configuration.  
	**Dependencies:** All core T5 tasks; `DexModule`, `PairDiscoveryService`, `config.yaml`, test patterns.  
	**Effort:** S

- [ ] **[P1][S] Sanity-check slippage handling and quote-vs-execution delta**  
	**Description:** Define a small set of test scenarios (unit or integration) that compare adapter quote outputs against simulated execution results, ensuring the delta stays within configured slippage (≤3%) for representative amounts. For now, this can be enforced via deterministic formulas in the stub implementations; later it can be backed by real on-chain or SDK calls.  
	**Dependencies:** Risk config (`risk.slippageBps`), T7 (slippage semantics), adapter unit tests, PriceMonitor tests.  
	**Effort:** S

- [ ] **[P2][L] Plan transition from deterministic stubs to real DEX SDK/RPC calls**  
	**Description:** Draft a follow-up plan for replacing the deterministic pricing and swap stubs with real Uniswap V3 / Velodrome / Pancakeswap SDK integrations or on-chain calls via wallet providers. Identify required configuration (RPC URLs, pool addresses, fee tiers), signing flows, and additional error handling (reverts, partial fills). This task is mainly design/documentation and should not be implemented in Phase 1.  
	**Dependencies:** All T5 implementation tasks; T9 wallet utilities; T12 performance & reliability requirements.  
	**Effort:** L

