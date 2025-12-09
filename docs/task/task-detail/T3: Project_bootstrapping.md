# T3: Project Bootstrapping Plan (Nest.js + TypeScript)

1. Objectives
   - Create a Nest.js TypeScript repo scaffold.
   - Establish module layout matching architecture: orchestrator, price_monitor, dex, bridge, risk_control, utils.
   - Integrate config, logging, env, linting, testing, and CI.
   - Ensure build/test run green.

2. Repo Initialization
   - Use Nest CLI:
     - `pnpm dlx @nestjs/cli new cross-chain-arb --packageManager pnpm`
     - Move/align under repo root and update paths to match docs layout.
   - Set Node version (e.g., .nvmrc: 20.x), engines in package.json.

3. Package Management & Scripts
   - Package manager: pnpm.
   - Add scripts:
     - `build`: nest build
     - `start:dev`: nest start --watch
     - `lint`: eslint .
     - `format`: prettier --write .
     - `test`: jest
     - `test:cov`: jest --coverage
     - `simulate`: node dist/src/simulate.js (placeholder for dry-run)
     - `start`: nest start

4. Monorepo Structure (folders)
   - Create folders (no code yet):
     - `/src/orchestrator` (main loop service)
     - `/src/price_monitor`
     - `/src/dex` (uniswap_v3, velodrome adapters)
     - `/src/bridge` (stargate adapter)
     - `/src/risk_control`
     - `/src/utils` (wallet, logger, config loader)
   - Config and assets:
     - `/config.yaml` (runtime config per arch)
     - `/logs/` (runtime logs, gitignored)
     - `/wallets/` (keystore, gitignored)

5. Nest Modules & Services (scaffold)
   - AppModule wires feature modules.
   - Feature modules:
     - OrchestratorModule: OrchestratorService (1s loop, DI of adapters).
     - PriceMonitorModule: PriceMonitorService.
     - DexModule: UniswapV3Service, VelodromeService.
     - BridgeModule: StargateService.
     - RiskModule: RiskManagerService.
     - UtilsModule: WalletService, LoggerService, ConfigService.
   - Provide interfaces via tokens for DI (e.g., `PRICE_MONITOR`, `DEX_UNISWAP_V3`, `BRIDGE_STARGATE`).

6. Config & Env
   - Use dotenv + YAML loader:
     - `.env` for RPCs, API keys, sensitive secrets.
     - Load `config.yaml` via ConfigService, validate schema (thresholds, fees, caps).
   - Add typed config interfaces per arch_general.md.

7. Logging
   - LoggerService:
     - JSON structured logs.
     - Correlation IDs (opId) injection.
     - Levels: info/warn/error/debug.
   - Hook Nest logger to custom transport.

8. Linting & Formatting
   - ESLint + Prettier setup:
     - `.eslintrc.cjs`, `.prettierrc`, `.editorconfig`.
   - Rules: no-floating-promises, prefer-const, explicit-module-boundary-types.

9. Testing Baseline
   - Jest configured by Nest.
   - Add placeholder unit tests for:
     - PriceMonitorService: fetch mock prices.
     - RiskManagerService: threshold gating and fee subtraction.
     - OrchestratorService: loop cadence (mock timers).

10. CI Setup
   - GitHub Actions workflow:
     - Jobs: install (pnpm), lint, build, test.
     - Cache pnpm store.
     - Node 20.x matrix (single version ok).
   - Status badges optional.

11. Security & Secrets
   - `.gitignore`:
     - `/logs/`, `/wallets/`, `.env`, compiled artifacts.
   - Sample `.env.example` (no secrets).
   - Secret loading only via env/keystore; no hardcoded keys.

12. Health & Run Modes
   - Add a simple health controller: `GET /status` returns loop state (heartbeat, paused flag).
   - Add dry-run mode flag in config to prevent on-chain tx during development.

13. Initial Orchestrator Wiring (stub)
   - OrchestratorService:
     - OnModuleInit: start 1s interval from config (ops.loopIntervalMs).
     - Concurrent price fetch; compute forward/backward net profit (subtract totalFeeRateBps).
     - Call RiskManagerService.shouldExecute(); log decision.
     - If ok & dry-run: skip execution; if live: call adapters (stubbed).
   - All external calls mocked initially.

14. Deliverables (this phase)
   - Code scaffold with modules/services wired.
   - Config loader, logger baseline, env management.
   - CI pipeline passing.
   - Basic tests green.

15. Success Criteria
   - `pnpm lint && pnpm build && pnpm test` all pass.
   - App starts (`pnpm start:dev`) and logs heartbeat every 1s.
   - Health endpoint responds with loop status.
   - No secrets in repo; config validated on boot.

16. Task Checklist
   - [ ] Initialize Nest project with pnpm.
   - [ ] Create folders/modules per architecture.
   - [ ] Implement ConfigService (YAML + env) with schema validation.
   - [ ] Implement LoggerService with JSON logs and opId support.
   - [ ] Wire OrchestratorService loop (stub execution).
   - [ ] Add Jest tests (baseline).
   - [ ] Setup ESLint/Prettier.
   - [ ] Add GitHub Actions CI (lint, build, test).
   - [ ] Add `.env.example`, `.gitignore`.
   - [ ] Add `/status` health endpoint.
   - [ ] Document run commands in README (optional).

17. Notes
   - Future adapters (DEX/bridge) will replace stubs in development phase T4–T6.
   - Keep module boundaries clean for easy mocking in tests.

## Detail Tasks

- [P0] T3-01: Validate local toolchain
  - Steps: Ensure Node 20.x (nvm), pnpm installed; `pnpm self-update`, `pnpm -v`, `node -v`.
  - Deps: —
  - Done when: Node 20.x and pnpm available.

- [P0] T3-02: Initialize Nest project (pnpm)
  - Steps:
    - Preferred If using global CLI:
      `nest new cross-chain-arb --package-manager pnpm`
    - Alternative (short flag):
      `pnpm dlx @nestjs/cli@11.0.14 new cross-chain-arb --package-manager pnpm`
    - (pin CLI + correct flag):
      `pnpm dlx @nestjs/cli@11.0.14 new cross-chain-arb -p pnpm`
    - Quick check (optional):
      `pnpm dlx @nestjs/cli@latest --version` to ensure a recent CLI before running.
  - Deps: T3-01
  - Done when: Base Nest app builds and runs.

- [P0] T3-03: Align repo structure and folders
  - Steps: Create folders `/src/orchestrator`, `/src/price_monitor`, `/src/dex`, `/src/bridge`, `/src/risk_control`, `/src/utils`; add `/logs/`, `/wallets/` (gitignored).
  - Deps: T3-02
  - Done when: Folders exist and compile unaffected.

- [P0] T3-04: Set Node version and engines
  - Steps: Add `.nvmrc` (20.x), set `engines` in package.json.
  - Deps: T3-02
  - Done when: `nvm use` selects 20.x; package.json updated.

- [P0] T3-05: Git hygiene and secrets
  - Steps: Update `.gitignore` to include `/logs/`, `/wallets/`, `.env`, `dist/`; add `.env.example`.
  - Deps: T3-02
  - Done when: Sensitive paths ignored; sample env present.

- [P0] T3-06: Package scripts
  - Steps: Add scripts for `build`, `start`, `start:dev`, `lint`, `format`, `test`, `test:cov`, `simulate`.
  - Deps: T3-02
  - Done when: `nest build` and `nest start --watch` work.

- [P0] T3-07: Config loader (YAML + env)
  - Steps: Implement `ConfigService` to load `.env` and `config.yaml`; validate with schema (thresholds, fees, risk, ops.loopIntervalMs).
  - Deps: T3-03
  - Done when: App boots only with valid config; errors on invalid.

- [P0] T3-08: LoggerService (JSON)
  - Steps: Implement structured JSON logger; levels; opId support; wire as Nest logger.
  - Deps: T3-03
  - Done when: Logs emitted in JSON with opId when provided.

- [P0] T3-09: Define DI tokens and interfaces
  - Steps: Create interface tokens (`PRICE_MONITOR`, `DEX_UNISWAP_V3`, `BRIDGE_STARGATE`, etc.); export TS interfaces per arch.
  - Deps: T3-03
  - Done when: Tokens/interfaces available for injection.

- [P0] T3-10: Scaffold feature modules
  - Steps: Create Nest modules/services:
    - OrchestratorModule/Service
    - PriceMonitorModule/Service
    - DexModule (UniswapV3Service, VelodromeService)
    - BridgeModule (StargateService)
    - RiskModule (RiskManagerService)
    - UtilsModule (WalletService, LoggerService, ConfigService provider)
  - Deps: T3-03, T3-09
  - Done when: AppModule imports/exports compile.

- [P0] T3-11: Orchestrator loop (stub)
  - Steps: OnModuleInit start interval (ops.loopIntervalMs); fetch mock prices; compute net forward/backward profits (subtract totalFeeRateBps); call RiskManager.shouldExecute(); log decision; honor dry-run flag.
  - Deps: T3-07, T3-08, T3-10
  - Done when: Heartbeat and decision logs every 1s.

- [P1] T3-12: Health endpoint
  - Steps: Add `/status` controller returning heartbeat timestamp, paused flag.
  - Deps: T3-10, T3-11
  - Done when: `GET /status` responds with JSON.

- [P1] T3-13: WalletService scaffold
  - Steps: Create signer/provider per chain from env/config; no key material in code; placeholder methods.
  - Deps: T3-07, T3-10
  - Done when: Service provides providers/signers without errors.

- [P1] T3-14: ESLint + Prettier setup
  - Steps: Configure `.eslintrc.cjs`, `.prettierrc`, `.editorconfig`; add recommended rules.
  - Deps: T3-02
  - Done when: `pnpm lint` passes; `pnpm format` formats.

- [P1] T3-15: Jest baseline tests
  - Steps: Add unit tests:
    - ConfigService schema validation.
    - RiskManager.shouldExecute gating with fee subtraction.
    - Orchestrator loop cadence (fake timers).
  - Deps: T3-07, T3-10, T3-11
  - Done when: `pnpm test` green; coverage reported.

- [P1] T3-16: CI (GitHub Actions)
  - Steps: Add workflow to install (pnpm), cache, lint, build, test on Node 20.x.
  - Deps: T3-06, T3-14, T3-15
  - Done when: CI runs green on push/PR.

- [P1] T3-17: Config artifacts
  - Steps: Add `config.yaml` template with chains, fees, risk, ops; document env vars.
  - Deps: T3-07
  - Done when: Template loads in dev.

- [P2] T3-18: Dry-run mode flag
  - Steps: Add config flag to bypass on-chain tx; ensure orchestrator checks it.
  - Deps: T3-07, T3-11
  - Done when: Dry-run active prevents adapter calls.

- [P2] T3-19: Rate-limit and retry helpers
  - Steps: Add simple retry/backoff util; token bucket placeholder for APIs.
  - Deps: T3-10
  - Done when: Utils available; no change in behavior yet.

- [P2] T3-20: Logging enrichment
  - Steps: Correlate opId across one loop; include prices, profits, plan, reasons.
  - Deps: T3-08, T3-11
  - Done when: Logs include correlation fields.

- [P2] T3-21: Docs (README)
  - Steps: Document setup, run commands, config, dry-run vs live.
  - Deps: T3-06, T3-07, T3-11
  - Done when: README present and accurate.

- [P2] T3-22: Pre-commit hooks (optional)
  - Steps: Add lint-staged + simple pre-commit (lint/format).
  - Deps: T3-14
  - Done when: Hooks run locally.

- [P3] T3-23: Containerization (optional)
  - Steps: Add Dockerfile and compose for local run with env/config mounts.
  - Deps: T3-06, T3-07, T3-11
  - Done when: `docker build` and run succeed.

- [P3] T3-24: Status metrics (optional)
  - Steps: Expose lightweight metrics in logs (counts, latencies).
  - Deps: T3-11, T3-20
  - Done when: Metrics appear in logs.

- [P3] T3-25: Sample mocks and fixtures
  - Steps: Provide mock price feeds and balances for dev/testing.
  - Deps: T3-15
  - Done when: Tests reuse fixtures.

Milestone grouping:
- M1 (Scaffold ready): T3-01–T3-06, T3-14
- M2 (Bootable services): T3-07–T3-13
- M3 (Quality gates): T3-15–T3-17
- M4 (Ops niceties): T3-18–T3-25

## Detail Sub Tasks
### [P0] T3-07: Config loader (YAML + env)
#### Implemetation Plan
Implementation plan for a typed, validated config loader using `.env` and `config.yaml`, aligned with `arch_general.md`.

1. Goals
  - Centralize runtime configuration (chains, fees, risk, ops, logging, wallets) in `config.yaml` plus sensitive values in `.env`.
  - Provide a typed `ConfigService` (Nest provider) that other modules use instead of reading env/files directly.
  - Validate configuration on startup; fail fast with clear errors if invalid or missing.

2. Files & Locations
  - `config.yaml` at project root (already planned in repo structure).
  - `.env` at project root (ignored by git, `.env.example` committed).
  - `src/utils/config` (or `src/utils/config-loader`):
    - `config.types.ts` – TypeScript interfaces mirroring the schema from `arch_general.md` (chains, bridge, risk, fees, ops, logging, wallets).
    - `config.schema.ts` – Validation schema (e.g., using `zod` or `joi`) for both env and YAML content.
    - `config.service.ts` – Nest injectable `ConfigService` that loads, merges, validates, and exposes typed getters.

3. Dependencies
  - Add libraries (implementation choice, one of):
    - YAML parsing: `yaml`.
    - Validation: `zod` (preferred) or `joi`.
    - Env loading: `dotenv` (or use Nest ConfigModule later, but start simple).
  - Update `package.json` devDependencies if needed.

4. Config Schema Design (from `arch_general.md`)
  - Mirror the indicative schema:
    - `chains[chainId].rpc`, `usdt`, `tokenA`, `dex`.
    - `bridge.provider`, `bridge.stargate.router`, `bridge.stargate.lzEndpoint`.
    - `risk.minProfitRateBps`, `risk.stopLossPct`, `risk.slippageBps`, `risk.positionCaps.fullAmountMode`, `singleTxCapPct`, `maxExposurePct`.
    - `fees.dexFeeBpsPerSwap`, `fees.bridgeFlatUSD`, `fees.gasUSD`, `fees.slippageReserveBps`, `fees.totalFeeRateBps`.
    - `ops.loopIntervalMs`, `ops.bridgeBackPct`, `ops.gasReservePctOfProfit`.
    - `logging.level`, `logging.json`.
    - `wallets.keystorePath`, `wallets.address` (private key only via env/keystore, not YAML).
  - Env-only values (from `.env`): RPC endpoints (if not in YAML), private key, API keys, optional overrides (e.g., `MIN_PROFIT_RATE_BPS`, `LOOP_INTERVAL_MS`).

5. Load & Merge Strategy
  - Load order at startup (inside `ConfigService`):
    1. Call `dotenv.config()` to populate `process.env` from `.env`.
    2. Read `config.yaml` synchronously on bootstrap (using `fs` + `yaml.parse`).
    3. Construct a raw config object from YAML.
    4. Overlay env-driven overrides:
      - Example: if `process.env.MIN_PROFIT_RATE_BPS` is set, override `risk.minProfitRateBps`.
      - Example: if `process.env.ARBITRUM_RPC` is set, override `chains.arbitrum.rpc`.
  - Pass the merged config through the validation schema.
  - On validation error: throw an error, causing Nest bootstrap to fail with a clear message.

6. Validation Rules (examples)
  - `loopIntervalMs` > 0 and <= e.g. 60000.
  - `bridgeBackPct` in [0.9, 0.95].
  - `gasReservePctOfProfit` in [0, 0.1].
  - `minProfitRateBps` >= 150.
  - `totalFeeRateBps` between 120 and 180.
  - `singleTxCapPct` and `maxExposurePct` within (0, 1].
  - For each configured chain: `rpc` non-empty string; `usdt` and `tokenA` look like hex addresses.
  - `wallets.keystorePath` present; `wallets.address` looks like an address.

7. ConfigService API
  - Provide typed getters used by the rest of the app, e.g.:
    - `getChainsConfig(): ChainsConfig` – returns map of chain configs.
    - `getRiskConfig(): RiskConfig`.
    - `getFeesConfig(): FeesConfig`.
    - `getOpsConfig(): OpsConfig`.
    - `getLoggingConfig(): LoggingConfig`.
    - `getWalletsConfig(): WalletsConfig`.
  - Optionally helper methods:
    - `getChainRpc(chainId: ChainId): string`.
    - `getDexForChain(chainId: ChainId): DexConfig`.
  - Ensure these return deeply immutable objects (e.g. via `Object.freeze`) to avoid runtime mutation.

8. Nest Integration
  - Register `ConfigService` as a provider in `UtilsModule` and export it.
  - Import `UtilsModule` into other modules needing config (Orchestrator, PriceMonitor, Dex, Bridge, Risk).
  - Ensure `ConfigService` is constructed only once (singleton).

9. `.env` and `.env.example`
  - Define expected keys in `.env.example`, e.g.:
    - `ARBITRUM_RPC=`, `BASE_RPC=`, `PRIVATE_KEY=`, `STARGATE_API_KEY=` (if applicable).
    - Optional overrides: `MIN_PROFIT_RATE_BPS=`, `LOOP_INTERVAL_MS=`.
  - Ensure `.env` is gitignored, while `.env.example` is committed.

10. Error Handling & Logging
  - On missing/invalid config values, log a clear message (using a minimal logger or console at bootstrap) before throwing.
  - Include which field failed validation and the offending value.
  - Avoid logging any secret values (e.g., private keys, API keys).

11. Tests (linked to T3-15 but scoped here)
  - Unit tests for `ConfigService` and schema:
    - Valid `config.yaml` + `.env` passes and produces expected typed output.
    - Missing mandatory fields cause validation errors.
    - Env overrides YAML for selected fields.
    - Invalid ranges (e.g., `bridgeBackPct` outside [0.9, 0.95]) fail validation.

12. Definition of Done (for T3-07)
  - `ConfigService` implemented with typed schema and validation.
  - `config.yaml` template and `.env.example` exist and load correctly in dev.
  - App fails fast with clear error on invalid/missing config.
  - Orchestrator/Risk/Wallet modules can inject `ConfigService` and read typed values.

#### Sub Tasks
1. Analyse requirements
  - Review `arch_general.md` section **4. Config Schema (config.yaml, indicative)** and `FRD.md`, then confirm all fields that must be supported.
  - List required config domains: `chains`, `bridge`, `risk`, `fees`, `ops`, `logging`, `wallets`, plus env-only secrets/overrides, and write to `config.yaml` and `.env` respectively.

2. Create config directory structure
  - Create folder `src/utils/config` (or the agreed path).
  - Ensure it is included in TS compilation (no path mapping issues).

3. Define TypeScript config types
  - In `config.types.ts`, define interfaces for:
    - `ChainId`, `ChainConfig`, `ChainsConfig`.
    - `BridgeConfig`, `RiskConfig`, `PositionCapsConfig`, `FeesConfig`, `OpsConfig`, `LoggingConfig`, `WalletsConfig`.
  - Export a root `AppConfig` interface containing all sections.

4. Choose and install libraries
  - Add dependencies:
    - `yaml` for parsing `config.yaml`.
    - `zod` (or chosen validator) for schema validation.
    - `dotenv` for `.env` loading (if not already present).
  - Update `package.json` and lockfile via `pnpm`.

5. Implement validation schema
  - In `config.schema.ts`, use the chosen validator to define:
    - Schema for each section (`chains`, `bridge`, `risk`, `fees`, `ops`, `logging`, `wallets`).
    - Cross-field constraints (e.g., `bridgeBackPct` in [0.9, 0.95], `totalFeeRateBps` between 120 and 180).
  - Export a `parseConfig(raw: unknown): AppConfig` helper.

6. Implement env loader
  - Call `dotenv.config()` at process start inside `ConfigService` (or a small bootstrap helper).
  - Decide which env vars override YAML (e.g., `ARBITRUM_RPC`, `BASE_RPC`, `MIN_PROFIT_RATE_BPS`, `LOOP_INTERVAL_MS`).
  - Document the mapping from env vars to config fields.

7. Implement YAML loader
  - In `config.service.ts`, read `config.yaml` from project root using `fs` + `yaml.parse`.
  - Handle file-not-found and parse errors with clear messages.

8. Merge YAML and env
  - Build a merged raw config object:
    - Start from YAML values.
    - Overlay env-derived overrides for selected fields.
  - Ensure env overrides do not introduce invalid types (convert strings to numbers/booleans as needed).

9. Validate merged config
  - Pass the merged config to `parseConfig`.
  - On validation error:
    - Log a concise error (without secrets).
    - Throw an exception to make Nest bootstrap fail fast.

10. Implement `ConfigService` API
   - Create a Nest `@Injectable()` class exposing:
    - `getConfig(): AppConfig`.
    - Convenience getters: `getChainsConfig()`, `getRiskConfig()`, `getFeesConfig()`, `getOpsConfig()`, `getLoggingConfig()`, `getWalletsConfig()`.
   - Freeze internal config object to avoid mutation at runtime.

11. Wire `ConfigService` into `UtilsModule`
   - Register `ConfigService` as a provider in `UtilsModule`.
   - Export `ConfigService` so other modules can inject it.
   - Verify DI works by injecting it into one simple service (e.g., OrchestratorService stub) and reading a field.

12. Prepare `config.yaml` template
   - Create a minimal but valid `config.yaml` example that satisfies the schema (dummy RPC URLs, token addresses, thresholds, etc.).
   - Ensure this template lets the app start in dev mode without secrets.

13. Prepare `.env.example`
   - Add all expected env keys (RPCs, private key, API keys, overrides) with empty or dummy values.
   - Confirm `.env` itself is ignored by git.

14. Add basic tests for `ConfigService`
   - Write unit tests to cover:
    - Successful load of valid `config.yaml` + `.env`.
    - Env overrides taking precedence over YAML for selected fields.
    - Validation failures when mandatory fields are missing or out of range.
   - Use temporary test fixtures or mocks for file reads.

14. Final verification
   - Run `pnpm build` and ensure no type errors from config modules.
   - Run `pnpm test` and confirm config tests pass.
   - Start the app and verify it logs a successful config load (without exposing secrets).
