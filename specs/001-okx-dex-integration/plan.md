# Implementation Plan: OKX DEX Integration

**Branch**: `001-okx-dex-integration` | **Date**: 2026-01-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-okx-dex-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Integrate OKX DEX as a multi-chain aggregator venue into the arbitrage bot. OKX DEX provides aggregated quotes by routing across multiple DEXs internally. The integration requires: (1) extending pair discovery to support aggregators, (2) implementing OKX DEX adapter with quoting, balance queries, and swap execution, (3) supporting all 5 chains (Ethereum, Arbitrum, Base, Polygon, BSC), and (4) following dependency order: discovery → quoting → balance validation → swap execution.

## Technical Context

**Language/Version**: TypeScript 5.x (Node.js v24+), pnpm 10.x
**Primary Dependencies**:
- Official OKX DEX SDK from `github.com/okx/okx-dex-sdk` (NEEDS CLARIFICATION: SDK availability, API structure, authentication method)
- Existing NestJS framework modules (DexModule, ConfigService, LoggerService)
- ethers.js v6 (already in project for blockchain interactions)

**Storage**: N/A (stateless trading bot, in-memory pair discovery)
**Testing**: Jest with TDD workflow (co-located `*.spec.ts`, integration tests in `test/`)
**Target Platform**: Linux server (Node.js runtime, pnpm 10.x version manager)
**Project Type**: Single TypeScript project in `code/ts/`
**Performance Goals**:
- Price quotes: <5 seconds per OKX DEX API call
- Balance queries: <3 seconds per query
- Pair discovery at startup: <10 seconds total
- Must not block orchestrator 1-second loop

**Constraints**:
- Must work in dry-run mode (no transaction signing/broadcasting)
- Must handle OKX API rate limits gracefully
- Must validate all OKX SDK responses before use
- Must follow existing DexAdapter interface pattern

**Scale/Scope**:
- 5 blockchain networks (Ethereum, Arbitrum, Base, Polygon, BSC)
- ~4-6 trading pairs (WIF, PEPE × USDT, USDC)
- Single adapter implementation following existing pattern (UniswapV3Service, PancakeswapV3Service, VelodromeV2Service)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] Code Quality: Type safety (`unknown` not `any`), immutability, proper async/await usage
  - OKX adapter will follow existing UniswapV3Service pattern with strict typing
  - All OKX SDK responses will be validated and typed

- [x] Testing: TDD workflow, coverage for critical paths (price calculations, risk control, DEX/bridge operations)
  - Will write tests BEFORE implementation (Red-Green-Refactor)
  - Unit tests: `okx-dex.service.spec.ts` co-located with adapter
  - Integration tests: `test/dex/okx-dex.integration.spec.ts` with mocked SDK
  - Coverage target: >80% for all adapter methods (FR-020)

- [x] User Experience: Dry-run mode support, structured logging with operation contexts
  - OKX adapter will respect existing dry-run flag in WalletService
  - All operations will use LoggerService with operation-scoped contexts (FR-011)
  - Logs will include: chainId, aggregator key, trading pair, amounts, txHash

- [x] Performance: Trading loop within `loopIntervalMs`, price fetching <3s, RPC reliability
  - OKX API calls have 5-second SLA for quotes, 3-second SLA for balances (SC-001, SC-002)
  - Will implement exponential backoff for rate limiting (constitution requirement)
  - Will timeout OKX calls within `priceRequestTimeoutMs` (FR-015)

- [x] Security: Key management (no hardcoded keys), input validation, risk control integration
  - OKX credentials via environment variables only (OKX_API_KEY, OKX_SECRET_KEY, etc.)
  - All OKX SDK responses validated before use (FR-013)
  - Adapter integrates with existing RiskManager for trade approval

**Result**: ✅ All constitution requirements satisfied. No violations.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
code/ts/                                    # TypeScript root (per constitution)
├── src/
│   ├── common/
│   │   └── tokens.ts                       # DI tokens (add DEX_OKX_DEX)
│   ├── dex/
│   │   ├── dex-adapter.interface.ts        # Existing interface (implement)
│   │   ├── dex.module.ts                   # Register OKX adapter here
│   │   ├── uniswap-v3.service.ts           # Reference pattern
│   │   ├── pancakeswap-v3.service.ts       # Reference pattern
│   │   ├── velodrome-v2.service.ts         # Reference pattern
│   │   ├── okx-dex.service.ts              # NEW: OKX DEX adapter
│   │   └── okx-dex.service.spec.ts         # NEW: Unit tests (TDD)
│   ├── orchestrator/
│   │   └── pair-discovery/
│   │       ├── pair-discovery.service.ts   # Extend for aggregators (opt-out model)
│   │       └── pair-discovery.helper.ts    # Extend for aggregators (check non-aggr)
│   ├── utils/
│   │   ├── config/
│   │   │   ├── config.service.ts           # Add aggregator-mulchain schema + non-aggr support
│   │   │   └── config.types.ts             # Add aggregator types + ChainConfig.nonAggr
│   │   └── logger/
│   │       └── logger.service.ts           # Use for structured logging
│   └── wallet/
│       └── wallet.service.ts               # Respects dry-run mode
└── test/
    └── dex/
        └── okx-dex.integration.spec.ts     # NEW: Integration tests
```

**Structure Decision**: Single TypeScript project following existing NestJS pattern. OKX adapter co-located with other DEX adapters in `src/dex/`. Tests follow TDD workflow with co-located unit tests (`*.spec.ts`) and integration tests in `test/dex/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | Constitution satisfied with no violations | N/A |

---

## Phase 0: Research & Technology Decisions

**Status**: ✅ COMPLETE

**Output**: [research.md](./research.md)

**Decisions Made**:
1. **SDK Choice**: Use official `@okx-dex/okx-dex-sdk` v1.0.17 (production-ready, full TypeScript support)
2. **Authentication**: 4 environment variables (OKX_API_KEY, OKX_SECRET_KEY, OKX_API_PASSPHRASE, OKX_PROJECT_ID)
3. **Balance Queries**: Use ethers.js directly (consistent with existing adapters)
4. **Multi-Chain Support**: All 5 required chains supported (Ethereum, Arbitrum, Base, Polygon, BSC)
5. **Adapter Pattern**: Follow existing DexAdapter interface (UniswapV3Service pattern)

**Resolved All Clarifications**:
- ✅ SDK availability and structure
- ✅ Authentication method
- ✅ Quote/Swap API methods
- ✅ Balance query strategy
- ✅ Multi-chain support
- ✅ TypeScript definitions

---

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETE

**Outputs**:
- [data-model.md](./data-model.md) - Entity definitions, validation rules, state transitions
- [contracts/okx-dex-adapter.md](./contracts/okx-dex-adapter.md) - API contract, error codes, logging format, security requirements
- [quickstart.md](./quickstart.md) - Developer onboarding guide with code examples

**Design Artifacts**:

### Data Model
- **AggregatorSwapPair**: Venue representation with aggregator key, chain, token addresses
- **AggregatorArbitragePair**: Derived from two swap pairs, enables aggregator→aggregator routes
- **AggregatorMultichainConfig**: Configuration for enabling aggregators (opt-out model)
- **TradingPairConfig Extension**: Reuses existing `dexJ/dexK` fields for aggregator keys (backward compatible)
- **Configuration Model**: Global enable via `aggregator-mulchain.{aggregatorKey}.enabled: true` + per-chain exclude via `chains.{chainId}.non-aggr: [{excludedAggregatorKeys}]`

### API Contract
- **Interface**: `OkxDexAdapter` extends `DexAdapter` (7 methods)
- **Error Codes**: 10 error codes with retry strategies
- **Logging Contract**: Structured JSON logging with operation contexts
- **Performance SLAs**: Quotes <5s, balances <3s, swaps <10s
- **Security Contract**: Environment-based credentials, input validation, dry-run mode

### Quickstart Guide
- Prerequisites (SDK install, credentials, env setup)
- Step-by-step implementation (6 steps)
- Troubleshooting guide
- Testing workflow (TDD)

**Agent Context Update**: ✅ Completed
- Updated CLAUDE.md with TypeScript 5.x and project structure info

---

## Phase 2: Implementation Planning

**Status**: 🔄 NEXT STEP (run `/speckit.tasks` to generate)

**Pending**: Generate `tasks.md` with dependency-ordered implementation tasks

**Anticipated Task Breakdown**:

1. **Configuration Schema Updates** (Priority: P0 - Foundation)
   - Add `AggregatorMultichainConfig` type
   - Extend `config.schema.ts` for `aggregator-mulchain` validation
   - Add `non-aggr` field to `ChainConfig` type (exclusion list)
   - Add getter methods to `ConfigService`

2. **Pair Discovery Extensions** (Priority: P1 - User Story 1)
   - Implement aggregator enumeration in `pair-discovery.helper.ts`
   - Add aggregator swap pair generation with opt-out logic (check `non-aggr` exclusion)
   - Support self-pairing for same-aggregator routes
   - Update fast-fail validation

3. **OKX DEX Adapter - Quotes** (Priority: P2 - User Story 2)
   - Implement `estimateBuyQuoteToBase` with OKX SDK
   - Implement `estimateSellBaseToQuote` with OKX SDK
   - Add error handling and retries
   - Write unit tests (TDD)

4. **OKX DEX Adapter - Balance Queries** (Priority: P3 - User Story 3)
   - Implement `getBalanceQuote` using ethers.js
   - Implement `getBalanceBase` using ethers.js
   - Add safe defaults on errors
   - Write unit tests (TDD)

5. **OKX DEX Adapter - Swaps** (Priority: P4 - User Story 4)
   - Implement `swapQuoteToBase` with dry-run mode
   - Implement `swapBaseToQuote` with dry-run mode
   - Add transaction signing and execution
   - Write unit tests (TDD)

6. **Module Integration** (Priority: P5)
   - Register `OkxDexService` in `DexModule`
   - Add `DEX_OKX_DEX` provider token
   - Export adapter from module

7. **Testing & Validation** (Priority: P6 - Quality Assurance)
   - Integration tests with mocked SDK
   - Dry-run mode testing
   - Pair discovery integration tests
   - Performance validation (SLAs)
   - Security validation (credentials, input validation)

8. **Multi-Chain Expansion** (Priority: P7 - User Story 5)
   - Test on all 5 chains (Ethereum, Arbitrum, Base, Polygon, BSC)
   - Validate chain ID mappings
   - Test cross-chain arbitrage routes

**Note**: Actual tasks will be generated by `/speckit.tasks` command with proper dependencies and acceptance criteria.

---

## Constitution Re-Check (Post Phase 1)

*Re-validate after design is complete*

- [x] Code Quality: Type safety maintained, adapter follows existing patterns
- [x] Testing: TDD workflow planned in quickstart, >80% coverage target defined
- [x] User Experience: Dry-run mode designed into all swap methods, structured logging defined
- [x] Performance: SLAs defined (quotes 5s, balances 3s), rate limiting strategy documented
- [x] Security: Environment-based credentials, input validation requirements specified

**Result**: ✅ All constitution requirements still satisfied. Design phase introduced no violations.

---

## Implementation Readiness

**Gate Status**: ✅ READY FOR PHASE 2

**Completed Artifacts**:
- ✅ Research complete (all clarifications resolved)
- ✅ Data model defined (4 core entities)
- ✅ API contract specified (7 methods, 10 error codes)
- ✅ Developer quickstart available (step-by-step guide)
- ✅ Agent context updated
- ✅ Constitution verified (pre- and post-design)

**Next Command**: Run `/speckit.tasks` to generate dependency-ordered implementation tasks

**Estimated Timeline**: 2-3 days for full implementation (including tests)
