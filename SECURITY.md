# Security Policy

OmniClaw handles payment infrastructure concerns for AI agents and AI-powered applications. Security is a core part of the project.

## Scope

Please use this policy for vulnerabilities related to:

- credential handling
- wallet creation and payment execution
- transaction authorization flows
- trust evaluation and guard enforcement
- webhook verification
- Redis-backed locks, reservations, and execution state

## How Keys Are Handled

OmniClaw is designed around Circle developer-controlled wallet flows.

Important concepts:

- `CIRCLE_API_KEY` authenticates API access to Circle
- `ENTITY_SECRET` is the signing secret required for wallet and transaction operations
- Circle recovery files are stored locally for recovery workflows

Current model:

- credentials can be provided through environment variables or explicit constructor arguments
- OmniClaw can store managed credentials in the local config directory
- on Linux, managed local state is stored under `~/.config/omniclaw/`
- recovery material should never be committed to git or shared publicly

Operator guidance:

- do not commit `.env` files
- back up recovery material securely
- restrict local file permissions for managed secrets and recovery files
- rotate compromised keys immediately

## Transaction Signing Model

OmniClaw does not implement an independent blockchain signing stack.

The signing model is based on provider-backed wallet infrastructure:

- wallet and transaction operations are performed through Circle developer-controlled wallet APIs
- the `ENTITY_SECRET` is used as part of the provider authorization model
- OmniClaw adds orchestration around provider execution, including guards, simulation, intents, reservation handling, trust checks, and ledger visibility

This means security depends on both:

- secure handling of OmniClaw runtime credentials
- secure handling of the underlying provider account and recovery material

## Reporting a Vulnerability

Please do not open public GitHub issues for security vulnerabilities.

Use one of these channels instead:

- GitHub private security advisory, if enabled for the repository
- direct private disclosure to the maintainer at `abiolaadedayo1993@gmail.com`

Please include:

- affected component
- steps to reproduce
- impact assessment
- any proof of concept or logs that help confirm the issue

## Responsible Disclosure

Please follow responsible disclosure practices:

- give maintainers reasonable time to investigate and patch
- avoid public disclosure before a fix or mitigation is available
- avoid accessing data that does not belong to you
- avoid actions that could disrupt real wallets, funds, or production systems

## Security Priorities

We take reports especially seriously in these areas:

- unauthorized payment execution
- secret leakage
- trust-check bypasses
- webhook verification bypasses
- double-spend or reservation consistency issues
- lock, ledger, or state corruption affecting payment safety
