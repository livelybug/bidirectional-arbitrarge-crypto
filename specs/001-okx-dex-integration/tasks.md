# Tasks: OKX DEX Integration

**Input**: Design documents from `/specs/001-okx-dex-integration/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/okx-dex-adapter.md, research.md

**Tests**: Tests are MANDATORY per project constitution (TDD workflow). All user stories MUST have test tasks defined below.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project root**: `code/ts/` (TypeScript project per plan.md)
- **Tests**: Co-located unit tests in `src/**/*.spec.ts`, integration tests in `test/**/*.integration.spec.ts`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project dependencies and SDK installation

- [x] T001 Install OKX DEX SDK in code/ts/ using `pnpm add @okx-dex/okx-dex-sdk@^1.0.17` (requires manual execution)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core configuration infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Add `AggregatorMultichainConfig` type to code/ts/src/utils/config/config.types.ts
- [X] T004 [P] Add `non-aggr` field to `ChainConfig` type in code/ts/src/utils/config/config.types.ts
- [X] T005 [P] Add `okx_dex` to `ChainDexType` union in code/ts/src/utils/config/config.types.ts
- [X] T006 Add `aggregatorMultichainSchema` to code/ts/src/utils/config/config.schema.ts with validation
- [X] T007 [P] Extend `appConfigSchema` in code/ts/src/utils/config/config.schema.ts to include `aggregatorMultichain` field
- [X] T008 Add `getAggregatorMultichainConfig()` getter to code/ts/src/utils/config/config.service.ts
- [X] T009 Add `isAggregatorEnabled(aggregatorKey: string)` method to code/ts/src/utils/config/config.service.ts

**Checkpoint**: ✅ Foundation ready - aggregator configuration infrastructure complete

---

## Phase 3: User Story 1 - Multi-Chain DEX Aggregator Discovery Flow (Priority: P1) 🎯 MVP

**Goal**: Extend pair discovery to support multi-chain aggregators (OKX) with opt-out configuration model

**Independent Test**: Add `aggregator-mulchain.okx.enabled: true` to config, run pair discovery, verify OKX aggregator routes are discovered without actual API calls

### Tests for User Story 1 (MANDATORY ⚠️ TDD REQUIREMENT)

> **CONSTITUTION REQUIREMENT: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Write aggregator enumeration test in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.spec.ts
- [X] T011 [P] [US1] Write aggregator swap pair generation test in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.spec.ts
- [X] T012 [P] [US1] Write `non-aggr` exclusion logic test in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.spec.ts
- [X] T013 [P] [US1] Write aggregator arbitrage pair derivation test in code/ts/src/orchestrator/pair-discovery/pair-discovery.service.spec.ts

### Implementation for User Story 1

- [X] T014 [P] [US1] Implement `getEnabledAggregators()` helper in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts
- [X] T015 [P] [US1] Implement `generateAggregatorSwapPairs()` in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts
- [X] T016 [P] [US1] Implement `checkNonAggrExclusion()` helper in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts
- [X] T017 [US1] Extend `deriveArbitragePairs()` in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts to support aggregator self-pairing
- [X] T018 [US1] Update `discoverAllPairs()` in code/ts/src/orchestrator/pair-discovery/pair-discovery.service.ts to enumerate and include aggregators
- [X] T019 [US1] Add aggregator validation fail-fast logic to code/ts/src/orchestrator/pair-discovery/pair-discovery.service.ts

**Checkpoint**: At this point, User Story 1 should be fully functional - pair discovery includes OKX aggregator routes

---

## Phase 4: User Story 2 - OKX DEX Price Quoting (Priority: P2)

**Goal**: Implement OKX DEX price quoting via DexAdapter interface

**Independent Test**: Configure OKX on one chain, query prices for known pairs, validate quotes returned correctly

### Tests for User Story 2 (MANDATORY ⚠️ TDD REQUIREMENT)

> **CONSTITUTION REQUIREMENT: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T020 [P] [US2] Write `estimateBuyQuoteToBase` test in code/ts/src/dex/okx-dex.service.spec.ts (normal, timeout, unsupported pair)
- [ ] T021 [P] [US2] Write `estimateSellBaseToQuote` test in code/ts/src/dex/okx-dex.service.spec.ts (normal, high slippage, rate limit)
- [ ] T022 [P] [US2] Write quote response validation test in code/ts/src/dex/okx-dex.service.spec.ts

### Implementation for User Story 2

- [ ] T023 [P] [US2] Create OKX DEX adapter skeleton in code/ts/src/dex/okx-dex.service.ts implementing DexAdapter interface
- [ ] T024 [US2] Implement `validateCredentials()` private method in code/ts/src/dex/okx-dex.service.ts
- [ ] T025 [US2] Implement `initializeClient()` private method in code/ts/src/dex/okx-dex.service.ts
- [ ] T026 [US2] Implement `mapChainId()` helper in code/ts/src/dex/okx-dex.service.ts for chain ID mapping
- [ ] T027 [US2] Implement `estimateBuyQuoteToBase()` method in code/ts/src/dex/okx-dex.service.ts with OKX SDK call
- [ ] T028 [US2] Implement `estimateSellBaseToQuote()` method in code/ts/src/dex/okx-dex.service.ts with OKX SDK call
- [ ] T029 [US2] Add structured JSON logging for quote operations in code/ts/src/dex/okx-dex.service.ts
- [ ] T030 [US2] Add error handling and retry logic for quote methods in code/ts/src/dex/okx-dex.service.ts

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - OKX aggregator discovered and providing quotes

---

## Phase 5: User Story 3 - Balance Queries (Priority: P3)

**Goal**: Implement token balance queries using ethers.js (not OKX Balance API)

**Independent Test**: Configure wallet with known balances, query via OKX adapter, verify amounts match

### Tests for User Story 3 (MANDATORY ⚠️ TDD REQUIREMENT)

> **CONSTITUTION REQUIREMENT: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T031 [P] [US3] Write `getBalanceQuote` test in code/ts/src/dex/okx-dex.service.spec.ts (native token, ERC-20, zero balance)
- [ ] T032 [P] [US3] Write `getBalanceBase` test in code/ts/src/dex/okx-dex.service.spec.ts (native token, ERC-20, error handling)
- [ ] T033 [P] [US3] Write balance error handling test in code/ts/src/dex/okx-dex.service.spec.ts (malformed data, safe defaults)

### Implementation for User Story 3

- [ ] T034 [US3] Implement unified private `getBalance(tokenAddress, tokenType)` method in code/ts/src/dex/okx-dex.service.ts using ethers.js provider
- [ ] T035 [US3] Implement `getBalanceQuote()` method in code/ts/src/dex/okx-dex.service.ts to delegate to `getBalance(quoteToken, 'quote')`
- [ ] T036 [US3] Implement `getBalanceBase()` method in code/ts/src/dex/okx-dex.service.ts to delegate to `getBalance(baseToken, 'base')`
- [ ] T037 [US3] Add native token vs ERC-20 token detection logic to `getBalance()` in code/ts/src/dex/okx-dex.service.ts
- [ ] T038 [US3] Add safe default error handling (return "0" on errors) in code/ts/src/dex/okx-dex.service.ts
- [ ] T039 [US3] Add structured JSON logging for balance operations in code/ts/src/dex/okx-dex.service.ts

**Checkpoint**: All user stories 1-3 functional - OKX can discover routes, quote prices, and validate balances

---

## Phase 6: User Story 4 - OKX DEX Swap Execution (Priority: P4)

**Goal**: Implement swap execution with dry-run mode support

**Independent Test**: Simulate profitable arbitrage, execute OKX swap in dry-run mode, verify transaction flow

### Tests for User Story 4 (MANDATORY ⚠️ TDD REQUIREMENT)

> **CONSTITUTION REQUIREMENT: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T039 [P] [US4] Write `swapQuoteToBase` dry-run test in code/ts/src/dex/okx-dex.service.spec.ts
- [ ] T040 [P] [US4] Write `swapBaseToQuote` dry-run test in code/ts/src/dex/okx-dex.service.spec.ts
- [ ] T041 [P] [US4] Write swap execution error test in code/ts/src/dex/okx-dex.service.spec.ts (insufficient balance, high slippage)

### Implementation for User Story 4

- [ ] T042 [US4] Implement `swapQuoteToBase()` method in code/ts/src/dex/okx-dex.service.ts with dry-run mode check
- [ ] T043 [US4] Implement `swapBaseToQuote()` method in code/ts/src/dex/okx-dex.service.ts with dry-run mode check
- [ ] T044 [US4] Add `simulateAsyncLatency()` helper to code/ts/src/dex/okx-dex.service.ts for dry-run delay simulation
- [ ] T045 [US4] Integrate OKX SDK `executeSwap()` call in code/ts/src/dex/okx-dex.service.ts for live mode
- [ ] T046 [US4] Add transaction hash logging and block explorer URL to swap operations in code/ts/src/dex/okx-dex.service.ts
- [ ] T047 [US4] Add slippage validation and error handling to swap methods in code/ts/src/dex/okx-dex.service.ts

**Checkpoint**: Core OKX DEX functionality complete - all user stories 1-4 working end-to-end

---

## Phase 7: User Story 5 - Multi-Chain OKX DEX Support (Priority: P5)

**Goal**: Ensure OKX DEX works correctly on all 5 supported chains (Ethereum, Arbitrum, Base, Polygon, BSC)

**Independent Test**: Configure OKX on all 5 chains, run pair discovery, verify OKX appears in all chain routes

### Tests for User Story 5 (MANDATORY ⚠️ TDD REQUIREMENT)

> **CONSTITUTION REQUIREMENT: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T048 [P] [US5] Write multi-chain quote test in code/ts/test/dex/okx-dex.integration.spec.ts
- [ ] T049 [P] [US5] Write chain ID mapping test in code/ts/src/dex/okx-dex.service.spec.ts for all 5 chains
- [ ] T050 [P] [US5] Write cross-chain arbitrage pair discovery test in code/ts/src/orchestrator/pair-discovery/pair-discovery.service.spec.ts

### Implementation for User Story 5

- [ ] T051 [US5] Verify chain ID mappings in `mapChainId()` helper cover all 5 chains in code/ts/src/dex/okx-dex.service.ts
- [ ] T052 [US5] Test OKX adapter instantiation per-chain pattern in code/ts/src/dex/dex.module.ts (one instance per chain)
- [ ] T053 [US5] Validate pair discovery generates OKX routes for all configured chains in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts
- [ ] T054 [US5] Test cross-chain arbitrage pair derivation with OKX in code/ts/src/orchestrator/pair-discovery/pair-discovery.helper.ts

**Checkpoint**: All user stories complete - full multi-chain OKX DEX integration functional

---

## Phase 8: Module Integration & Registration

**Purpose**: Register OKX DEX adapter in NestJS dependency injection system

- [ ] T055 [P] Add `DEX_OKX_DEX` provider token to code/ts/src/common/tokens.ts
- [ ] T056 Register `OkxDexService` in code/ts/src/dex/dex.module.ts providers array
- [ ] T057 Export `OkxDexService` from code/ts/src/dex/dex.module.ts exports array
- [ ] T058 [P] Add per-chain OKX adapter factory pattern to code/ts/src/dex/dex.module.ts

---

## Phase 9: Testing & Quality Assurance

**Purpose**: Integration tests, validation, and constitution compliance

- [ ] T059 [P] Write end-to-end integration test in code/ts/test/dex/okx-dex.integration.spec.ts (quote → balance → swap flow)
- [ ] T060 [P] Write pair discovery integration test in code/ts/test/dex/okx-dex.integration.spec.ts with mocked SDK
- [ ] T061 [P] Write dry-run vs live mode test in code/ts/test/dex/okx-dex.integration.spec.ts
- [ ] T062 [P] Write error recovery test in code/ts/test/dex/okx-dex.integration.spec.ts (SDK failure, graceful degradation)
- [ ] T063 Verify >80% code coverage by running `pnpm test:cov` for OKX adapter
- [ ] T064 Run all tests with `pnpm test` and ensure no regressions
- [ ] T065 Run linter with `pnpm run lint` and fix any issues in OKX adapter code
- [ ] T066 Validate input validation implementation per constitution requirement in code/ts/src/dex/okx-dex.service.ts
- [ ] T067 Verify credential security (no hardcoded keys) in code/ts/src/dex/okx-dex.service.ts

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, performance validation, and production readiness

- [ ] T068 [P] Verify quickstart.md examples match implementation in specs/001-okx-dex-integration/quickstart.md
- [ ] T069 [P] Add JSDoc comments to public methods in code/ts/src/dex/okx-dex.service.ts
- [ ] T070 Run performance validation - verify quotes <5s, balances <3s per SLA in contracts/okx-dex-adapter.md
- [ ] T071 Test rate limiting and exponential backoff logic in code/ts/src/dex/okx-dex.service.ts
- [ ] T072 Verify all OKX operations emit structured JSON logs per logging contract in contracts/okx-dex-adapter.md
- [ ] T073 Test opt-out configuration model - verify `non-aggr` exclusion works correctly
- [ ] T074 Validate configuration schema with `pnpm run config:print` and check aggregator-mulchain section
- [ ] T075 Run quickstart.md validation by following steps in specs/001-okx-dex-integration/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Module Integration (Phase 8)**: Depends on User Stories 1-4 (adapter implementation complete)
- **Testing (Phase 9)**: Depends on Module Integration completion
- **Polish (Phase 10)**: Depends on Testing completion

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independently testable (mocked SDK)
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independently testable (read-only operations)
- **User Story 4 (P4)**: Depends on User Story 3 (balance validation prerequisite per spec)
- **User Story 5 (P5)**: Depends on User Stories 1-4 (requires adapter functional on all chains)

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD Red-Green-Refactor)
- Test files marked [P] can be written in parallel
- Implementation tasks follow test completion
- Helper methods before main adapter methods
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- All test tasks marked [P] within a user story can run in parallel
- Module integration tasks marked [P] can run in parallel
- Testing tasks marked [P] can run in parallel
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 2 (Price Quoting)

```bash
# Launch all tests for User Story 2 together:
Task: "Write estimateBuyQuoteToBase test in okx-dex.service.spec.ts"
Task: "Write estimateSellBaseToQuote test in okx-dex.service.spec.ts"
Task: "Write quote response validation test in okx-dex.service.spec.ts"

# After tests fail, implement adapter:
Task: "Create OKX DEX adapter skeleton in okx-dex.service.ts"

# Then implement methods sequentially (each depends on helpers):
Task: "Implement validateCredentials() method"
Task: "Implement initializeClient() method"
Task: "Implement mapChainId() helper"
Task: "Implement estimateBuyQuoteToBase() method"
Task: "Implement estimateSellBaseToQuote() method"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (SDK installation)
2. Complete Phase 2: Foundational (config infrastructure) - CRITICAL
3. Complete Phase 3: User Story 1 (aggregator discovery)
4. **STOP and VALIDATE**: Test pair discovery with OKX aggregator enabled
5. Deploy/demo if ready - aggregator routes discovered, ready for quoting implementation

### Incremental Delivery (Recommended)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: aggregator discovery!)
3. Add User Story 2 → Test independently → Deploy/Demo (quotes working)
4. Add User Story 3 → Test independently → Deploy/Demo (balance validation)
5. Add User Story 4 → Test independently → Deploy/Demo (swap execution)
6. Add User Story 5 → Test independently → Deploy/Demo (multi-chain complete)
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 2 (quoting) - can start in parallel with US1
   - Developer B: User Story 1 (discovery) - blocks others slightly but independent
3. After US1 and US2 complete:
   - Developer A: User Story 4 (swaps) - depends on US3
   - Developer B: User Story 3 (balances) - prerequisite for US4
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **MANDATORY**: Verify tests fail before implementing (TDD Red-Green-Refactor)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **CONSTITUTION COMPLIANCE**: All code must pass linting, maintain type safety (use `unknown` not `any`), include proper logging via LoggerService
- **OPT-OUT MODEL**: Aggregators enabled globally via `aggregator-mulchain`, excluded via `chains.{chainId}.non-aggr`
- **PER-CHAIN PATTERN**: OKX adapter instantiated once per chain, not as global singleton
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
