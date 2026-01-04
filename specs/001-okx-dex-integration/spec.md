# Feature Specification: OKX DEX Integration

**Feature Branch**: `001-okx-dex-integration`
**Created**: 2026-01-02
**Status**: Draft
**Input**: User description: "Integrate OKX dex: OKX DEX is an all-in-one trading aggregator for multi-chain and cross-chain transactions. We need the arbitrarge bot to support OKX dex."

## Clarifications

### Session 2026-01-02

- **Q**: Should OKX DEX be integrated as a traditional per-chain DEX or as a multi-chain aggregator with special discovery semantics? → **A**: OKX DEX MUST be integrated as a multi-chain aggregator requiring dedicated pair discovery flow (User Story 1) that treats aggregators as venue providers across chains, enables self-pairing for same-aggregator routes, and uses `aggregator-mulchain` configuration section
- **Q**: What is the priority of aggregator-aware pair discovery relative to OKX DEX price quoting and swap execution? → **A**: Aggregator discovery is P1 (highest priority after foundational infrastructure) - it enables all downstream OKX DEX functionality by allowing aggregator routes to be discovered
- **Q**: How should aggregator routes be represented in the existing `TradingPairConfig` structure? → **A**: Reuse existing `dexJ/dexK` fields to store aggregator keys (e.g., `okx`), interpreting `(chainId, dexKey)` as a generic "venue key" that may be either a native DEX key or an aggregator key
- **Q**: Should "Balance Queries" be higher priority than "Swap Execution"? → **A**: Yes, Balance Queries (P3) should be higher priority than Swap Execution (P4) because balance validation is a prerequisite for safe execution, follows progressive complexity (read-only before state-changing), and enables accurate position sizing before attempting swaps

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - Multi-Chain DEX Aggregator Discovery Flow (Priority: P1)

The arbitrage bot's pair discovery system supports multi-chain DEX aggregators (like OKX DEX) as first-class venues alongside traditional DEXs. At startup, the discovery process enumerates aggregator keys from configuration, generates swap pairs for each aggregator on each chain where tokens exist, and derives arbitrage pairs allowing same-aggregator routes (where buy/sell through the same aggregator may produce price gaps via different underlying DEX pools).

**Why this priority**: This is the foundational infrastructure - without aggregator-aware pair discovery, OKX DEX cannot participate in arbitrage route detection at all. This extends the existing discovery algorithm to treat aggregators as venue providers across multiple chains, enabling all downstream OKX DEX functionality.

**Independent Test**: Can be tested by adding `aggregator-mulchain.okx.enabled: true` to configuration, running pair discovery at startup, and verifying that OKX aggregator routes are discovered alongside traditional DEX routes without requiring actual OKX API calls.

**Acceptance Scenarios**:

1. **Given** Configuration includes `aggregator-mulchain.okx.enabled: true` and WIF/USDT tokens on Arbitrum and Base, **When** pair discovery runs at startup, **Then** OKX aggregator swap pairs are generated for both chains and arbitrage pairs are derived including OKX→OKX same-chain routes
2. **Given** OKX aggregator is enabled but API credentials are missing from environment variables, **When** pair discovery runs, **Then** discovery completes successfully (credentials validated later during adapter initialization) but OKX adapter will fail-fast when initialized
3. **Given** OKX aggregator is enabled alongside traditional DEXs (Uniswap V3, PancakeSwap V3), **When** pair discovery runs, **Then** discovered routes include aggregator→DEX, DEX→aggregator, and aggregator→aggregator combinations
4. **Given** Only one aggregator (OKX) is enabled with tokens on two chains, **When** pair discovery runs, **Then** cross-chain aggregator arbitrage pairs are discovered in format `WIF~USDT~okx+arbitrum~okx+base`
5. **Given** OKX aggregator configuration is malformed or missing required fields, **When** pair discovery runs, **Then** discovery fails fast with clear error message indicating invalid aggregator configuration

---

### User Story 2 - OKX DEX Price Quoting (Priority: P2)

The arbitrage bot discovers and quotes prices from OKX DEX alongside existing DEXs (Uniswap V3, PancakeSwap V3, Velodrome V2). When the orchestrator queries prices for a trading pair, OKX DEX provides aggregated quotes that may offer better rates than individual DEX venues.

**Why this priority**: This is the foundation - without OKX DEX quoting, the bot cannot identify arbitrage opportunities involving OKX DEX. Price discovery is the first step in the arbitrage pipeline.

**Independent Test**: Can be tested by configuring OKX DEX on a single chain, querying prices for known token pairs, and validating that quotes are returned correctly without executing any trades.

**Acceptance Scenarios**:

1. **Given** OKX DEX is configured on Ethereum with WETH/USDT pair, **When** PriceMonitor queries prices for this pair, **Then** OKX DEX returns a valid quote with price and output amount
2. **Given** OKX DEX is configured on multiple chains (Arbitrum, Base, BSC), **When** PriceMonitor queries prices for each chain, **Then** OKX DEX returns chain-specific quotes for supported pairs
3. **Given** OKX DEX API is temporarily unavailable, **When** PriceMonitor queries prices, **Then** the request times out gracefully and logs an error without crashing the orchestrator loop
4. **Given** A token pair is not supported by OKX DEX on a specific chain, **When** PriceMonitor queries prices, **Then** OKX DEX returns a clear "not supported" response

---

### User Story 3 - Balance Queries (Priority: P3)

The arbitrage bot queries token balances from OKX DEX venues to assess available capital for trading. Before executing a swap, the bot verifies sufficient balance exists for the required tokens.

**Why this priority**: Balance validation is a prerequisite for safe execution and prevents failed transactions. Balance queries are read-only operations (safer and simpler than state-changing swaps), enable accurate position sizing, and provide a validation checkpoint before attempting trades. This follows progressive complexity: discovery → quoting → balance validation → execution.

**Independent Test**: Can be tested by configuring a wallet with known token balances, querying balances via OKX DEX adapter, and verifying returned amounts match expected values.

**Acceptance Scenarios**:

1. **Given** A wallet holds 1000 USDT on Ethereum, **When** orchestrator queries quote token balance via OKX DEX, **Then** adapter returns "1000" (or equivalent wei units)
2. **Given** A wallet holds 0 WETH on Arbitrum, **When** orchestrator queries base token balance via OKX DEX, **Then** adapter returns "0"
3. **Given** OKX DEX API returns malformed balance data, **When** balance query executes, **Then** adapter logs an error and returns a safe default value (e.g., "0")

---

### User Story 4 - OKX DEX Swap Execution (Priority: P4)

When the arbitrage bot identifies a profitable opportunity involving OKX DEX, it executes the swap through OKX's aggregated routing. The bot submits transactions that OKX routes optimally across multiple DEXs to achieve the best execution.

**Why this priority**: Swap execution builds on balance validation (P3) and is the final step in the trading pipeline. After confirming sufficient capital via balance queries, the bot can safely execute state-changing transactions to capture arbitrage profits. This is appropriately placed after balance validation to follow the dependency chain: discovery → quoting → balance check → execution.

**Independent Test**: Can be tested in dry-run mode by simulating a profitable arbitrage scenario, executing the OKX DEX swap, and verifying the transaction flow and logs without broadcasting real transactions.

**Acceptance Scenarios**:

1. **Given** A profitable WETH→USDT swap opportunity on Ethereum via OKX DEX, **When** orchestrator executes the forward arbitrage plan, **Then** OKX DEX successfully executes the swap and returns a transaction hash
2. **Given** OKX DEX routes a swap across multiple DEXs (e.g., Uniswap + Curve), **When** the swap executes, **Then** the bot receives a single transaction hash representing the aggregated trade
3. **Given** OKX DEX returns a higher-than-expected slippage during execution, **When** the swap occurs, **Then** the transaction fails safely if slippage exceeds the configured threshold
4. **Given** Insufficient wallet balance for the swap, **When** orchestrator attempts execution, **Then** OKX DEX adapter returns a clear error and the orchestrator skips this opportunity

---

### User Story 5 - Multi-Chain OKX DEX Support (Priority: P5)

The arbitrage bot recognizes OKX DEX as a venue on all supported chains (Ethereum, Arbitrum, Base, Polygon, BSC). During pair discovery, OKX DEX appears as a configurable DEX option on each chain where it operates.

**Why this priority**: Multi-chain support maximizes arbitrage opportunities by enabling OKX DEX participation in both same-chain and cross-chain arbitrage routes.

**Independent Test**: Can be tested by configuring OKX DEX on all five supported chains, running pair discovery, and verifying that OKX DEX appears in the discovered trading pair routes.

**Acceptance Scenarios**:

1. **Given** OKX DEX configured on Arbitrum, Base, Ethereum, Polygon, and BSC, **When** pair discovery runs at startup, **Then** OKX DEX is included as a venue on each chain in the discovered TradingPairConfig list
2. **Given** A WIF/USDT pair exists on Arbitrum via Uniswap V3 and on BSC via OKX DEX, **When** pair discovery runs, **Then** a cross-chain arbitrage route is discovered combining these venues
3. **Given** OKX DEX is only configured on Ethereum and Arbitrum but not Polygon, **When** pair discovery runs, **Then** OKX DEX only appears as a venue on the configured chains
4. **Given** OKX DEX is added to an existing configuration, **When** the bot restarts, **Then** pair discovery automatically includes new OKX DEX routes without code changes

---

### Edge Cases

- What happens when OKX DEX API rate limits are exceeded during high-frequency price queries?
- How does the bot handle OKX DEX returning a quote for a different amount than requested (e.g., due to liquidity constraints)?
- What happens when OKX DEX supports a token pair on-chain but the specific token address differs from the configured address?
- How does the system handle OKX DEX SDK initialization failures (missing API keys, network issues)?
- What happens when OKX DEX routes a swap through a DEX that is temporarily unavailable?
- How does the bot handle OKX DEX returning quotes in different decimal precision than other DEXs?
- What happens when OKX DEX is configured on a chain but the chain's RPC is unavailable?
- How does the system handle OKX DEX timeout during swap execution (transaction submitted but no response)?
- What happens when aggregator configuration exists in `config.yaml` but environment variables for credentials are not set?
- How does pair discovery handle aggregator enabled but no tokens available on any chain for that aggregator?
- What happens when same-aggregator self-pairing generates a route but the aggregator's internal routing produces identical prices (no arbitrage opportunity)?
- How does the system prevent duplicate routes when aggregators are enabled alongside traditional DEXs on the same chain?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-000**: System MUST extend pair discovery to support multi-chain DEX aggregators via `aggregator-mulchain` configuration section in `config.yaml`
- **FR-000-1**: System MUST enumerate aggregator keys (e.g., `okx`) from `config['aggregator-mulchain']` during discovery startup
- **FR-000-2**: System MUST generate swap pairs for each aggregator on each chain where both base and quote tokens exist in `chains.{chainId}.tokenList`, UNLESS the aggregator is listed in that chain's `non-aggr` exclusion list
- **FR-000-3**: System MUST allow self-pairing for aggregator swap pairs (same aggregator on same chain for both buy/sell legs) to capture price gaps from different underlying DEX pools
- **FR-000-4**: System MUST derive aggregator arbitrage pairs in format `{base}~{quote}~{aggJ}+{chainM}~{aggK}+{chainN}` with deterministic ordering by `(baseToken, quoteToken, chainM, chainN, aggJ, aggK)`
- **FR-000-5**: System MUST support aggregator credential configuration via environment variables (OKX_API_KEY, OKX_SECRET_KEY, OKX_API_PASSPHRASE, OKX_PROJECT_ID) without logging credential values
- **FR-000-6**: System MUST treat aggregator keys lacking corresponding adapter mappings as configuration errors (fail-fast) rather than silently skipping
- **FR-000-7**: System MUST integrate aggregator discovery with existing pair discovery service, reusing `TradingPairConfig` fields (`dexJ`, `dexK`) to store aggregator keys
- **FR-000-8**: System MUST implement an opt-out configuration model where aggregators are globally enabled via `aggregator-mulchain.{aggregatorKey}.enabled: true` and supported on all chains by default unless explicitly excluded via `chains.{chainId}.non-aggr: [{excludedAggregatorKeys}]`
- **FR-001**: System MUST implement a new DexAdapter called `OkxDexService` that conforms to the existing DexAdapter interface
- **FR-002**: System MUST install and integrate the official OKX DEX SDK from `github.com/okx/okx-dex-sdk`
- **FR-003**: System MUST support OKX DEX price quoting via `estimateBuyQuoteToBase` and `estimateSellBaseToQuote` methods
- **FR-004**: System MUST support balance queries via `getBalanceQuote` and `getBalanceBase` methods (higher priority than swap execution as it enables safe trade validation)
- **FR-005**: System MUST support OKX DEX swap execution via `swapQuoteToBase` and `swapBaseToQuote` methods (builds on balance validation)
- **FR-006**: System MUST register OKX DEX adapter in the DexModule with provider token `DEX_OKX_DEX`
- **FR-007**: System MUST allow OKX DEX to be configured on any supported chain (Ethereum, Arbitrum, Base, Polygon, BSC) via `config.yaml` by default when enabled in `aggregator-mulchain`
- **FR-008**: System MUST allow specific chains to exclude OKX DEX via `chains.{chainId}.non-aggr: ['okx']` configuration when needed
- **FR-009**: System MUST include OKX DEX in pair discovery when configured on a chain with both base and quote tokens
- **FR-010**: System MUST handle OKX DEX API errors gracefully without crashing the orchestrator loop
- **FR-011**: System MUST log all OKX DEX operations (quotes, swaps, balance queries) with structured JSON logging
- **FR-012**: System MUST respect configured slippage thresholds when executing OKX DEX swaps
- **FR-013**: System MUST validate token addresses before passing them to OKX DEX SDK to prevent invalid transactions
- **FR-014**: System MUST support both dry-run and live execution modes for OKX DEX operations
- **FR-015**: System MUST handle OKX DEX API timeouts within the configured `priceRequestTimeoutMs` threshold
- **FR-016**: System MUST normalize OKX DEX quote responses to match the standard `QuoteToBaseEstimate` and `BaseToQuoteEstimate` interfaces
- **FR-017**: System MUST validate that OKX DEX SDK initialization succeeds before allowing quotes or swaps
- **FR-018**: System MUST provide clear error messages when OKX DEX does not support a requested token pair on a specific chain
- **FR-019**: System MUST support OKX DEX configuration via environment variables for API keys or credentials (if required)
- **FR-020**: System MUST include unit tests for OKX DEX adapter covering all DexAdapter interface methods
- **FR-021**: System MUST include integration tests for OKX DEX adapter with mocked SDK responses

### Key Entities

- **Aggregator Swap Pair**: Represents a trading venue for a token pair on a specific chain via an aggregator (e.g., OKX DEX). Key attributes: `swapPairId` (format: `{base}~{quote}~{aggregator}~{chainId}`), base token, quote token, aggregator key (e.g., `okx`), chain ID
- **Aggregator Arbitrage Pair**: Derived from two aggregator swap pairs for the same token pair, enabling arbitrage routes between aggregators or between aggregators and traditional DEXs. Key attributes: `arbitrargePairId`, `swapPair1` (entry leg), `swapPair2` (exit leg). Maps to `TradingPairConfig` with `dexJ/dexK` fields storing aggregator keys
- **Multi-Chain Aggregator Configuration**: Configuration in `config.yaml` under `aggregator-mulchain` section defining enabled aggregators (opt-out model). Example: `{ okx: { enabled: true } }`. Aggregators are supported on all chains by default unless explicitly excluded via `chains.{chainId}.non-aggr: ['okx']`. Credentials sourced from environment variables (OKX_API_KEY, OKX_SECRET_KEY, etc.)
- **OKX DEX Adapter**: A DexAdapter implementation that wraps the OKX DEX SDK, providing quoting, balance query, and swapping capabilities. Key attributes: chain ID, aggregator key (`okx`), SDK client instance, configuration service reference, logger instance. Balance query methods (`getBalanceQuote`, `getBalanceBase`) are implemented before swap methods to enable pre-execution validation
- **OKX DEX Quote Response**: Raw response from OKX DEX SDK containing output amount, price, route information (if available), and estimated gas. Must be normalized to standard adapter interfaces
- **OKX DEX Balance Response**: Response from OKX DEX SDK containing wallet balance information for a specific token. Must be normalized to string format matching other DEX adapters. Critical for validating sufficient capital before executing swaps
- **OKX DEX Swap Receipt**: Transaction response from OKX DEX containing transaction hash, status, and any transfer IDs for cross-chain operations. Normalized to standard `DexSwapReceipt` interface

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: OKX DEX adapter successfully returns valid quotes for at least 95% of supported token pairs on configured chains within 5 seconds
- **SC-002**: OKX DEX balance queries return accurate wallet balances for configured tokens within 3 seconds, enabling pre-execution capital validation
- **SC-003**: Pair discovery includes OKX DEX as a venue on all configured chains where token pairs are available
- **SC-004**: OKX DEX adapter handles API errors (rate limits, timeouts, unsupported pairs) without crashing the orchestrator loop
- **SC-005**: Unit test coverage for OKX DEX adapter exceeds 80% of code paths including error scenarios
- **SC-006**: Integration tests validate end-to-end OKX DEX operations (quote, balance, swap) with mocked SDK responses, following dependency order
- **SC-007**: OKX DEX configuration can be added to any supported chain via `config.yaml` without code changes
- **SC-008**: OKX DEX quotes return prices within expected market ranges (validated against other DEXs for same token pairs)
- **SC-009**: Arbitrage opportunities involving OKX DEX are correctly identified and logged by the orchestrator
- **SC-010**: OKX DEX swap execution completes successfully in dry-run mode for all test scenarios without transaction broadcasting (after balance validation is confirmed)
- **SC-011**: OKX DEX adapter initialization fails fast with clear error messages when SDK credentials or configuration are invalid

## Assumptions

1. OKX DEX SDK is compatible with Node.js v24+ and TypeScript strict mode
2. OKX DEX SDK provides quote, balance query, and swap methods that can be wrapped by the DexAdapter interface (in dependency order)
3. OKX DEX supports token pairs for all base tokens (WIF, PEPE) and quote tokens (USDT, USDC) currently configured
4. OKX DEX API or SDK does not require paid API keys for basic quoting functionality (or keys can be provided via environment variables)
5. OKX DEX SDK returns quotes and balances in a format that can be normalized to the bot's standard interfaces
6. OKX DEX operates on all five chains currently supported by the arbitrage bot (Ethereum, Arbitrum, Base, Polygon, BSC)
7. OKX DEX provides aggregated quotes by routing across multiple DEXs internally, abstracting route complexity from the bot
8. OKX DEX swap execution returns a standard Ethereum-style transaction hash for on-chain transactions
9. OKX DEX has rate limits that can be respected with the bot's current retry/backoff mechanisms
10. OKX DEX SDK documentation is sufficient to implement the required adapter methods
11. Existing pair discovery infrastructure can be extended to support aggregators without breaking traditional DEX discovery
12. Aggregator self-pairing (same aggregator on same chain for both legs) will produce meaningful price differences due to routing across different underlying DEX pools
13. Aggregator credentials (API keys, secrets) can be sourced from environment variables and are not required to be stored in config.yaml
14. The `TradingPairConfig` data structure's `dexJ/dexK` fields can safely store aggregator keys (e.g., `okx`) alongside traditional DEX keys (e.g., `uniswap_v3`)
15. Aggregators follow an opt-out configuration model: when enabled globally via `aggregator-mulchain.{aggregatorKey}.enabled: true`, they are supported on all chains by default unless explicitly excluded via `chains.{chainId}.non-aggr: [{excludedAggregatorKeys}]`
16. The `non-aggr` exclusion list allows per-chain opt-out from specific aggregators without requiring changes to the aggregator's global configuration
17. Pair discovery algorithm's deterministic sorting can accommodate aggregator keys without changing existing ordering logic
18. Balance query operations can be executed independently from swap operations and do not require transaction signing, making them safer to implement and test first

## Dependencies & Prerequisites

1. OKX DEX SDK from `github.com/okx/okx-dex-sdk` must be available as a Node.js package
2. OKX DEX API or SDK documentation must specify quote, balance query, and swap methods (in priority order)
3. OKX DEX must support the token addresses currently configured in the bot for each chain
4. RPC endpoints for all configured chains must be accessible from the bot's deployment environment
5. Wallet credentials (private keys) must be available for signing OKX DEX transactions in live mode
6. Existing DexAdapter interface must remain stable for OKX DEX adapter implementation (balance query methods implemented before swap methods)
7. ConfigService must support reading the new `aggregator-mulchain` configuration section from `config.yaml`
8. Existing pair discovery service must be extensible to support aggregator enumeration and swap pair generation
9. Environment variable loading mechanism must support OKX credential variables (OKX_API_KEY, OKX_SECRET_KEY, OKX_API_PASSPHRASE, OKX_PROJECT_ID)
10. `TradingPairConfig` type definition must accommodate aggregator keys in `dexJ/dexK` fields without breaking existing routes
11. OKX DEX SDK must provide balance query methods that can be called independently from swap operations to support pre-execution validation

## Non-Goals (Explicitly Out of Scope)

1. Implementing custom routing logic to compete with OKX DEX's internal aggregation
2. Supporting OKX DEX cross-chain swaps as a bridge replacement (using Stargate for bridging)
3. Building a custom OKX DEX API client (using official SDK)
4. Real-time monitoring of OKX DEX's internal routing decisions or DEX selection
5. Dynamic addition/removal of OKX DEX support during runtime (requires restart)
6. GUI or dashboard for visualizing OKX DEX quotes and routes
7. Historical analysis of OKX DEX quote accuracy or execution quality
8. Support for OKX DEX features beyond standard swapping (e.g., limit orders, advanced routing options)
9. Implementing fallback to individual DEXs when OKX DEX fails (treat as single venue)
10. Optimizing gas costs specific to OKX DEX routing (using bot's standard gas estimation)
