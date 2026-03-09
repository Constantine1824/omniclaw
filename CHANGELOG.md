# Changelog

All notable changes to OmniClaw are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Rewrote the top-level documentation set for launch readability.
- Reduced README scope to the actual SDK entry points and runtime contract.
- Split docs by purpose: usage guide, API reference, architecture, and cross-chain usage.
- Removed stale or duplicate SDK markdown that conflicted with the current codebase.

### Fixed
- Documented the strict Redis environment contract around `OMNICLAW_REDIS_URL`.
- Documented trust-gate behavior so explicit trust checks require a real `OMNICLAW_RPC_URL`.
- Brought SDK-facing docs in line with the current async client surface and wallet flows.

### Verified
- SDK unit suite currently passes with `401` tests in `tests/`.

## [0.0.2] - 2026-01-22

### Added
- Initial public alpha of the OmniClaw SDK.
- Core payment client, wallet management, routing, guards, intents, ledger, and webhook support.
- Transfer, x402, and cross-chain adapter support.
- Onboarding helpers for Circle entity secret setup.

### Notes
- Requires Python `3.10+`.
- Requires Circle Web3 Services credentials.

[0.0.2]: https://github.com/omniclaw/omniclaw/releases/tag/v0.0.2
