## T3c: Wallet & Config Utilities – Task Breakdown

Effort scale: **XS / S / M / L / XL**  
Priority: **P0 (must-have)**, **P1 (nice-to-have for Phase 1)**, **P2 (later)**

- [x] **T3c.1 – Clarify wallet & config security model**  
	- Description: Define how private keys, RPC URLs, and other secrets are loaded (env vs encrypted keystore in `./wallets`), how they are referenced in `config.yaml`, and which environments (dev/test/prod) are supported. Capture rules for never committing secrets, using read-only accounts in testnets, and minimal-privilege RPC/API keys.  
	- Priority: P0  
	- Effort: S  
	- Dependencies: T1 (requirements), T2 (architecture roles for wallet/config).

- [x] **T3c.2 – Extend config schema & types for chains, tokens, and wallets**  
	- Description: Ensure `config.types.ts` and `config.schema.ts` fully represent `chains[chainId].{rpc,tokenList,dexList}`, global `tokens.{base,quote}`, bridge/risk/fees/ops/logging, and wallet settings (e.g., `keystorePath`, key alias, derivation, optional labels for “hot” vs “cold” keys). Align with `arch_general.md`, `schema_validation.md`, and FRD platform lists.  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3 (project scaffold), T3b (discovery config needs), T3c.1.

- [ ] **T3c.3 – Harden `ConfigService` loading and validation**  
	- Description: Finalize `ConfigService` behavior: load `config.yaml` (respecting `APP_CONFIG_PATH`), merge env overrides via `env-merge`, apply Zod schema via `parseConfig`, deep-freeze the resulting `AppConfig`, and log skipped env overrides. Ensure it fails fast with clear error messages for missing files, invalid YAML, and schema violations (e.g., empty `chains`, missing `dexList`, unknown tokens).  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.2.

- [ ] **T3c.4 – Implement wallet utility for key management and providers**  
	- Description: Implement `utils/wallet.ts` to: load private keys from env/keystore, construct per-chain ethers providers/signers based on `config.chains[chainId].rpc`, expose helpers for getting balances, nonces, and sending generic transactions, and enforce a clear separation between read-only and signing contexts. Include basic safety checks (chainId match, address format validation).  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.1, T3c.2, `ConfigService` (T3c.3).

- [ ] **T3c.5 – Implement structured logger utility**  
	- Description: Implement `utils/logger.ts` providing a Nest-compatible `LoggerService` wrapper with JSON-structured logs, log levels, opId correlation, and configuration via `config.logging`. Ensure it is used by core modules (ConfigService, Wallet, PriceMonitor, DEX/Bridge adapters) for consistent diagnostics.  
	- Priority: P0  
	- Effort: S  
	- Dependencies: T3 (logging infra), T3c.2.

- [ ] **T3c.6 – Add unit tests for config loading and schema enforcement**  
	- Description: Add Jest specs to cover `ConfigService` and config schema behavior: valid config round-trip; invalid YAML; missing required fields; mismatched token coverage (Fast-fail A); empty or inconsistent `dexList`; environment override precedence. Include fixtures and snapshot key error messages where helpful.  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.2, T3c.3.

- [ ] **T3c.7 – Add unit tests for wallet and logger utilities**  
	- Description: Test `wallet.ts` with mocked providers/signers and sample configs: loading from env/keystore, provider selection per chain, basic balance/nonce fetch, and error handling for bad RPC URLs or missing keys. Test `logger.ts` for level handling, JSON formatting, and opId propagation.  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.4, T3c.5.

- [ ] **T3c.8 – Phase 2: Live RPC connectivity & wallet smoke tests (testnets)**  
	- Description: Using a non-production key and testnet RPCs, run a focused script or test harness that exercises `wallet.ts` end-to-end: fetch balances and nonces on at least one testnet per supported chain, and send a single low-value test transaction per chain. Verify logs from `logger.ts` and confirm failures for deliberately misconfigured RPC URLs or chainIds.  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.4, T3c.5, T3c.6, T3c.7; On-chain principle (Section 3 in `task.md`).

- [ ] **T3c.9 – Phase 2: Integrate wallet/config into higher-level modules**  
	- Description: Wire `ConfigService` and wallet utilities into DEX adapters, Bridge adapter, and Orchestrator so that all chain interactions use the common config and wallet layer. Confirm that test suites for T4 (PriceMonitor), T5 (DEX integrations), and T6 (Bridge) rely on these utilities instead of ad-hoc providers or inline config.  
	- Priority: P0  
	- Effort: M  
	- Dependencies: T3c.4, T3c.6, T3c.7; T4, T5, T6 design tasks.

- [ ] **T3c.10 – Documentation and runbook for wallet & config**  
	- Description: Document wallet and config usage: sample `config.yaml` snippets, required env vars, how to set up keystore files in `./wallets`, per-environment (dev/test/prod) conventions, and safety guidelines for mainnet keys. Link this doc from `arch_general.md` and the main `README`.  
	- Priority: P1  
	- Effort: S  
	- Dependencies: T3c.1–T3c.8.


### T3c.1 – Wallet & Config Security Model (v1)

**Goal:** Define a clear, enforceable security model for how wallets, RPC endpoints, and other secrets are configured across environments, without blocking local development.

#### 1. Sources of truth & storage locations

- **Config files (`config.yaml` + overlays):**
	- Store only non-sensitive configuration: chain IDs, token lists, DEX keys, and *non-secret* RPC base URLs.
	- Environment-specific overlays (`config.dev.yaml`, `config.test.yaml`, `config.prd.yaml`) may override RPC URLs and operational settings, but must **never** contain private keys, keystore JSON, mnemonics, or embedded API keys in query strings.
- **Environment variables:**
	- Primary channel for secrets: keystore passphrases, raw private keys (dev-only), and RPC/API keys (e.g., Alchemy/Infura keys) live in env vars or an external secret store, not in git.
	- Example (indicative, to be wired in T3c.2/T3c.4): `WALLET_KEYSTORE_PASSPHRASE`, `DEV_WALLET_PK`, `ARBITRUM_RPC_API_KEY`.
- **Keystore files (`./wallets`):**
	- Standardize on encrypted JSON keystores (Ethers/Web3-compatible) stored under `./wallets` with paths referenced from `config.wallets.keystorePath`.
	- Keystore files are encrypted at rest; passphrases are provided via environment/secret manager only.
	- The entire `./wallets` directory is expected to be gitignored; only documentation or sample filenames are committed.

#### 2. Environment matrix (dev / test / prd)

| Env  | Keys & addresses                                                                 | RPC configuration                                                              | Allowed secret sources                                 | Usage rules |
|------|----------------------------------------------------------------------------------|-------------------------------------------------------------------------------|--------------------------------------------------------|------------|
| dev  | Raw private key via env (`DEV_WALLET_PK`) **allowed**; encrypted keystore optional. | RPC endpoints may be public/test or free-tier; API keys in env only.          | Env vars for keys and RPC API keys; optional local keystore. | Small funds only; intended for local development and experimentation. |
| test | **Preferred:** encrypted keystore in `./wallets/test/…` referenced by config; read-only observer keys acceptable. | Dedicated testnet RPC endpoints; URLs in config, sensitive keys in env. | Env vars + encrypted keystores; raw private keys strongly discouraged. | Used for pre-production validation on testnets with non-production funds. |
| prd  | **Only:** encrypted keystore(s) in `./wallets/prod/…`; no raw private keys; one hot trading wallet per env for now. | Dedicated production RPC endpoints; host/chain in config, API keys in env only. | Env/secret manager + keystores; no secrets from CLI args or files in git. | Real capital; cold storage stays outside the bot; manual funding/withdrawal. |

For v1, there is **exactly one active hot trading wallet per environment** (future roles like funding / observer / cold wallets can be added later in T3c.2/T3c.9).

#### 3. How config references wallets and RPC endpoints

- `config.wallets.keystorePath` points to an encrypted keystore JSON file under `./wallets` (e.g., `./wallets/dev/trader.json`, `./wallets/prod/trader.json`).
- `config.wallets.address` holds the corresponding public address (checksummed string) and is used for logging, position sizing, and safety checks.
- Future wallet metadata (to be formalized in T3c.2) may include labels (e.g., `env: dev/test/prd`, `role: hot`) but **must not** include raw private keys or passphrases.
- `config.chains[chainId].rpc` contains the base RPC URL or host; if a provider requires an API key, that key is appended or injected from env at runtime by the wallet/provider layer, not stored in YAML.

#### 4. Rules for secrets, git, and logging

- **No secrets in git:**
	- Never commit private keys, mnemonics, encrypted keystore JSON with real keys, or real RPC API keys to the repository.
	- Commit only templates and examples (e.g., `wallets/README.md`, sample keystore filenames, example config snippets with placeholders like `<YOUR_API_KEY>`).
- **`./wallets` handling:**
	- `./wallets` is a runtime-only directory. Operators provision keystores out-of-band and ensure they are gitignored and excluded from artifacts.
- **Environment-specific config safety:**
	- APP_ENV (`dev` / `test` / `prd`) selects which overlay to use, but overlays follow the same rule: no secrets, only structure and non-sensitive values.
	- Any schema fields that could be sensitive (wallets, RPC auth) must be designed so that the *presence* of a path or label is in YAML, while the actual secret material stays in env/secret manager.
- **CLI and logging:**
	- The `config:print` CLI intentionally redacts `wallets` (and future secret-bearing sections) so operators can inspect effective config without leaking secrets.
	- Logging must never print raw private keys, keystore contents, mnemonics, or full RPC URLs with embedded API keys. Logs should use addresses, chain IDs, and short-hash identifiers instead.

This model aligns with the FRD security requirement that "Private keys and sensitive API keys must be stored securely and not exposed in the codebase" and with the existing `ConfigService` + `APP_ENV` design. Concrete schema fields and wallet utility behavior will be implemented in **T3c.2–T3c.4** under this model.

### T3c.4 – Wallet Utility Implementation Plan (v1)

**Goal:** Implement a single `WalletService` (wallet utility) that turns the validated config + environment secrets into safe, reusable ethers providers/signers per chain, with a clear separation between read-only and signing operations. This service must support **real on-chain reads and real on-chain transactions** against whatever RPC endpoints and keys are configured.

#### 1. Define WalletService API surface

- Design and **fully implement** the public methods for `WalletService` in `src/utils/wallet/wallet.service.ts` using `ethers.js`:
	- `getReadOnlyProvider(chainId: ChainId): Provider` – returns a concrete `ethers.JsonRpcProvider` (or compatible) that talks to the real RPC URL from `config.chains[chainId].rpc`.
	- `getSigner(chainId: ChainId): Signer` – returns a concrete `ethers.Wallet` (or compatible signer) connected to the provider for that `chainId`, only when a private key/keystore is successfully loaded.
	- `getNativeBalance(chainId: ChainId): Promise<bigint>` – calls `provider.getBalance(config.wallets.address)` on-chain and returns the live native token balance.
	- `getTokenBalance(chainId: ChainId, tokenAddress: string): Promise<bigint>` – instantiates a minimal ERC‑20 contract (e.g., `balanceOf(address)`) via `ethers` and returns the on-chain token balance.
	- `getNonce(chainId: ChainId): Promise<number>` – calls `provider.getTransactionCount(config.wallets.address)` to fetch the current on-chain nonce.
	- `sendTransaction(chainId: ChainId, tx: TransactionRequest): Promise<TransactionReceipt>` – when `ops.dryRun === false`, sends a real transaction via `signer.sendTransaction(tx)` and waits for a mined `TransactionReceipt`; when `ops.dryRun === true`, logs and skips the send.
- Keep the API narrow and chain-agnostic; DEX/Bridge adapters should not know how keys are stored, only how to obtain providers/signers.

##### Implementation steps for WalletService API surface (coding checklist)

1. **Create service shell and wiring**
	- Add `WalletService` in `src/utils/wallet/wallet.service.ts` as a Nest `@Injectable()` class.
	- Inject `ConfigService` and `LoggerService` via the constructor and cache `config.wallets`, `config.chains`, and `config.ops` on construction.
	- Define private fields: `providersByChainId = new Map<ChainId, Provider>()` and `signersByChainId = new Map<ChainId, Signer>()`.

2. **Add internal helpers for providers and signer**
	- Implement `private getOrCreateProvider(chainId: ChainId): Provider` that:
		- Looks up `config.chains[chainId]`, throws a typed `WalletConfigError` if missing.
		- Validates `chainConfig.rpc` is a non-empty string.
		- Lazily constructs and caches an `ethers.JsonRpcProvider` in `providersByChainId`.
	- Implement `private getOrLoadBaseSigner(): Wallet` that:
		- Uses the key-loading strategy from section 3 (env vs keystore) to construct a single base `ethers.Wallet`.
		- Verifies the derived address matches `config.wallets.address` (case-insensitive) and throws `WalletKeyLoadError` if not.
		- Caches the base signer instance for reuse.

3. **Implement `getReadOnlyProvider`**
	- Call `getOrCreateProvider(chainId)` and return the provider.
	- Log at debug level when a provider is first created for a `chainId` (include `wallets.env`/`wallets.role` if present).
	- Ensure this method never requires a loaded private key and can be used safely in discovery/dry-run paths.

4. **Implement `getSigner`**
	- Call `getOrLoadBaseSigner()` to obtain the base signer (may throw if no key/keystore is available per environment rules).
	- Resolve the provider for the requested `chainId` via `getOrCreateProvider(chainId)` and return `baseSigner.connect(provider)`.
	- Cache the connected signer in `signersByChainId` so repeated calls for the same chain reuse the same object.
	- Throw a typed `WalletConfigError` if the chain is unknown or its RPC URL is missing.

5. **Implement balance and nonce helpers**
	- `getNativeBalance(chainId)`:
		- Use `const provider = this.getReadOnlyProvider(chainId)`.
		- Call `provider.getBalance(config.wallets.address)` and return the result as `bigint`.
	- `getTokenBalance(chainId, tokenAddress)`:
		- Validate `tokenAddress` format (starts with `0x` and length 42) and throw `WalletConfigError` on failure.
		- Use `getReadOnlyProvider(chainId)` and instantiate a minimal ERC‑20 `ethers.Contract` with `balanceOf(address)`.
		- Call `contract.balanceOf(config.wallets.address)` and return the result as `bigint`.
	- `getNonce(chainId)`:
		- Use `getReadOnlyProvider(chainId)` and call `provider.getTransactionCount(config.wallets.address)` with the latest block tag.
		- Return the numeric nonce.

6. **Implement `sendTransaction` with dry-run support**
	- Read `ops.dryRun` from the cached config:
		- If `dryRun === true`:
			- Log at info level that a dry-run transaction was skipped, including `chainId` and a redacted summary of `tx`.
			- Throw a dedicated `WalletDryRunError` so callers know no transaction was actually sent.
		- If `dryRun === false`:
			- Obtain a signer via `getSigner(chainId)`; let any missing-key errors surface as `WalletKeyLoadError`.
			- Optionally normalize gas parameters on `tx` (e.g., ensure `chainId`, `nonce` are consistent; leave tuning for later tasks).
			- Call `const response = await signer.sendTransaction(tx)` and then `const receipt = await response.wait()`.
			- Log the final receipt (tx hash, status, gas used) at info level without leaking sensitive details.
			- Return the `TransactionReceipt`.

7. **Error handling and typing**
	- Define error classes in `wallet.service.ts` (or a small sibling file) for `WalletConfigError`, `WalletKeyLoadError`, `WalletRpcError`, and `WalletDryRunError`.
	- Wrap low-level RPC or provider errors thrown by ethers in `WalletRpcError` where it improves clarity, preserving the original error as `cause`.
	- Ensure all public methods reject with these typed errors rather than raw strings where possible, so upstream modules can discriminate failure modes in tests and at runtime.

#### 2. Wire dependencies and config resolution

- Inject `ConfigService` and `LoggerService` into `WalletService` (via `UtilsModule`), and cache `config.wallets` + `config.chains` on construction.
- Create internal maps:
	- `providersByChainId: Map<ChainId, Provider>` – lazily constructed from `config.chains[chainId].rpc`.
	- `signersByChainId: Map<ChainId, Signer>` – lazily constructed when first needed.
- Respect the wallet metadata from config:
	- `wallets.address` is the canonical public address and is used for all balance/nonce queries and safety checks.
	- Optional `wallets.env` and `wallets.role` (from T3c.2) are used only for logging/diagnostics (e.g., `[wallet env=dev role=hot]`).

#### 3. Implement key loading strategy (env + keystore)

- Implement a private key loader that follows the T3c.1 security model:
	- **dev:** allow raw private key from env (e.g., `DEV_WALLET_PK`) *or* encrypted keystore from `wallets.keystorePath` + passphrase env.
	- **test/prd:** only load from encrypted keystore at `wallets.keystorePath`; passphrase must come from env/secret manager (e.g., `WALLET_KEYSTORE_PASSPHRASE`). If missing or invalid, fail fast with a clear, non-secret-leaking error.
- Use ethers-compatible helpers to:
	- Load a JSON keystore file from `wallets.keystorePath`.
	- Decrypt it using the env-provided passphrase.
	- Instantiate a `Wallet`/`Signer` bound to the correct provider.
- Ensure the loaded signer address exactly matches `wallets.address` (see safety checks below).

#### 4. Provider and signer construction per chain

- For each `chainId` present in `config.chains`:
	- Build a concrete `ethers.JsonRpcProvider` using `config.chains[chainId].rpc` (plus any API key interpolation from env, if required by the final implementation).
	- When a signer is needed, connect the shared signer instance to the appropriate provider via `signer.connect(provider)` so that all subsequent calls (including `sendTransaction`) hit the real network for that `chainId`.
- Support chains where only read-only access is needed (e.g., discovery-only chains) by allowing a `Provider` without a signer; `getSigner` should throw a typed error if no key is loaded.

#### 5. Safety checks and invariants

- On first key load, compare the signer’s derived address with `config.wallets.address`:
	- If they differ (case-insensitive), throw a configuration error and log a clear message without printing any private key or passphrase.
- On first use of a provider per chain, optionally fetch `provider.getNetwork()` and compare with an expected chain mapping (if maintained elsewhere) to catch misconfigured RPC URLs (wrong network for a `chainId`).
- Validate token addresses passed to `getTokenBalance` and `sendTransaction` helpers:
	- Must start with `0x` and have length 42 characters, aligning with schema expectations.

#### 6. Read-only vs signing separation

- Ensure all balance and pricing read paths can use `getReadOnlyProvider` without requiring a private key (useful for discovery and dry-run modes). These **must** perform real on-chain reads via the configured RPC endpoints.
- Restrict any state-changing operations to use `getSigner` and fail clearly when a signer is unavailable (e.g., missing key/keystore or dry-run restrictions).
- Honour `ops.dryRun` from config in `sendTransaction`:
	- When `dryRun` is true, log the would-be transaction and short-circuit without sending on-chain.
	- When `dryRun` is false, `sendTransaction` **must** submit a real transaction to the network and await a mined receipt, subject to normal network and gas behaviour.

#### 7. Logging and error handling

- Use `LoggerService` for structured logs around wallet operations:
	- Log when providers/signers are first constructed, including `chainId`, `wallets.env`, and `wallets.role` (if present).
	- Log balance/nonce fetches at debug level; log transaction submissions and receipts at info level.
	- Never log private keys, keystore contents, passphrases, or full RPC URLs with embedded API keys.
- Define a small internal error taxonomy for wallet operations (e.g., `WalletConfigError`, `WalletKeyLoadError`, `WalletRpcError`) to make upstream error handling easier in DEX/Bridge/Orchestrator modules.

#### 8. Small dev/test harness (pre-T3c.8)

- Add a minimal, non-production harness to sanity-check the wallet utility before full Phase 2 (T3c.8):
	- Either a focused Jest spec (e.g., `src/utils/wallet/wallet.service.dev-smoke.spec.ts`) or a small script under `code/ts/scripts/` (e.g., `wallet-dev-balance.ts`).
	- Behavior:
		- Use `APP_ENV=dev` and a tiny-funded dev/test key (raw env or keystore as per T3c.1).
		- Instantiate `WalletService` via the Nest testing module or a lightweight bootstrap.
		- Fetch and log the native balance and nonce on a single configured chain (no live transactions yet).
- Keep this harness clearly scoped to dev/test; full multi-chain, on-chain send tests remain the responsibility of **T3c.8**.

These steps keep T3c.4 scoped to a robust v1 wallet utility that respects the security model from T3c.1 and the config schema from T3c.2, while also guaranteeing that all wallet methods for balances, nonces, and `sendTransaction` are implemented concretely against real RPC endpoints. This lays the groundwork for the deeper on-chain validation in T3c.8 and allows `WalletService` to be used immediately for real on-chain reads and transactions (with appropriate keys, RPCs, and `ops.dryRun` settings).
 surface