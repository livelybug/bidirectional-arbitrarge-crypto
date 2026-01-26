# Quick Start

Get the Cross-Chain Arbitrage Bot running locally.

## Prerequisites

- **Node.js** ≥24 (see `package.json` > `engines.node`)
- **pnpm** installed globally: `npm install -g pnpm`
- **Git** clone of this repository

## Installation

```bash
# From repo root
cd code/ts
pnpm install
```

## Configuration

### 1. Copy Environment Template

```bash
cd code/ts
cp .env.example .env
edit .env    # Add your RPC endpoints and secrets
```

### 2. Verify Configuration

```bash
# Print effective merged config (base YAML + env overrides)
pnpm config:print

# Example: print test or production config
APP_ENV=test pnpm config:print
APP_ENV=prd pnpm config:print
```

Output shows resolved `appEnv` and redacted `config` object.

## Running

### Development (Watch Mode)

```bash
cd code/ts
pnpm start:dev
```
- Builds on start
- Reloads on code changes
- 1s orchestrator loop with JSON logs

### One-Off Start

```bash
cd code/ts
pnpm start
```
- Uses pre-built `dist/` if available, else builds first
- Single run; exits on error

### Production Mode

```bash
cd code/ts
pnpm build
pnpm start:prod
```
- Builds optimized output
- Runs from compiled JavaScript
- For production deployment

## Expected Logs

On successful startup, you'll see JSON logs every second:

```json
{"ts":"2025-01-25T12:34:56.789Z","level":"info","msg":"Orchestrator tick","data":{"pairCount":5,"evaluatedMs":150}}
```

Look for:
- **"Pair discovery complete"** - Success at startup
- **"Orchestrator loop starting"** - 1s loop active
- **opId** - Correlation ID for tracing full cycles

## Common Setup Issues

**Startup fails with config error**:
- Check [Fast-Fail Errors](../config/fast-fail-errors.md) for exact error and fix

**No output / hanging**:
- Verify `config.yaml` has at least 2 chains with `dexList` entries
- Check `.env` has required RPC URLs (e.g., `ARBITRUM_RPC`)

**TypeScript errors**:
- Run `pnpm build` to see compilation errors
- Ensure all dependencies installed: `pnpm install`

## Next Steps

- [Architecture Overview](../architecture/overview.md) - System design
- [Config Reference](../config/reference.md) - Full config options
- [Pair Discovery](../implementation/pair-discovery.md) - How routes are generated

**Full README**: [README.ts.md](../readme/README.ts.md) - Detailed project documentation
