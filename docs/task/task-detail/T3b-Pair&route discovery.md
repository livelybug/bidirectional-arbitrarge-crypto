## T3b: Pair & Route Discovery – Task Breakdown

- [P0] Define discovery goals and inputs/outputs  
	- Clarify that discovery runs at startup, uses `ConfigService` to read `tokens` (global base/quote lists) and `chains.*.{tokenList,dexList}`, and produces an in-memory, deterministic list of `TradingPairConfig` + route entries `(chainM, dexJ) → (chainN, dexK)` for all eligible token pairs.  
	- Capture fast-fail expectations (e.g., base/quote symbols that never appear in any `chains.*.tokenList` must cause an error) in a short design note within this file.  
	- Deps: T3-07 (Config loader), T3-09 (interfaces/types).

- [P0] Design `TradingPairConfig` and supporting types  
	- Review `docs/arch/arch_general.md` and `docs/task/task.md` to align `TradingPairConfig`, `PairId`, and any per-pair override fields (minProfitRateBps, slippageBps, positionCaps) with the architecture.  
	- Confirm final type definitions live in `src/utils/config/config.types.ts` (or a shared domain types module) so they are reusable by Orchestrator, PriceMonitor, and RiskManager.  
	- Deps: T3-09 (common interfaces and tokens).

- [P0] Specify discovery algorithm and error modes  
	- On paper (or in comments in this file), define, in terms of `symbolPair`, `swapPair`, and `arbitrargePair`, how to:  
		- Enumerate `symbolPair` as all base/quote combinations from `tokens.{base,quote}` (cartesian product).  
		- For each `symbolPair` and each chain, determine which of those token symbols are present in `chains[chainId].tokenList` and, for each DEX in `chains[chainId].dexList`, build corresponding `swapPair`s.  
		- For each token pair that appears on at least two venues (two or more `swapPair`s), construct one or more `arbitrargePair`s / routes `(chainM, dexJ) → (chainN, dexK)` as described in the flow.
	- Enumerate explicit failure cases and desired error messages (Fast-fail A/B/C in the flow section), e.g.:  
		- Missing token coverage (Fast-fail A): base or quote symbol listed in `tokens` but missing from *all* `chains.*.tokenList`.  
		- No `swapPairs` / `arbitrargePairs` discovered (Fast-fail B/C): no eligible routes found at all (empty discovery result).  
		- Unknown or duplicate chain ids/dex keys or unsupported adapters (cannot map cleanly to implementations).  
	- Deps: `config.yaml`, schema docs (`schema_validation.md`).
	- Output: [Arbitrarge Pairs Discovery Flow](#arbitrarge-pairs-discovery-flow) below

- [P0] Implement pure discovery helper (framework-agnostic)
	- Add a pure function (e.g. `buildTradingPairsAndRoutes`) under `src/orchestrator` or `src/utils` that accepts a typed snapshot of config (`AppConfig` or `{ tokens, chains }`) and returns `{ pairs: TradingPairConfig[] }` plus optional metadata (e.g. skipped tokens, diagnostics).  
	- Ensure the helper does **not** depend on Nest DI; it should be easily unit-testable by passing in an in-memory config object.  
	- Implement deterministic ordering (e.g. sort by `baseToken`, then `quoteToken`, then `chainM`, `chainN`, `dexJ`, `dexK`) to keep results stable across runs.  
	- Deps: Type definitions from previous tasks.
	- Implementation steps (prep for coding session):  
		1. **Scaffold module** – create `src/orchestrator/pair-discovery/` with `pair-discovery.helper.ts` (pure code) and `index.ts` exporting the helper + types.  
		2. **Define input/output contracts** – import `TradingPairConfig`, `ChainsConfig`, token symbol types from `config.types.ts`; define `PairDiscoveryInput = Pick<AppConfig, 'tokens' | 'chains'>` (or equivalent) plus a `PairDiscoveryResult` interface.  
		3. **Implement helper** – code `buildArbitrargePairs(input: PairDiscoveryInput): PairDiscoveryResult` that:  
			- Validates tokens arrays are non-empty (extra guard) then builds sorted `symbolPairs`.  
			- Builds per-chain token lookup maps (symbol → metadata) to speed membership checks.  
			- Generates `swapPairs` per chain/DEX, tracking coverage stats per symbol.  
			- Applies Fast-fail A/B checks immediately after `swapPairs` creation; surface errors with precise messages.  
			- Enumerates ordered `swapPair1`/`swapPair2` combinations to yield `TradingPairConfig` objects (Fast-fail C if none).  
			- Supports optional diagnostics (e.g., array of skipped symbols or chains).  
		4. **Deterministic ordering** – ensure every iteration uses sorted arrays; finish with a single `.sort()` using `(baseToken, quoteToken, chainM, chainN, dexJ, dexK)` comparator.  
		5. **Surface-friendly errors** – throw plain `Error` instances with actionable text, reusing Fast-fail names and referencing offending symbols / chains / dex keys.  
		6. **Export helpers for tests** – export internal utilities if needed (e.g., comparator) to simplify unit specs.

- [P0] Add fast-fail checks to the discovery helper  
	- Inside the helper, implement explicit validation that:  
		- Every symbol in `tokens.base` and `tokens.quote` appears in at least one `chains.*.tokenList`.  
		- At least one eligible route is produced overall; otherwise throw with a clear message.  
		- Optionally, enforce that each route’s DEX key exists in `chains[chainId].dexList` (reusing the fail-fast defaults already used by DEX adapters).  
	- Design error types/messages to be easily surfaced to the operator (e.g. plain `Error` with human-readable text).  
	- Deps: Pure helper implementation.

- [P1] Wrap helper in a Nest discovery service  
	- Create a dedicated discovery service (e.g. `PairDiscoveryService`) under `src/orchestrator` or a small `src/discovery` module.  
	- Inject `ConfigService` and call the pure helper with the validated config snapshot on service initialization.  
	- Cache the computed `TradingPairConfig[]` list in memory and expose read-only getters (e.g. `getAllPairs()`, `getRoutesForPair(pairId)`).  
	- Implementation steps (prep for coding session):  
		1. **Scaffold service + module wiring** – add `pair-discovery.service.ts` (and optionally `pair-discovery.module.ts`) under `src/orchestrator/pair-discovery/`, export it through the local `index.ts`, and register the provider inside `OrchestratorModule` so other modules can inject it.  
		2. **Inject ConfigService + helper** – in the service constructor (or `onModuleInit`), inject `ConfigService`, read `{ tokens, chains }` via the typed getter, run `buildArbitrargePairs`, and surface any Fast-fail errors immediately (let Nest bubble them to abort boot).  
		3. **Cache + expose getters** – store `{ pairs, diagnostics }` in private readonly fields, expose `getAllPairs(): TradingPairConfig[]`, `getRoutesForPair(pairId)` (filter by `pair.id`), and `getDiagnostics()` returning the helper metadata without re-running discovery.  
		4. **Guard re-computation + logging** – keep discovery pure at startup (no hot reload), but add TODO hook for future refresh; emit a structured log summarizing counts (tokens, chains, pairs) using `LoggerService`.  
		5. **Add targeted tests** – create `pair-discovery.service.spec.ts` using a mocked `ConfigService` that returns in-memory configs; assert it calls the helper once, caches output, and propagates Fast-fail errors.  
	- Deps: P0 helper + fast-fail checks; T3-10 (scaffold modules) for wiring pattern.

- [P1] Define contracts for Orchestrator and PriceMonitor  
	- Update or create small TypeScript interfaces (or doc comments) clarifying how Orchestrator and PriceMonitor consume discovery output, e.g.:  
		- Orchestrator receives `TradingPairConfig[]` at startup and iterates it on each tick.  
		- PriceMonitor exposes `getPairPrices(pair: TradingPairConfig)` and does not re-derive routes.  
	- Record this contract briefly in `docs/arch/arch_general.md` (or a short note in this T3b doc) so later tasks (T4, T8) have a stable reference.  
	- Deps: Discovery types and service.

- [P1] Integrate discovery into Orchestrator initialization (light wiring)  
	- Inject the new discovery service into `OrchestratorService` and replace any temporary hard-coded pair/route derivation with a call to `getAllPairs()` (or equivalent).  
	- Ensure the Orchestrator fails fast on startup if discovery throws (propagate the error rather than catching and continuing).  
	- Leave multi-pair loop logic and execution selection to T4/T8; here only ensure the discovered list is available and logged once at boot.  
	- Implementation steps (prep for coding session):  
		1. **Inject discovery service into Orchestrator** – update `OrchestratorService`'s constructor to accept `PairDiscoveryService` (from `src/orchestrator/pair-discovery`) alongside existing `ConfigService`, `LoggerService`, `PriceMonitor`, and `RiskManager` dependencies.  
		2. **Replace hard-coded pair derivation** – remove or deprecate the current `derivePairs()` helper that inspects `config.chains`/`tokens` directly; instead, initialize the private `pairs: TradingPairConfig[]` field from `pairDiscoveryService.getAllPairs()` so the orchestrator always runs on the discovered universe.  
		3. **Preserve fail-fast semantics** – let any exception from `PairDiscoveryService` (which already wraps `buildArbitrargePairs`) bubble through Nest startup without a catch in `OrchestratorService`; optionally keep a guard that throws if `getAllPairs()` returns an empty list to make the failure mode explicit.  
		4. **Align boot logging** – keep the existing `onModuleInit` log (`Orchestrator loop starting`) but source `pairCount` from the injected discovery data; avoid re-reading config tokens/chains here since discovery already logged a summary at its own initialization.  
		5. **Adjust orchestrator tests** – update `orchestrator.service.spec.ts` (or add a focused spec under `test/orchestrator/`) to use a mocked `PairDiscoveryService` that returns a fixed `TradingPairConfig[]`; assert that the service is constructed with those pairs, that `pairCount` in the startup log matches, and that startup fails if the discovery mock throws.  
	- Deps: Pair discovery service; existing Orchestrator loop (T3-11).

- [P1] Implement unit tests for the pure discovery helper  
	- Add a new spec file (e.g. `src/orchestrator/pair-discovery.spec.ts` or under `src/utils`) that constructs small in-memory configs and asserts:  
		- Single-token, single-chain cases produce no routes when only one venue exists.  
		- Multi-chain, multi-DEX cases build the expected set of routes, including same-chain and cross-chain combinations.  
		- Result ordering is deterministic given the same input config.  
	- Include explicit tests for fast-fail conditions:  
		- Base/quote symbol configured but missing from all `chains.*.tokenList`.  
		- Config with tokens present but no eligible dual-venue routes.  
	- Implementation steps (prep for coding session):  
		1. **Scaffold spec file** – create `code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.spec.ts` and import `buildArbitrargePairs`, `tradingPairComparator`, and the relevant discovery types from `./pair-discovery.helper`.  
		2. **Use typed configs via schema** – import `parseConfig` (or `appConfigSchema`) and `AppConfig` from `src/utils/config/config.schema.ts` / `config.types.ts`; define a local helper `makeInput(raw: Partial<AppConfig>): PairDiscoveryInput` that merges `raw` onto a minimal base config, runs schema validation once, and returns `{ tokens: config.tokens, chains: config.chains }`.  
		3. **Happy-path: two-chain, single-DEX** – write a test that builds an input with one base, one quote, and two chain & single DEX where both tokens exist; assert `buildArbitrargePairs` returns an empty `pairs` array while diagnostics show `symbolPairsEvaluated === 2`, `swapPairsGenerated === 2`, `arbitrargePairsGenerated === 1`.  
		4. **Happy-path: multi-chain/multi-DEX routes** – construct a small config with two chains sharing the same `(base, quote)` and two DEX venues at each chain; assert the resulting `TradingPairConfig[]` has the expected length and that a few entries exactly match the expected `(baseToken, quoteToken, chainM, dexJ, chainN, dexK)` and id encoding.  
		5. **Deterministic ordering** – add a test that calls `buildArbitrargePairs` multiple times with the same logical config but with tokens/chains listed in different orders; assert that all resulting `pairs` arrays are identical and that applying `.sort(tradingPairComparator)` does not change their order.  
		6. **Fast-fail A/B/C coverage** – add three tests that each start from a valid base config and then: (A) introduce a token symbol absent from all `chains.*.tokenList`, (B) ensure no chain contains both base and quote simultaneously, and (C) ensure only one venue per `(base, quote)` pair; in each case, assert `buildArbitrargePairs` throws and the error message includes the corresponding Fast-fail label (`Fast-fail A/B/C`).  
		7. **Shape-validation errors** – add tests that pass malformed `PairDiscoveryInput` objects (e.g. missing `tokens.base` / `tokens.quote`, or `chains` set to `null`) directly to `buildArbitrargePairs` and assert the helper throws with the expected `tokens configuration is invalid` / `chains configuration is invalid` messages.  
		8. **Keep tests framework-agnostic** – ensure the spec does not construct a Nest testing module or use `ConfigService`; all tests should be pure Jest specs operating on in-memory config objects and the exported helper/comparator.  
	- Deps: Pure helper implementation.

- [P1] Implement integration tests for discovery + ConfigService  
	- Add or extend tests (e.g. in `src/utils/config/config.schema.spec.ts` or a dedicated discovery spec) that:  
		- Load the real `config.yaml` via `ConfigService`.  
		- Invoke the discovery service/helper with the validated config.  
		- Assert that at least one `TradingPairConfig` and route is discovered and that token symbols/chain ids match expectations from `config.yaml`.  
	- Confirm that the test will fail if `config.yaml` drifts (e.g. tokens removed, chains misconfigured) in ways that would break discovery.  
	- **Integration Test Plan (ConfigService + PairDiscoveryService)**  
		1. **Test file & placement** – create `code/ts/test/discovery/discovery.integration.spec.ts` under the existing Jest `test/` tree so it runs with the standard `pnpm test` command. Import `TestingModule` / `Test` from `@nestjs/testing`, `ConfigService` from `src/utils/config/config.service`, `LoggerService` from `src/utils/logger/logger.service`, and `PairDiscoveryService` from `src/orchestrator/pair-discovery/pair-discovery.service`.  
		2. **Testing module wiring** – in the spec, build a Nest testing module in `beforeAll` that registers `ConfigService`, `LoggerService`, and `PairDiscoveryService` as providers (no mocks for `ConfigService` so it loads the real `config.yaml` from the project root). Retrieve `configService` and `pairDiscoveryService` instances from the module for use in tests; keep `logger` as the real logger or a lightweight stub if needed.  
		3. **Smoke test: discovery runs on real config** – add a basic `it` block that calls `pairDiscoveryService.onModuleInit()` once, then asserts `getAllPairs().length > 0` and that `getDiagnostics()` reports non-zero `uniqueBaseSymbols`, `uniqueQuoteSymbols`, `chainsScanned`, and `arbitrargePairsGenerated`. This ensures that the real `config.yaml` is structurally sound and produces at least one arbitrageable route.  
		4. **Config-driven expectations** – using the current `config.yaml`, assert that at least one discovered `TradingPairConfig` has `baseToken === 'WIF'`, `quoteToken === 'USDT'`, and venues consistent with the config (e.g. a route between `arbitrum`/`uniswap_v3` and `base`/`uniswap_v3`). Optionally assert the exact `id` format (e.g. `WIF~USDT~uniswap_v3+arbitrum~uniswap_v3+base`) to guard encoding stability.  
		5. **Determinism on repeated calls** – within the same module, call `pairDiscoveryService.onModuleInit()` multiple times and assert that `getAllPairs()` returns the same array instance or at least equal contents, and that diagnostics do not change between calls. This guards against accidental re-computation or non-deterministic behavior when the service is initialized more than once.  
		6. **Failure-on-config-drift** – add a separate test (or test block) that temporarily points `APP_CONFIG_PATH` to a modified copy of `config.yaml` with deliberate misconfigurations (e.g. removing `WIF` from one chain’s `tokenList` or stripping a `dexList` entry). In that context, assert that calling `pairDiscoveryService.onModuleInit()` (or directly invoking `buildArbitrargePairs` with the altered config) throws with one of the defined Fast-fail messages, demonstrating that discovery fails loudly when config drifts in breaking ways.  
	- Deps: ConfigService; discovery helper + service.

- [P2] Add logging and diagnostics around discovery  
	- Use `LoggerService` to emit a summary at startup: number of base/quote tokens, number of chains, number of discovered pairs/routes, and any skipped tokens or chains.  
	- Ensure logs include enough context (token symbols, chain ids, dex keys) to debug misconfigurations quickly without exposing secrets.  
	- Deps: Discovery service wired into Orchestrator/Utils logging.

- [P2] Document discovery behavior in architecture docs  
	- Update `docs/arch/arch_general.md` to briefly describe the discovery process:  
		- No static pairs in config; pairs/routes are computed at startup from `tokens` and `chains`.  
		- Fast-fail rules for missing tokens and empty discovery results.  
		- Relationship between discovery output, Orchestrator, and PriceMonitor.  
	- Optionally cross-link this T3b detail file from the architecture doc for traceability.  
	- Deps: Discovery algorithm finalized.

- [P2] Keep README and operator docs aligned (optional)  
	- Add a short note to `docs/readme/README.ts.md` summarizing how trading pairs and routes are discovered from `config.yaml`, and what kinds of config mistakes will cause startup failures.  
	- Ensure messaging is operator-friendly (focus on how to fix config), not implementation details.  
	- Deps: Discovery behavior stable and tested.

- [P3] Plan for per-pair overrides and future extensions  
	- Capture, in this T3b document, how per-pair overrides (`minProfitRateBps`, `slippageBps`, `positionCaps`) should be attached to `TradingPairConfig` in later phases, even if not yet implemented.  
	- Note any implications for discovery (e.g. defaulting to global risk/fee settings unless overrides are provided by a future config extension).  
	- Deps: None (design note only; feeds into later tasks such as T7 and future config extensions).

### Arbitrarge Pairs Discovery Flow

Conceptual flow using `symbolPair`, `swapPair`, and `arbitrargePair`:

> Mapping to implementation types: in code, each `arbitrargePair` will be represented as a `TradingPairConfig` where `swapPair1` provides `(chainM, dexJ)` and `swapPair2` provides `(chainN, dexK)` for a given `(baseToken, quoteToken)`.

1. **Enumerate `symbolPair` from global tokens**  
	- From `config.tokens.base` and `config.tokens.quote`, build the cartesian product of base×quote symbols. Example:

```yaml
tokens:
  base:
    - WIF
    - PEPE
  quote:
    - USDT
    - USDC
```

leads to:

```text
symbolPairs = [
  { base: WIF,  quote: USDT },
  { base: WIF,  quote: USDC },
  { base: PEPE, quote: USDT },
  { base: PEPE, quote: USDC },
]
```

	- Determinism: iterate `base` and `quote` arrays in sorted order so `symbolPairs` is always constructed in the same order for a given `config.yaml`.

2. **Generate `swapPair`s per chain/DEX for each `symbolPair`**  
	- For each `symbolPair = { base, quote }` and for each `chainId` in sorted `Object.keys(config.chains)`:  
		- Check `chains[chainId].tokenList` for both `base` and `quote` symbols.  
		- If both exist, then for each DEX in `chains[chainId].dexList` create a `swapPair`:

```text
swapPair = {
  swapPairId: `${base}~${quote}~${dexKey}~${chainId}`,
  base,
  quote,
  dex: dexKey,
  chain: chainId,
}
```

	- Example (simplified from current `config.yaml`):

```yaml
chains:
  arbitrum:
    tokenList:
      - symbol: USDT
      - symbol: WIF
    dexList:
      - key: uniswap_v3
      - key: camelot_v3
  base:
    tokenList:
      - symbol: USDT
      - symbol: WIF
      - symbol: PEPE
    dexList:
      - key: uniswap_v3
```

produces (for brevity):

```text
swapPairs = [
  { swapPairId: WIF~USDT~uniswap_v3~arbitrum, base: WIF,  quote: USDT, dex: uniswap_v3, chain: arbitrum },
  { swapPairId: WIF~USDT~camelot_v3~arbitrum, base: WIF,  quote: USDT, dex: camelot_v3, chain: arbitrum },
  { swapPairId: WIF~USDT~uniswap_v3~base,     base: WIF,  quote: USDT, dex: uniswap_v3, chain: base },
  { swapPairId: PEPE~USDT~uniswap_v3~base,    base: PEPE, quote: USDT, dex: uniswap_v3, chain: base },
]
```

	- **Fast-fail A – missing token coverage**: if any symbol in `tokens.base` or `tokens.quote` never appears in *any* `chains.*.tokenList`, throw:  
		- `Config error: token symbol "${s}" is listed in tokens.* but never appears in any chains.*.tokenList`.
	- **Fast-fail B – no `swapPair`s**: if, after processing all chains/DEXes, `swapPairs.length === 0`, throw:  
		- `Config error: no eligible swapPairs discovered; ensure tokens.* and chains.*.tokenList/dexList are configured consistently`.
	- **Adapter availability**: for each `swapPair.dex`, ensure there is a corresponding adapter/token in `src/common/tokens.ts` (or equivalent). If not, treat this as a configuration error and fail fast rather than silently skipping.

3. **Derive `arbitrargePair`s from `swapPair`s**  
	- Conceptually, an `arbitrargePair` ties together two venues (chain+DEX) for the same `(base, quote)` pair.  
	- For each ordered pair of `swapPair1`, `swapPair2` in `swapPairs` where:  
		- `swapPair1.base === swapPair2.base` and `swapPair1.quote === swapPair2.quote`, and  
		- `swapPair1.swapPairId !== swapPair2.swapPairId` (avoid self-pairing),  
	- Create:

```text
arbitrargePair = {
  arbitrargePairId:
    `${base}~${quote}~${swapPair1.dex}+${swapPair1.chain}~${swapPair2.dex}+${swapPair2.chain}`,
  swapPair1,
  swapPair2,
}
```

	- Same-chain and cross-chain routes are both allowed:  
		- Same-chain DEX↔DEX: `swapPair1.chain === swapPair2.chain` but `swapPair1.dex !== swapPair2.dex`.  
		- Cross-chain: `swapPair1.chain !== swapPair2.chain` (DEX keys may be equal or different).
	- In implementation, each `arbitrargePair` becomes a `TradingPairConfig` with:  
		- `baseToken = base`, `quoteToken = quote`.  
		- `chainM = swapPair1.chain`, `dexJ = swapPair1.dex`.  
		- `chainN = swapPair2.chain`, `dexK = swapPair2.dex`.  
		- `id = arbitrargePairId` (or a similar deterministic encoding).
	- **Fast-fail C – no `arbitrargePair`s**: if `arbitrargePairs.length === 0`, throw:  
		- `Config error: no arbitrargePairs discovered; ensure at least two venues share the same base/quote pair`.

4. **Deterministic ordering and stability**  
	- Construct `symbolPairs`, `swapPairs`, and `arbitrargePairs` using sorted iterations over:  
		- Base symbols, then quote symbols.  
		- Chain ids (`chainId` strings).  
		- DEX keys within each chain.
	- After building `arbitrargePairs` (or the derived `TradingPairConfig[]` list), apply a final sort by:

```text
(baseToken ASC, quoteToken ASC, chainM ASC, chainN ASC, dexJ ASC, dexK ASC)
```

	- This ensures the exact same `config.yaml` always yields the same ordered discovery output, simplifying testing and debugging.

Error modes summary (aligned with the flow):

- **Missing token coverage** – any symbol in `tokens.base` or `tokens.quote` not present in any `chains.*.tokenList` must fail discovery with a clear config error (Fast-fail A).  
- **No swapPairs** – if no venues support any `(base, quote)` from `tokens`, discovery must fail (Fast-fail B).  
- **No arbitrargePairs** – if `swapPairs` exist but there is never more than one venue per `(base, quote)`, discovery must fail (Fast-fail C).  
- **Unsupported DEX keys** – any DEX key present in `chains.*.dexList` but lacking a corresponding adapter/token mapping should be treated as a hard configuration error rather than silently skipped.  
- **Non-deterministic iteration (to avoid)** – unsorted iteration over tokens, chains, or DEX lists can lead to unstable output; sorting at each step is required.

These rules apply whether the algorithm is coded as a pure helper or wrapped in a Nest discovery service. The key behavior is that configuration gaps or drifts are surfaced early and loudly, and the final `TradingPairConfig[]` universe of arbitrageable pairs is deterministic for a given config.