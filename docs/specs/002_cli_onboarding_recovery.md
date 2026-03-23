# Spec 002 — CLI Onboarding & Recovery Commands

**Status:** Draft
**Author:** —
**Created:** 2026-03-23

## Summary

`omniclaw doctor` exists but only diagnoses. Users still need explicit CLI commands to **set up**, **inspect backup state**, **export credentials**, and **import an existing entity secret**. This spec adds four new subcommands to close those gaps.

---

## Background

### What exists today

| Layer | What's there |
|---|---|
| `cli.py` | Only `omniclaw doctor` (diagnosis, `--json` output) |
| `onboarding.py` | `quick_setup()` — generates entity secret, registers with Circle, writes `.env`, saves recovery file to config dir. `auto_setup_entity_secret()` — silent version called by the SDK client when `ENTITY_SECRET` is missing. `doctor()` — reads env / managed store / recovery file and returns a status dict |
| Config store | `~/.config/omniclaw/credentials.json` (Linux), `%APPDATA%/omniclaw/credentials.json` (Windows), `~/Library/Application Support/omniclaw/credentials.json` (macOS). Keyed by SHA-256 fingerprint of the API key. Stores entity secret, masked values, source, recovery file path |
| Recovery files | `recovery_file_*.dat` in the config dir. Created by Circle SDK during `register_entity_secret()`. Needed to reset a lost entity secret via the Circle console |

### What's missing

1. No CLI path to run `quick_setup()` — users must write Python or rely on auto-setup.
2. No way to quickly see "where are my backup files and what should I do with them" from the CLI.
3. No way to export the managed entity secret into shell env vars or a `.env` file from the CLI.
4. No way to import an already-known entity secret (e.g. from a teammate or CI vault) into the managed store without writing Python.

---

## Proposed Commands

### 1. `omniclaw setup`

Interactive first-run setup. Wraps `quick_setup()` with CLI ergonomics.

```
omniclaw setup --api-key <KEY> [--network ARC-TESTNET] [--env-path .env] [--force]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--api-key` | Yes (or `CIRCLE_API_KEY` env) | — | Circle API key |
| `--network` | No | `ARC-TESTNET` | Target network |
| `--env-path` | No | `.env` | Where to write the env file |
| `--force` | No | `False` | Overwrite existing `.env` |

**Behaviour:**
1. Validate Circle SDK is installed. Exit with a clear message if not.
2. Check if credentials already exist (managed store + `.env`). If they do and `--force` is not set, print current state and ask the user to confirm or re-run with `--force`.
3. Call `generate_entity_secret()`.
4. Call `register_entity_secret()` → saves recovery file to config dir.
5. Call `create_env_file()` → writes `.env`.
6. Call `store_managed_credentials()` → persists to managed store.
7. Print summary: paths to `.env`, recovery file, config dir. Remind user to back up recovery file.

**Exit codes:** `0` success, `1` setup error, `2` user abort.

---

### 2. `omniclaw backup-info`

Show the location and status of all backup-critical files.

```
omniclaw backup-info [--json]
```

**Output (human-readable):**
```
OmniClaw Backup Info
------------------------------
  Config directory:    ~/.config/omniclaw/
  Managed credentials: ~/.config/omniclaw/credentials.json  [FOUND]
  Recovery file:       ~/.config/omniclaw/recovery_file_abc123.dat  [FOUND]
  .env file:           /home/user/project/.env  [FOUND]

Recommended actions:
  - Copy the recovery file to a secure off-machine location (e.g. password manager, encrypted USB).
  - The recovery file is required to reset your entity secret via the Circle console if it is lost.
  - Do NOT commit the recovery file or credentials.json to version control.
```

**Data returned (JSON mode):**
```json
{
  "config_dir": "~/.config/omniclaw/",
  "managed_credentials_path": "~/.config/omniclaw/credentials.json",
  "managed_credentials_exists": true,
  "recovery_file_path": "~/.config/omniclaw/recovery_file_abc123.dat",
  "recovery_file_exists": true,
  "recovery_file_permissions": "0o600",
  "env_file_path": "/home/user/project/.env",
  "env_file_exists": true,
  "warnings": []
}
```

**Warnings surfaced:**
- Recovery file missing → "No recovery file found. Run `omniclaw setup` or back up from another machine."
- Recovery file permissions too broad → "Recovery file permissions are {mode}. Expected 0o600."
- Managed store missing → "No managed credentials found. Run `omniclaw setup` or `omniclaw import-secret`."

---

### 3. `omniclaw export-env`

Print the active credentials as shell export statements or append them to a `.env` file.

```
omniclaw export-env [--format shell|dotenv] [--output <path>] [--api-key <KEY>]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--format` | No | `shell` | `shell` → `export VAR=value` lines. `dotenv` → `VAR=value` lines |
| `--output` | No | stdout | If set, write to file instead of stdout. Refuses to overwrite unless `--force` is also passed |
| `--force` | No | `False` | Allow overwriting the output file |
| `--api-key` | No | `CIRCLE_API_KEY` env | Which API key's credentials to export |

**Resolution order for entity secret:** environment → managed store (same as `doctor()`).

**Shell format (default, printed to stdout):**
```bash
export CIRCLE_API_KEY="sk_test_..."
export ENTITY_SECRET="abcd1234..."
export OMNICLAW_NETWORK="ARC-TESTNET"
```

**Dotenv format:**
```
CIRCLE_API_KEY=sk_test_...
ENTITY_SECRET=abcd1234...
OMNICLAW_NETWORK=ARC-TESTNET
```

**Security:** `export-env` **does not** include the raw API key in stdout by default; it reads it from the environment. The entity secret is the one pulled from the managed store. Users should pipe output carefully. A warning line is printed to stderr: `# Warning: secrets printed to stdout. Pipe carefully.`

**Exit codes:** `0` success, `1` no credentials found.

---

### 4. `omniclaw import-secret`

Import an existing entity secret into the managed store without running full setup (no Circle API call, no registration).

```
omniclaw import-secret --api-key <KEY> --entity-secret <SECRET> [--recovery-file <PATH>]
```

| Flag | Required | Default | Description |
|---|---|---|---|
| `--api-key` | Yes (or `CIRCLE_API_KEY` env) | — | Circle API key the secret belongs to |
| `--entity-secret` | Yes | — | 64-char hex entity secret |
| `--recovery-file` | No | — | Path to the associated recovery file. If provided, its path is recorded in the managed store |

**Behaviour:**
1. Validate entity secret format (64 hex chars).
2. If `--recovery-file` is provided, verify the file exists.
3. Call `store_managed_credentials(api_key, entity_secret, source="cli_import", recovery_file=...)`.
4. Print confirmation with masked values.
5. Suggest running `omniclaw doctor` to verify.

**Use cases:**
- Restoring credentials on a new machine from a vault or password manager.
- CI/CD pipelines that inject secrets at deploy time and want them in the managed store for the SDK to pick up automatically.
- Teams sharing a test API key where the entity secret is already registered.

**Exit codes:** `0` success, `1` validation error.

---

## Files Changed

### `src/omniclaw/cli.py`
- Add `setup`, `backup-info`, `export-env`, and `import-secret` subcommands to the argparse parser.
- Wire each subcommand to a handler function.

### `src/omniclaw/onboarding.py`
- Add `backup_info()` → returns a dict with all backup-related paths + status + warnings.
- Add `export_credentials()` → returns credential dict resolved from env / managed store.
- Add `import_entity_secret()` → validates and stores an entity secret in the managed store.
- Minor: expose `print_backup_info()` for human-readable output (mirrors `print_doctor_status()`).

### `src/omniclaw/__init__.py`
- Export `backup_info`, `export_credentials`, `import_entity_secret` if they should be part of the public API.

### `docs/`
- New or updated doc covering all CLI commands (could be `docs/CLI_REFERENCE.md` or additions to `docs/SDK_USAGE_GUIDE.md`).

### `tests/test_setup.py`
- Add tests for `backup_info()`, `export_credentials()`, `import_entity_secret()`.
- Add tests for CLI argument parsing and handler dispatch for the new subcommands.

---

## Verification Plan

### Automated Tests

Existing tests live in `tests/test_setup.py`. New tests will be added to the same file following the same patterns (temp dirs, `patch.dict(os.environ, ...)`, `capsys` for CLI output).

**Run with:**
```bash
uv run pytest tests/test_setup.py -v
```

New test classes:

| Test Class | What it covers |
|---|---|
| `TestBackupInfo` | `backup_info()` returns correct paths, detects missing files, surfaces permission warnings |
| `TestExportCredentials` | `export_credentials()` resolves from env → managed store, formats `shell` and `dotenv` output |
| `TestImportEntitySecret` | `import_entity_secret()` stores credentials, validates 64-hex format, rejects bad input, handles optional recovery file |
| `TestCLISetup` | `build_parser()` + `main(["setup", ...])` dispatches correctly, exits with right codes |
| `TestCLIBackupInfo` | `main(["backup-info"])` and `main(["backup-info", "--json"])` produce expected output |
| `TestCLIExportEnv` | `main(["export-env"])` formats correctly, `--format dotenv` works |
| `TestCLIImportSecret` | `main(["import-secret", ...])` validates and stores |

### Manual Verification

After implementation, run these from a terminal:

1. **Setup flow:**
   ```bash
   omniclaw setup --api-key <your-test-key>
   # Verify: .env created, recovery file in config dir, managed store updated
   omniclaw doctor
   # Verify: all items show [OK]
   ```

2. **Backup info:**
   ```bash
   omniclaw backup-info
   # Verify: paths printed, [FOUND]/[MISSING] correct
   omniclaw backup-info --json
   # Verify: valid JSON output
   ```

3. **Export:**
   ```bash
   omniclaw export-env
   # Verify: export lines printed to stdout
   omniclaw export-env --format dotenv --output /tmp/test.env
   # Verify: file written with VAR=value lines
   ```

4. **Import:**
   ```bash
   omniclaw import-secret --api-key <key> --entity-secret <64-hex>
   # Verify: omniclaw doctor now shows managed secret
   ```
