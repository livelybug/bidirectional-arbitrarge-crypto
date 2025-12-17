## T3a: Environment-Specific Configuration – Analysis & Plan

### 1. Analysis: Environment-Based Configuration Management

#### 1.1. Core Challenges
- **Separation of concerns:** Keeping business/config logic in versioned files (chains, tokens, fees, risk, ops) while keeping secrets (keys, RPC auth) out of Git.
- **Environment drift:** Ensuring `dev`, `test`, and `prd` stay structurally identical (same schema and keys) even when actual values differ.
- **Determinism:** For discovery and risk logic, the same `config.yaml` structure must always produce the same `TradingPairConfig[]`; environment overlays must not introduce non-deterministic behavior.
- **Safety:** Preventing accidental use of production keys or endpoints in development or tests; making it obvious which environment is active.
- **Observability & debugging:** When something is misconfigured (missing DEX key, bad token coverage, wrong RPC), failures must be loud and attributable to a specific env source.

#### 1.2. Best Practices
- **Single canonical schema:** One typed schema (`config.types.ts` + `config.schema.ts`) that all environments must satisfy; per-env differences are values, not structure.
- **Base config + env overlays:** Maintain a base `config.yaml` that encodes shared structure and defaults; layer per-environment YAML files on top (e.g. `config.dev.yaml`, `config.test.yaml`, `config.prd.yaml`) with only overrides.
- **Secrets in environment variables only:** Wallet private keys, API keys, and any sensitive RPC credentials are read from env (or keystore referenced by env), never from YAML.
- **Explicit environment selection:** Use a small set of env identifiers (`APP_ENV ∈ {dev, test, prd}`) and log the chosen env and config files at startup.
- **Fail-fast loading:** If any required slice is missing or invalid in a given env (tokens, chains, dexList, wallets, ops), `ConfigService` must throw before the app bootstraps the orchestrator.
- **Override transparency:** When env overlays change values (e.g. `ops.loopIntervalMs`, `logging.level`, `wallets.keystorePath`), log which file and key were overridden to aid debugging.

#### 1.3. Strategy Options Considered
- **Option A – Single `config.yaml` + `.env.*` only:**
	- Pros: Simple; fewer files.
	- Cons: Harder to represent structural differences (e.g. different chain sets by env) without branching logic in code; more logic pushed into env variables.
- **Option B – Base YAML + per-env YAML overlays + env secrets (Chosen):**
	- Pros: Matches current YAML+Zod loader; keeps structure in files, secrets in env; easy to reason about `dev` vs `test` vs `prd` while sharing schema; enables consistent discovery behavior across envs.
	- Cons: Requires a small overlay-merge mechanism and some filename conventions.
- **Option C – Completely separate per-env configs:**
	- Pros: Maximal flexibility.
	- Cons: Easy schema drift; higher maintenance burden; weaker guarantees that dev/test are faithful models of prd.

**Recommended approach:** Option B – **base `config.yaml` plus per-env YAML overlays** (`config.dev.yaml`, `config.test.yaml`, `config.prd.yaml`), merged at load time, with secrets in env variables, controlled by `APP_ENV` and compatible with existing `APP_CONFIG_PATH` behavior.

---

### 2. Implementation Plan

#### 2.1. Recommended Approach Summary
- **Environments:** Support three explicit environments – `dev`, `test`, `prd` – selected via `APP_ENV` (defaulting to `dev` if unset for local development, and to `test` in Jest if needed).
- **Config files:**
	- `config.yaml` – base config shared across all envs (chains, tokens, DEX lists, general fees/risk/ops/logging structure and safe defaults).
	- `config.dev.yaml`, `config.test.yaml`, `config.prd.yaml` – optional per-env overlay files that only contain keys that differ from base (e.g. different RPC URLs, logging levels, loop intervals, wallet keystore paths).
- **Secrets:** Stay in `.env` / environment variables (e.g. `WALLET_KEYSTORE_PASSWORD`, `WALLET_PRIVATE_KEY`, RPC auth tokens). YAML files may reference paths but never embed secrets.
- **Loader behavior:** Extend existing `ConfigService` / `env-merge.ts` to:
	1. Resolve the base config path (`APP_CONFIG_PATH` or default `config.yaml`).
	2. Detect `APP_ENV` and load an optional overlay (`config.${APP_ENV}.yaml`) from the same directory.
	3. Deep-merge base + overlay (overlay wins) before passing into `loadAndMergeConfig` (env overrides) and `parseConfig` (Zod schema).
	4. Deep-freeze and expose the final `AppConfig`.
- **Testing & rollout:** Add Jest specs to validate merging behavior, env selection, and fail-fast semantics; introduce example per-env configs and documentation for operators.

#### 2.2. Practical Steps

1. **Define environment model and naming conventions**
	 - Decide on the canonical env variable: `APP_ENV` with allowed values `dev`, `test`, `prd`.
	 - Document that `NODE_ENV` is not authoritative for app config; it can still be used by tooling (e.g. Nest, Jest) but configuration selection is driven by `APP_ENV`.
	 - Update `FRD.md` / `arch_general.md` briefly to reference the three environments and configuration expectations.

2. **Create initial per-environment config templates**
	 - At the repo root (or where `config.yaml` lives), add:
		 - `config.dev.yaml` – tuned for local development: verbose logging, shorter `ops.loopIntervalMs` for testing, testnet RPC URLs, wallets pointing to non-production keys.
		 - `config.test.yaml` – minimal differences from base, focused on deterministic tests (possibly stub RPC endpoints or in-memory providers).
		 - `config.prd.yaml` – production-specific values: production RPC URLs, stricter `ops.loopIntervalMs`, higher log level, wallet keystore paths for production keys.
	 - Keep these templates **value placeholders only** (no secrets); use comments to indicate which env vars must be set alongside them.

3. **Extend the config loading flow (design-level plan)**
	 - In `ConfigService.loadConfig()` / `env-merge.ts` (design only for this task):
		 - Compute `baseConfigPath` as today (`APP_CONFIG_PATH` or `config.yaml`).
		 - Infer `env` from `APP_ENV` with validation:
			 - If `APP_ENV` is missing → default to `dev` (for CLI/dev runs); log a warning.
			 - If `APP_ENV` is not one of `dev`, `test`, `prd` → throw with a clear message.
		 - Derive `overlayPath` as `config.${env}.yaml` in the same directory as `baseConfigPath`.
		 - If `overlayPath` exists:
			 - Load and parse YAML to `overlayConfig`.
			 - Deep-merge `baseConfig` + `overlayConfig` (overlay wins, but never removes keys that base defines).
		 - If `overlayPath` does not exist:
			 - Proceed with `baseConfig` only and log an info-level message ("No env overlay for APP_ENV=dev; using base config.yaml only").
		 - Pass the merged config into existing `loadAndMergeConfig` to apply env overrides, then run `parseConfig` as usual.

4. **Clarify precedence rules**
	 - Document the precedence (from lowest to highest):
		 1. Base `config.yaml`.
		 2. Per-env overlay `config.${APP_ENV}.yaml` (if present).
		 3. Environment variables via the existing `env-merge` mechanism (e.g. `APP__CHAINS__ARBITRUM__RPC`).
	 - Ensure that env overrides cannot break schema structure; if they do, `parseConfig` must fail.

5. **Adjust config schema and types if needed**
	 - Verify that `AppConfig` and its nested types (`ChainsConfig`, `TokensConfig`, `OpsConfig`, `WalletsConfig`, etc.) cover all env-sensitive fields:
		 - `ops.loopIntervalMs`, `ops.priceRequestTimeoutMs`, `logging.level`, `logging.json`, `wallets.keystorePath`, etc.
	 - If any env-specific knobs are missing (e.g. `ops.dryRun` toggle), plan to add them under T3-11 / T3c tasks, keeping the schema uniform across envs.

6. **Design tests for environment-specific behavior**
	 - Add Jest tests (in `config.env-merge.spec.ts` or a new spec) that simulate different `APP_ENV` values and config file combinations:
		 - `APP_ENV=dev` with only `config.yaml` present → ensure loader picks base config and logs appropriate message.
		 - `APP_ENV=test` with `config.test.yaml` present → ensure specific overridden keys (e.g. `logging.level`, `ops.loopIntervalMs`) take effect.
		 - `APP_ENV=prd` with `config.prd.yaml` present → verify that production-specific overrides (e.g. RPC URLs) show up in the final `AppConfig`.
		 - Invalid `APP_ENV` (e.g. `staging`) → expect a thrown error with a clear message.
	 - Include at least one test that asserts the final merged config still passes discovery and fast-fail rules (e.g. tokens and chains remain consistent).

7. **Logging and diagnostics plan**
	 - On app startup, log a small structured payload from `ConfigService`:
		 - `env: APP_ENV`, `baseConfigPath`, `overlayPath` (if found), and counts of tokens/chains.
	 - When `env-merge` skips any env overrides (due to invalid keys), continue logging warnings as implemented today, making sure they include `APP_ENV` for context.

8. **Rollout & safety guidelines**
	 - **Development:**
		 - Default to `APP_ENV=dev` when running locally; use `config.dev.yaml` with testnet RPCs and dummy wallets.
		 - Ensure `.env.development` (or local `.env`) contains only non-sensitive values or test keys; keep `.env*` gitignored.
	 - **Testing:**
		 - In CI/Jest, explicitly set `APP_ENV=test` and point to `config.test.yaml` tuned for deterministic behavior.
		 - Add tests that assert `ConfigService` boots successfully under `test` with no manual intervention.
	 - **Production:**
		 - Require `APP_ENV=prd` in deployment manifests; mount `config.yaml` + `config.prd.yaml` via config maps or secrets as appropriate.
		 - Store secrets only in the environment (or secret manager), referenced by wallet/config code; verify with a smoke test that uses read-only RPC and wallet checks before enabling live trading.

9. **Operator documentation & examples**
	 - Extend `docs/readme/README.ts.md` or add a short section under `docs/arch/arch_general.md` that:
		 - Describes `APP_ENV` and the config file naming convention.
		 - Shows minimal examples of `config.yaml` plus `config.dev.yaml` overrides.
		 - Clarifies how to switch environments in local runs and CI.
	 - Provide a small matrix/table summarizing per-env expectations (chains enabled, RPC types, wallet key sources).

10. **Future extensions (optional)**
		- Introduce a `staging` env later if needed by adding `config.staging.yaml` and extending the allowed `APP_ENV` set.
		- Add a lightweight CLI or script to print the effective configuration for a given `APP_ENV` (redacted for secrets) to help operators inspect deployments.

