# Bidirectional Arbitrage Trading Bot Constitution

## Core Principles

### I. Code Quality & Type Safety

- **Type Safety**: Use `unknown` instead of `any`.
- **Immutability**: Use Readonly types where appropriate.
- **Async Discipline**: Avoid `async` keyword on functions without `await` expressions.
- **Logging**: All logging MUST use the custom `LoggerService` with operation-scoped contexts. 

### II. Testing Excellence (NON-NEGOTIABLE)

- **Test-Driven Development (TDD)**: Tests MUST be written BEFORE implementation code:
  1. Write test and verify it FAILS (Red)
  2. Write minimal implementation to make test pass (Green)
  3. Refactor while keeping tests green (Refactor)
- **Test Organization**:
  - Unit tests: `**/*.spec.ts` (co-located with source files)
  - Integration tests: `test/**/*.integration.spec.ts`
  - E2E tests: `test/**/*.e2e-spec.ts`
- **Blockchain Integration Tests**: Tests that interact with live blockchain RPCs MUST be marked as slow tests in `test/slow/`.

### III. User Experience & Observability

- **Dry-Run Mode**: ALL features MUST work correctly in dry-run mode before live execution. Dry-run simulates operations without signing/broadcasting transactions.
- **Structured Logging**: All operations MUST emit structured logs with:
  - Operation context (e.g., "arbitrage-cycle", "price-fetch", "risk-check")
  - Trading pair identifiers
  - Key metrics (prices, fees, estimated profit, gas costs)
- **Error Messages**: Errors MUST provide actionable information:
  - What operation failed
  - What data was involved

### IV. Performance & Reliability Standards

- **Memory Management**: Avoid memory leaks in long-running processes. Immutable data helps, circular references must be cautious.
- **RPC Reliability**: All blockchain RPC calls MUST handle:
  - Timeouts and retries with exponential backoff
  - Rate limiting (HTTP 429) responses
  - Network failures
  - Malformed responses (validate all RPC results)
- **Gas Estimation**: All transaction estimations MUST be accurate.

### V. Security & Financial Safety

- **Key Management**: Private keys MUST NEVER be hardcoded or committed to git. Keys are stored in `wallets/` directory (gitignored). Config references key files by name, not content.
- **Transaction Safety**: Before ANY live transaction:
  - Verify all parameters
  - Double-check chain IDs (prevent mainnet vs testnet confusion)
  - Validate gas estimates are reasonable
- **Input Validation**: ALL external inputs (API responses, RPC results, user configs) MUST be validated before use.
- **Error Recovery**: The system MUST handle partial failures gracefully:
  - If a DEX fetch fails, log and continue with other DEXs
  - If a bridge fails, don't attempt the reverse trade
  - If wallet balance is insufficient, skip that trading pair

## Architecture Constraints
* The ts codebase is in folder `code/ts/`.

### Configuration System

Configuration MUST follow the multi-layer loading system:

1. Base YAML file: `config.yaml` (or via `APP_CONFIG_PATH` env var)
2. Environment overlay: `config.{ENV}.yaml` (selected via `APP_ENV`)
3. Environment variable merging: `MY__KEY__SUBKEY=value` format

## Development Workflow

### Code Review Requirements

All pull requests MUST:

- Pass all tests (unit, integration, and slow integration tests if applicable)
- Pass linting (`pnpm run lint`) with no errors

### Testing Gates

Code MUST NOT merge to main unless:

- All tests pass
- Dry-run mode works for the feature
- Manual testing has been performed for financial operations

### Deployment Safety

Before deploying to production:

- MUST successfully run in dry-run mode for at least one full trading cycle

## Governance

### Amendment Procedure

This constitution supersedes all other development practices. Amendments require:

1. Migration plan for existing code that violates the new principle
2. Update to this document with version bump

### Compliance Review

For runtime development guidance, refer to `CLAUDE.md` in the project root.

**Version**: 1.0.0 | **Ratified**: 2025-12-29 | **Last Amended**: 2025-12-29
