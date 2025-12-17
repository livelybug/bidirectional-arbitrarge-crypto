## T3c: Wallet & Config Utilities – Task Breakdown

Effort scale: **XS / S / M / L / XL**  
Priority: **P0 (must-have)**, **P1 (nice-to-have for Phase 1)**, **P2 (later)**

- [ ] **T3c.1 – Clarify wallet & config security model**  
	- Description: Define how private keys, RPC URLs, and other secrets are loaded (env vs encrypted keystore in `./wallets`), how they are referenced in `config.yaml`, and which environments (dev/test/prod) are supported. Capture rules for never committing secrets, using read-only accounts in testnets, and minimal-privilege RPC/API keys.  
	- Priority: P0  
	- Effort: S  
	- Dependencies: T1 (requirements), T2 (architecture roles for wallet/config).

- [ ] **T3c.2 – Extend config schema & types for chains, tokens, and wallets**  
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

