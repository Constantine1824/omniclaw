# Contributing

Thank you for contributing to OmniClaw.

This repository contains the Python SDK as the primary product surface, along with supporting docs, examples, and an optional MCP server.

## Project Areas

Main contribution areas:

- Python SDK in `src/omniclaw/`
- SDK tests in `tests/`
- docs in `docs/`
- examples in `examples/`
- MCP server in `mcp-server/`

## Local Setup

Clone the repository and install development dependencies:

```bash
uv sync --extra dev
```

Useful environment pieces for local work:

- Circle sandbox credentials for live-path testing
- Redis for execution-state and reservation testing
- `.env` configured for local development

## Common Commands

Run the SDK test suite:

```bash
.venv/bin/pytest tests
```

Run release-oriented checks:

```bash
./build.sh
```

Run static checks:

```bash
.venv/bin/ruff check src tests
python3 -m compileall src
```

## Pull Requests

When submitting a PR:

- keep scope focused
- explain the problem being solved
- describe behavioral changes clearly
- include or update tests when behavior changes
- update docs when public behavior changes

PRs are especially helpful when they improve:

- SDK reliability
- MCP server usability
- npm / TypeScript SDK progress
- docs and examples
- trust-aware or operator-friendly payment flows

## Coding Standards

Please follow these standards:

- prefer clear, boring, maintainable code
- keep public APIs explicit
- preserve backward compatibility where practical
- add tests for fixes and new behavior
- avoid unrelated refactors in focused PRs

For Python:

- use the existing project style
- keep changes typed where possible
- prefer small, readable functions over clever abstractions

## Branch Workflow

Recommended workflow:

1. create a branch from the current main branch
2. make focused commits
3. run relevant tests locally
4. open a pull request with clear context

Suggested branch naming:

- `feature/...`
- `fix/...`
- `docs/...`
- `ci/...`

## Issue-Driven Contributions

If possible, pick up an existing GitHub issue before starting work.

Good starting areas:

- docs improvements
- examples
- CLI improvements
- MCP server cleanup
- npm / TypeScript SDK work

## Security

If you find a security issue, do not open a public issue.

Please follow the guidance in [SECURITY.md](SECURITY.md).
