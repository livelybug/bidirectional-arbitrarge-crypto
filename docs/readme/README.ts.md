## Bidirectional Cross-Chain Arbitrage (TypeScript / Nest.js)

This directory (`code/ts`) contains the TypeScript / Nest.js service that drives
the bidirectional cross-chain arbitrage engine. It boots a 1s orchestrator
loop, reads configuration from `config.yaml` + environment variables, and
evaluates forward/backward opportunities in **dry-run mode** (no on-chain
transactions are sent).

Live execution will be added in later phases; for now the system is a
deterministic, config-driven simulator with strict, fail-fast config
validation.

---

## Project Structure (high level)

- `src/app.module.ts` – Root Nest module wiring feature modules.
- `src/orchestrator` – Main loop (`OrchestratorService`) and wiring to
  price monitor, risk manager, DEX/bridge adapters.
- `src/price_monitor` – Price monitor abstraction and stub implementation.
- `src/dex` – DEX adapter interfaces + stubs (Uniswap V3, Velodrome V2, etc.).
- `src/bridge` – Bridge adapter interface + Stargate stub.
- `src/risk_control` – Risk configuration and `RiskManagerService`.
- `src/utils/config` – Typed config loader (`config.yaml` + `.env`), schema
  validation, and env merge helper.
- `src/utils/logger` – JSON `LoggerService` with opId (correlation id)
  support.
- `src/utils/wallet` – Wallet / signer abstraction (no secrets committed).
- `config.yaml` – Main runtime configuration (tokens, chains, risk, fees,
  ops, logging, wallets).
- `.env.example` – Template for environment variables (RPC endpoints,
  secrets, overrides).

For more details on architecture and configuration, see:

- `docs/arch/arch_general.md`
- `docs/FRD/FRD.md`

---

## Prerequisites

- Node.js (see `engines.node` in `package.json`).
- `pnpm` installed globally.
- Git checkout of this repository.

From the repo root:

```bash
cd code/ts
pnpm install
```

---

## Configuration

### 1. `config.yaml`

The file `code/ts/config.yaml` is the primary runtime configuration and is
validated on startup (and in tests) using a Zod schema. The top-level
structure, in simplified form, is:

- `tokens` – Symbols used to build trading pairs:
  - `base`: e.g. `WIF`, `PEPE`.
  - `quote`: usually stablecoins like `USDT`.
- `chains` – Per-chain settings keyed by chain id (`arbitrum`, `base`,
  `optimism`, `ethereum`, `bsc`, `polygon`):
  - `rpc`: JSON-RPC endpoint URL (non-empty string).
  - `tokenList`: list of `{ symbol, address }` for tokens used on that chain.
  - `dexList`: list of `{ key, type }` DEX descriptors (e.g. `uniswap_v3`,
    `velodrome_v2`).
- `bridge` – Bridge provider configuration (currently `stargate` only).
- `risk` – Arbitrage risk settings (min profit, stop loss, position caps).
- `fees` – Fees and reserves (DEX fees, bridge fees, gas, slippage reserve).
- `ops` – Operational parameters:
  - `loopIntervalMs`: orchestrator tick interval in milliseconds.
  - `bridgeBackPct`: fraction of profits to bridge back.
  - `gasReservePctOfProfit`: fraction of profits reserved for gas.
  - `dryRun`: `true` for simulation-only; see below.
- `logging` – Log level and JSON flag.
- `wallets` – Wallet metadata:
  - `keystorePath`: path under `./wallets/`.
  - `address`: public address (no private key in YAML).

The application **fails fast** if this configuration is incomplete or
inconsistent. For example, startup will error if:

- `tokens.base` or `tokens.quote` is empty.
- Fewer than two chains are configured.
- The first two chains lack at least one `dexList` entry.
- No chain advertises a DEX key required by an adapter (e.g. `uniswap_v3`,
  `velodrome_v2`).

The test suite also validates the checked-in `config.yaml` against these
guardrails.

### 2. Environment variables (`.env`)

Sensitive and environment-specific values live in `.env` (which is
gitignored). Use `.env.example` as a template:

```bash
cd code/ts
cp .env.example .env
edit .env
```

`config.yaml` remains the source of truth for structure; selected fields can
be overridden via environment variables, for example (see
`.env.example` for the full list):

- RPC endpoints: `ARBITRUM_RPC`, `BASE_RPC`, `OPTIMISM_RPC`, `ETHEREUM_RPC`,
  `POLYGON_RPC`, `BSC_RPC`.
- Risk and ops overrides: `MIN_PROFIT_RATE_BPS`, `STOP_LOSS_PCT`,
  `SLIPPAGE_BPS`, `LOOP_INTERVAL_MS`, `BRIDGE_BACK_PCT`,
  `GAS_RESERVE_PCT_OF_PROFIT`, `SINGLE_TX_CAP_PCT`, `MAX_EXPOSURE_PCT`.
- Logging: `LOG_LEVEL`, `LOG_JSON`.
- Secrets: `PRIVATE_KEY`, `WALLET_PRIVATE_KEY`, `STARGATE_API_KEY`,
  `LZ_API_KEY` (do not commit real values).

On bootstrap, the `ConfigService` loads `config.yaml`, applies supported
overrides from `process.env`, and validates everything with Zod. Invalid or
out-of-range values cause startup to fail with a clear error.

---

## Dry-Run vs Live Mode

The orchestrator loop is designed to support both simulation and real
execution. In the current phase, **only dry-run behavior is implemented**:

- `ops.dryRun: true` (default in `config.yaml`)
  - The orchestrator computes forward/backward opportunities using the price
    monitor and risk manager.
  - Decisions and plans are logged via `LoggerService`.
  - DEX and bridge adapters are stubbed; no on-chain transactions are sent.

- `ops.dryRun: false`
  - This flag is reserved for future live-mode work. Even if set to `false`
    today, the code still uses stubbed adapters and will not broadcast real
    transactions.
  - When live-mode is implemented, this flag will be the primary safety
    switch between simulation and execution.

Always keep `dryRun` enabled when experimenting with new configuration or
deploying to unfamiliar environments.

---

## Common Commands

Run all commands from `code/ts`.

### Install dependencies

```bash
pnpm install
```

### Lint, build, and test

```bash
# Lint TypeScript sources
pnpm lint

# Type-check and compile
pnpm build

# Unit tests
pnpm test

# E2E tests (Nest default harness)
pnpm test:e2e

# Coverage report
pnpm test:cov
```

### Run the orchestrator

```bash
# One-off start (honors config.yaml and .env)
pnpm start

# Watch mode (reload on code changes)
pnpm start:dev

# Production-style run from compiled output
pnpm build
pnpm start:prod
```

On successful startup, you should see JSON logs on stdout every second from
the orchestrator loop, including correlation ids (`opId`) and decision
metadata.

Logs can be redirected to files under `logs/` (which is gitignored) using
your process manager or shell redirection.

---

## CI and Quality Gates

This project ships with a GitHub Actions workflow in
`.github/workflows/ci.yml` that runs on `push` and `pull_request` events
targeting the `main` branch. The pipeline runs the same commands described
above:

- `pnpm lint`
- `pnpm build`
- `pnpm test -- --runInBand`

Locally, you can approximate the CI gates with:

```bash
pnpm lint && pnpm build && pnpm test
```

---

## Further Reading

- Architecture and config schema: `docs/arch/arch_general.md`.
- Functional requirements: `docs/FRD/FRD.md`.
- Bootstrapping tasks and milestones:
  `docs/task/task-detail/T3- Project_bootstrapping.md`.

These documents describe the longer-term plan for adapters, live-mode
execution, and additional operational features beyond the current dry-run
engine.
