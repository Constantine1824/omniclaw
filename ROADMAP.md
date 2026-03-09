# Roadmap

This roadmap describes the current direction of OmniClaw as a product and open-source project.

OmniClaw is building the execution layer for AI-native payments: wallet orchestration, guarded spending, trust-aware execution, operator visibility, and payment flows that work for AI agents and AI-powered applications.

The roadmap is organized by phases, but work may progress in parallel where it makes sense.

## Phase 1: SDK Foundation

Focus: make the Python SDK the strongest and most reliable entry point.

Goals:

- stable wallet creation and management flows
- safe `simulate()` and `pay()` execution
- payment intents with reservation and confirmation handling
- Redis-backed locking and execution state
- `omniclaw doctor` for setup, recovery, and operator confidence
- stronger examples, release process, and contributor documentation

Outcomes:

- Python SDK is easy to install and adopt
- release process is predictable
- core flows are safe enough for production use

## Phase 2: Developer Integrations

Focus: make OmniClaw easier to integrate into real agent stacks and app backends.

Goals:

- production-ready MCP server
- official npm / TypeScript SDK
- framework-friendly examples for AI apps and agent systems
- better webhook, event, and observability support

Outcomes:

- developers can adopt OmniClaw from Python, TypeScript, or MCP-based agent environments
- SDK surface becomes easier to plug into real products

## Phase 3: Interoperability and Multi-Rail Payments

Focus: help AI systems move money across the rails and protocols they already use.

Goals:

- stronger x402 support
- stronger cross-chain USDC routing
- better route selection and payment simulation
- support for emerging agent interoperability patterns such as A2A where they improve real payment workflows

Notes:

- A2A is already part of the current ecosystem conversation, so OmniClaw treats it as an interoperability track, not as a distant future concept
- interoperability work should stay grounded in actual payment execution, trust, and operator control

Outcomes:

- OmniClaw becomes easier to use across web2 and web3 AI products
- payment routing becomes more flexible and production-friendly

## Phase 4: Agent Economy Primitives

Focus: expand from payment execution into the higher-level primitives AI-native commerce needs.

Exploration areas:

- delegated spending models
- escrow and approval workflows
- marketplace payment patterns
- richer trust-aware payment policies
- treasury and budget tooling for multi-agent systems

Outcomes:

- OmniClaw grows from payment execution into broader AI-native financial coordination

## Near-Term Priorities

The current near-term priorities are:

1. strengthen the Python SDK release surface
2. make the MCP server easier to run and contribute to
3. ship the npm / TypeScript SDK
4. improve docs, examples, and contributor onboarding
5. deepen trust-aware and operator-friendly payment workflows

## Project Principles

OmniClaw should stay aligned to these principles:

- product and developer facing, not hype driven
- safe by default
- interoperable across agent and payment ecosystems
- useful for both web2 and web3 AI products
- clear enough that outside contributors can extend it confidently
