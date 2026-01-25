# CLAUDE.md

## Core Principle

**All code and documents must be very concise!!!**

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer Docs
* The developer document is in folder `docs/`.
  * The architecture doc is `docs/arch/arch_general.md`.
  * The readme is `docs/readme/README.ts.md`.

## Project Root

The TypeScript codebase is located in `code/ts`. All commands below should be run from that directory.

## Common Development Commands

### Build & Run
```bash
# Build the project
pnpm run build

# Development mode (with watch)
pnpm run start:dev

# Production mode
pnpm run start:prod
```

### Testing
```bash
# Run all tests (builds first)
pnpm run test

# Watch mode
pnpm run test:watch

# Coverage report
pnpm run test:cov

# E2E tests only
pnpm run test:e2e

# Run a single test file (specify full path)
pnpm run test src/path/to/service.spec.ts
```

### Linting & Formatting
```bash
# Lint and auto-fix
pnpm run lint

# Lint test files
pnpm run lint:test

# Format code
pnpm run format
```

### Utilities
```bash
# Print current configuration
pnpm run config:print

# Check wallet balance (dev helper)
pnpm run wallet:dev-balance
```

## Architecture Overview

This is a **cross-chain arbitrage trading bot** built with NestJS that identifies and executes profitable trades across multiple DEXs and blockchain bridges.

### Core Components

**Modules Structure:**
- `orchestrator/` - Main trading loop coordinator that drives the arbitrage cycle
- `price_monitor/` - Fetches and aggregates prices from multiple DEXs
- `risk_control/` - Risk management and execution plan approval
- `dex/` - DEX adapters for Uniswap V3, PancakeSwap V3, Velodrome V2
- `bridge/` - Bridge adapters (currently Stargate)
- `utils/` - Shared utilities (config, wallet, logger)

**Trading Flow:**
1. **Orchestrator** runs a continuous loop (interval configurable via `ops.loopIntervalMs`)
2. For each discovered **TradingPairConfig**:
   - Requests current prices from **PriceMonitor**
   - Computes net profit (forward/backward) minus fees
   - Submits to **RiskManager** for approval
   - If approved, generates an **ExecutionPlan**
   - In dry-run mode: logs what would happen
   - In live mode: would execute swaps and bridges (not yet implemented)

### Adapter Pattern

**DEX Adapter** (`src/dex/dex-adapter.interface.ts`):
- Standardized interface for swapping tokens across different DEXs
- Methods: `estimateBuyQuoteToBase`, `estimateSellBaseToQuote`, `swapQuoteToBase`, `swapBaseToQuote`, `getBalanceQuote`, `getBalanceBase`
- Implementations: UniswapV3Service, PancakeswapV3Service, VelodromeV2Service

**Bridge Adapter** (`src/bridge/bridge-adapter.interface.ts`):
- Standardized interface for cross-chain token transfers
- Methods: `estimateBridgeToken`, `bridgeToken`, `waitForSettlement`
- Implementation: StargateService

**Wallet Adapter** (`src/utils/wallet/wallet.interface.ts`):
- Abstraction over ethers.js for key management and transaction signing
- Supports dry-run mode (simulates without signing/broadcasting)

### Configuration System

**Multi-layer config loading** (`src/utils/config/`):
1. Base YAML file: `config.yaml` (or via `APP_CONFIG_PATH` env var)
2. Environment overlay: `config.{ENV}.yaml` (selected via `NODE_ENV`)
3. Environment variable merging: `env-merge.ts` allows overriding with `MY__KEY__SUBKEY=value`

Config is validated with Zod schemas and frozen on load. Key sections:
- `ops` - Operational settings (dryRun, loopIntervalMs)
- `chains` - Chain-specific RPC URLs and gas settings
- `tokens` - Token addresses per chain
- `wallets` - Private key references (paths, not direct keys)
- `fees` - Fee model (dexFeeBps, bridgeFeeUsd, etc.)
- `risk` - Risk thresholds (minProfitRateBps, positionCaps)

**Wallet Key Management:**
- Keys are stored in `wallets/` directory (gitignored)
- Config references key files by name, not content
- Supports dry-run mode where keys are loaded but transactions aren't signed

### Pair Discovery

**PairDiscoveryService** (`src/orchestrator/pair-discovery/`):
- Runs at startup to discover all valid trading routes
- Generates `TradingPairConfig` objects combining:
  - Token pairs (base/quote)
  - Chain pairs (M/N)
  - DEX pairs (J/K)
- Pair ID format: `${baseToken}~${quoteToken}~${dexJ}+${chainM}~${dexK}+${chainN}`

### Dependency Injection Tokens

Custom DI tokens are defined in `src/common/tokens.ts`:
- `DEX_UNISWAP_V3`, `DEX_PANCAKESWAP_V3`, `DEX_VELODROME_V2`
- `BRIDGE_STARGATE`
- `PRICE_MONITOR`
- `RISK_MANAGER`

## Coding Conventions

- Use `unknown` instead of `any`
- Avoid `async` keyword on functions without `await` expressions
- All services use NestJS `@Injectable()` decorator
- Modules export via provider tokens, not direct service classes
- Immutable data objects (e.g., `TradingPairConfig`, `Prices`) should not be mutated
- Logging uses the custom `LoggerService` with operation-scoped contexts

## Testing

- Unit tests: `**/*.spec.ts` (co-located with source)
- Integration tests: `test/**/*.integration.spec.ts`
- E2E tests: `test/**/*.e2e-spec.ts`

## Environment

- Node.js >= 24 required
- Uses `pnpm` as package manager
- TypeScript with strict mode enabled (but some strictness options relaxed)
- Uses ethers.js v6 for blockchain interactions

## Active Technologies
- TypeScript 5.x (Node.js v24+) (001-okx-dex-integration)
- N/A (stateless trading bot, in-memory pair discovery) (001-okx-dex-integration)

## Recent Changes
- 001-okx-dex-integration: Added TypeScript 5.x (Node.js v24+)
