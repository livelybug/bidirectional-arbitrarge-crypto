# Deployment & Environments

Multi-environment configuration and deployment strategies.

## Environment Types

| Env | Purpose | RPC Configuration | Wallet Source | Allowed Secrets |
|-----|-----------|-------------------|---------------|-----------------|
| **dev** | Local development and experimentation | Public/testnet RPCs | Raw private key via env (dev-only) or encrypted keystore | Env vars only; optional local keystore |
| **test** | Pre-production validation on testnets | Dedicated testnet RPCs | **Preferred**: Encrypted keystore; read-only observer keys acceptable | Env vars + keystores; raw keys discouraged |
| **prd** | Production with real capital | Dedicated production RPCs | **Only**: Encrypted keystores in `./wallets/prod/` | Env/secret manager + keystores; no raw private keys |

## Environment Configuration

### Dev Environment

**Activation**: `APP_ENV=dev` (default when unset)

**Config Overlay**: `config.dev.yaml` (optional)
- Overrides: Verbose debug logging, testnet RPC URLs
- Use for: Local testing, code experimentation, integration testing

**Example** `config.dev.yaml`:
```yaml
ops:
  loopIntervalMs: 5000             # Longer intervals for dev (don't spam)
logging:
  level: debug                  # Verbose output
  includeCaller: true             # Show file/line in logs
```

### Test Environment

**Activation**: `APP_ENV=test`

**Config Overlay**: `config.test.yaml` (optional)
- Overrides: Quieter logs, shorter loop intervals, CI-friendly settings
- Use for: Automated testing, CI pipelines, staging validation

**Example** `config.test.yaml`:
```yaml
ops:
  loopIntervalMs: 20000            # Longer for test efficiency
logging:
  level: warn                    # Less noise in CI
  json: false                    # Readable in CI logs
```

### Production Environment

**Activation**: `APP_ENV=prd`

**Config Overlay**: `config.prd.yaml` (optional)
- Overrides: Production RPC URLs, production wallet keystore paths
- Use for: Real-money operations, live trading

**Example** `config.prd.yaml`:
```yaml
# No overrides needed if config.yaml has production-ready values
# Only specify if prod-specific tweaks required
```

## Configuration Loading Priority

ConfigService loads in this order (later values override earlier):

1. **Base YAML**: `config.yaml`
2. **Environment overlay**: `config.{APP_ENV}.yaml` (dev/test/prd)
3. **Environment variables**: `.env` (injected into merged config)
4. **Validation**: Zod schema validates final merged config

Example:
```yaml
# config.yaml (base)
tokens:
  base: [WIF, PEPE]
  quote: [USDT]

# config.dev.yaml (override)
ops:
  dryRun: false              # Live mode for dev testing
```

```bash
# .env
ARBITRUM_RPC=https://public-rpc-url.com
```

**Final Result**: Base config + dev overlay + env vars + Zod validation.

## Wallet Matrix by Environment

### Dev Wallet
- **Location**: `./wallets/dev/` (if using keystore)
- **Keys**: Raw private key via `DEV_WALLET_PK` (allowed for dev)
- **Funding**: Small amounts only; testnet or minimal mainnet
- **Security**: Never commit; rotate keys regularly

### Test Wallet
- **Location**: `./wallets/test/`
- **Keys**: Encrypted keystore (preferred); read-only observer keys acceptable
- **Funding**: Non-production test tokens; testnet-specific values
- **Security**: No raw private keys; keystore passwords in env only

### Production Wallet
- **Location**: `./wallets/prod/`
- **Keys**: **Only** encrypted keystores; cold storage outside bot
- **Funding**: Real production capital
- **Security**: Strict separation; manual funding/withdrawal; no CLI args for keys

## Deployment Artifacts

### Build Output
```bash
cd code/ts
pnpm build
```
Produces: `dist/` directory with compiled JavaScript.

### Containerization (Optional)
```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN pnpm install --prod
COPY . .
RUN pnpm build
CMD ["node", "dist/main.js"]
```

### Deployment Config
All configuration is runtime-driven. No code changes per environment.

- Environments switched via `APP_ENV` env var
- Secrets injected via `.env` or secret manager
- No environment-specific code branches

## CI Pipeline

**Location**: `.github/workflows/ci.yml`

**Stages**:
1. **Lint**: `pnpm lint` (auto-fix errors)
2. **Build**: `pnpm build` (type-check + compile)
3. **Test**: `pnpm test -- --runInBand` (run tests sequentially)

**Quality Gates**: All stages must pass for PR merge.

## Health Checks (Future)

Planned improvements for deployment monitoring:

- `/status` endpoint: Returns `healthy`, `paused`, or `degraded`
- Loop heartbeat logs: Every 60s, log "Orchestrator heartbeat: tick=${count}"
- Metrics export: Prometheus format for external monitoring

## Rollback Strategy

If production deployment fails:

1. **Immediate rollback**: Revert to previous working container/config
2. **Investigate**: Check logs for root cause (config error, network issue)
3. **Fix**: Address issue in code or config
4. **Re-deploy**: Push updated version with fix verification

## Security Checklist

- [ ] No private keys in git (use `.gitignore`)
- [ ] `.env` never committed (use `.env.example` as template)
- [ ] Production wallets encrypted with strong passwords
- [ ] RPC endpoints use HTTPS or authenticated providers
- [ ] Rate limits configured on external APIs
- [ ] Fail-fast enabled to prevent running with bad config
- [ ] Stop-loss configured for production (15-30% loss threshold)

## Related Documentation

- [Config Reference](../config/reference.md) - Full config structure
- [Fast-Fail Errors](../config/fast-fail-errors.md) - Configuration errors
- [Commands Reference](commands.md) - pnpm commands
