# Documentation Index

Complete guide for the Cross-Chain Bi-Directional Arbitrage Bot (TypeScript / Nest.js).

**Primary mode**: Multi-chain DEX aggregator arbitrage (e.g., OKX)  
**Fallback mode**: Native DEX-to-DEX (when no aggregators enabled)

## Quick Start
- [Getting Started](getting-started/quickstart.md) - Installation, setup, and first run

## Architecture
- [Component Overview](architecture/overview.md) - Module responsibilities and data flow (aggregator-first)
- [TypeScript Interfaces](architecture/interfaces.md) - Core type definitions
- [Core Sequences](architecture/sequences.md) - Price loop, execution, discovery flows
- [Error Handling](architecture/error-handling.md) - Retries, circuit-breakers, resilience

## Configuration
- [Schema Validation](config/schema.md) - Zod validation rules for config.yaml
- [Config Reference](config/reference.md) - Full config example with inline comments
- [Fast-Fail Errors](config/fast-fail-errors.md) - Startup errors and how to fix them

## Implementation Guides
- [Pair Discovery Algorithm](implementation/pair-discovery.md) - Route discovery from tokens and chains
- [Adding a DEX](implementation/adding-dex.md) - Integrate new DEX adapters
- [Adding a Chain](implementation/adding-chain.md) - Configure new blockchain network
- [Adding a Bridge](implementation/adding-bridge.md) - Integrate new bridge adapter

## Operations
- [Deployment & Environments](operations/deployment.md) - Environments, overlays, CI pipeline
- [Command Reference](operations/commands.md) - pnpm commands for build/test/run
- [Troubleshooting](operations/troubleshooting.md) - Common issues and solutions

## Requirements
- [Functional Requirements](FRD/FRD.md) - High-level product requirements and user stories

## Project Structure
```
code/ts/
├── src/
│   ├── orchestrator/        # Main trading loop
│   ├── price_monitor/      # Price fetching
│   ├── dex/                # DEX adapters (Uniswap V3, PancakeSwap V3, etc.)
│   ├── bridge/              # Bridge adapters (Stargate, etc.)
│   ├── risk_control/        # Risk management
│   └── utils/              # Config, wallet, logger
├── config.yaml              # Runtime configuration
└── .env                    # Environment variables (secrets, RPCs)
```

**Target:** TypeScript (prod), behavioral parity with Python reference.
