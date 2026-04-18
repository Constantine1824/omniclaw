# OmniClaw CLI Reference

OmniClaw ships a single `omniclaw` command with several subcommands for setup, diagnostics, credential management, and server operation.

## Quick Start

```bash
# First-time setup
omniclaw setup --api-key <YOUR_CIRCLE_API_KEY>

# Check everything is configured
omniclaw doctor

# Start the Financial Firewall server
omniclaw server
```

---

## Commands

### `omniclaw setup`

Interactive first-run setup. Generates an entity secret, registers it with Circle, and writes a `.env.agent` file.

```bash
omniclaw setup [--api-key <KEY>] [--network ARC-TESTNET]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--api-key` | No | `CIRCLE_API_KEY` env | Circle API key |
| `--network` | No | `ARC-TESTNET` | Target network |

**Behaviour:**
1. Prompts for API key if not provided via flag or environment.
2. Checks if an entity secret already exists in the managed store.
3. If not found, prompts the user to enter one or auto-generates and registers a new one.
4. Writes credentials to `.env.agent`.

**Exit codes:** `0` success, `1` error.

---

### `omniclaw doctor`

Diagnose the local OmniClaw setup and credential state.

```bash
omniclaw doctor [--api-key <KEY>] [--entity-secret <SECRET>] [--json]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--api-key` | No | `CIRCLE_API_KEY` env | Override API key for diagnostics |
| `--entity-secret` | No | `ENTITY_SECRET` env | Override entity secret for diagnostics |
| `--json` | No | `False` | Output machine-readable JSON |

**Checks performed:**
- Circle SDK installed
- API key configured
- Entity secret available (environment or managed store)
- Recovery file present
- Recovery file permissions
- Environment/managed store secret mismatch

---

### `omniclaw backup-info`

Show the location and status of all backup-critical files.

```bash
omniclaw backup-info [--json]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--json` | No | `False` | Output machine-readable JSON |

**Output (human-readable):**
```
OmniClaw Backup Info
------------------------------
  Config directory:    ~/.config/omniclaw/
  Managed credentials: ~/.config/omniclaw/credentials.json  [FOUND]
  Recovery file:       ~/.config/omniclaw/recovery_file_abc123.dat  [FOUND]
  .env file:           /home/user/project/.env  [FOUND]

Recommended actions:
  - Copy the recovery file to a secure off-machine location.
  - The recovery file is required to reset your entity secret via the Circle console.
  - Do NOT commit the recovery file or credentials.json to version control.
```

**Warnings surfaced:**
- Recovery file missing
- Recovery file permissions too broad (expected `0o600`)
- Managed credentials store missing

---

### `omniclaw export-env`

Print active credentials as shell export statements or dotenv format.

```bash
omniclaw export-env [--format shell|dotenv] [--output <path>] [--force] [--api-key <KEY>]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--format` | No | `shell` | `shell` → `export VAR=value`. `dotenv` → `VAR=value` |
| `--output` | No | stdout | Write to file instead of stdout |
| `--force` | No | `False` | Overwrite output file if it exists |
| `--api-key` | No | `CIRCLE_API_KEY` env | Which API key's credentials to export |

**Resolution order:** environment → managed store.

**Shell format (default):**
```bash
export CIRCLE_API_KEY="sk_test_..."
export ENTITY_SECRET="abcd1234..."
export OMNICLAW_NETWORK="ARC-TESTNET"
```

> **Note:** A warning is printed to stderr: `# Warning: secrets printed to stdout. Pipe carefully.`

**Exit codes:** `0` success, `1` no credentials found.

---

### `omniclaw import-secret`

Import an existing entity secret into the managed config store without calling the Circle API.

```bash
omniclaw import-secret --entity-secret <SECRET> [--api-key <KEY>] [--recovery-file <PATH>]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--api-key` | Yes (or env) | `CIRCLE_API_KEY` | API key the secret belongs to |
| `--entity-secret` | Yes | — | 64-character hex entity secret |
| `--recovery-file` | No | — | Path to associated recovery file |

**Validation:**
- Entity secret must be exactly 64 hex characters.
- If `--recovery-file` is provided, the file must exist.

**Use cases:**
- Restoring credentials on a new machine from a vault or password manager.
- CI/CD pipelines that inject secrets at deploy time.
- Teams sharing a test API key where the entity secret is already registered.

**Exit codes:** `0` success, `1` validation error.

---

### `omniclaw env`

List all available OmniClaw environment variables with their status.

```bash
omniclaw env
```

Shows required, optional, and production environment variables with their current set/unset status.

---

### `omniclaw server`

Start the OmniClaw Control Plane (Financial Firewall) server.

```bash
omniclaw server [--host 0.0.0.0] [--port 8080] [--reload]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--host` | No | `0.0.0.0` | Host to bind to |
| `--port` | No | `8080` | Port to listen on |
| `--reload` | No | `False` | Enable auto-reload for development |

**Behaviour:**
1. Loads `.env.agent` (or `.env`) if present.
2. Auto-resolves entity secret from managed store if API key is set but secret is missing.
3. Starts a uvicorn server running the OmniClaw agent app.

---

### `omniclaw policy lint`

Validate a `policy.json` file against the OmniClaw policy schema.

```bash
omniclaw policy lint [--path /config/policy.json]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--path` | No | `/config/policy.json` (or `OMNICLAW_AGENT_POLICY_PATH`) | Path to policy file |

---

## Environment Variables

See `omniclaw env` for a full list. The most important ones:

| Variable | Required | Description |
|---|---|---|
| `CIRCLE_API_KEY` | Yes | Circle API key for wallet operations |
| `ENTITY_SECRET` | Auto | Auto-generated; only set manually for advanced usage |
| `OMNICLAW_NETWORK` | No | Network target (default: `ARC-TESTNET`) |
| `OMNICLAW_PRIVATE_KEY` | For nanopayments | Private key for nanopayment signing |
| `OMNICLAW_STORAGE_BACKEND` | No | `memory` (default) or `redis` |
| `OMNICLAW_LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## File Locations

| File | Location | Purpose |
|---|---|---|
| Managed credentials | `~/.config/omniclaw/credentials.json` | Stores entity secrets keyed by API key fingerprint |
| Recovery file | `~/.config/omniclaw/recovery_file_*.dat` | Circle recovery file for entity secret reset |
| `.env` / `.env.agent` | Project root | Environment variable file for local development |

> **Security:** The managed credentials store and recovery files use restrictive permissions (`0o600`). Never commit these files to version control.
