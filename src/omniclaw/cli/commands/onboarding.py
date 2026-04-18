from __future__ import annotations

import os

import typer


def doctor_cmd(
    api_key: str | None = typer.Option(None, "--api-key", help="Override CIRCLE_API_KEY"),
    entity_secret: str | None = typer.Option(None, "--entity-secret", help="Override ENTITY_SECRET"),
    as_json: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Inspect OmniClaw setup, managed credentials, and recovery state."""
    from omniclaw.onboarding import print_doctor_status

    print_doctor_status(api_key=api_key, entity_secret=entity_secret, as_json=as_json)


def backup_info_cmd(
    as_json: bool = typer.Option(False, "--json", help="Output machine-readable JSON"),
) -> None:
    """Show location and status of backup-critical files."""
    from omniclaw.onboarding import print_backup_info

    print_backup_info(as_json=as_json)


def export_env_cmd(
    fmt: str = typer.Option("shell", "--format", help="Output format: shell or dotenv"),
    output: str | None = typer.Option(None, "--output", help="Write to file instead of stdout"),
    force: bool = typer.Option(False, "--force", help="Overwrite output file if it exists"),
    api_key: str | None = typer.Option(None, "--api-key", help="Override CIRCLE_API_KEY"),
) -> None:
    """Print active credentials as shell export statements or dotenv format."""
    from omniclaw.onboarding import run_export_env_cli

    code = run_export_env_cli(api_key=api_key, fmt=fmt, output=output, force=force)
    if code != 0:
        raise typer.Exit(code)


def import_secret_cmd(
    entity_secret: str = typer.Option(..., "--entity-secret", help="64-char hex entity secret"),
    api_key: str | None = typer.Option(None, "--api-key", help="Override CIRCLE_API_KEY"),
    recovery_file: str | None = typer.Option(None, "--recovery-file", help="Path to recovery file"),
) -> None:
    """Import an existing entity secret into the managed config store."""
    from omniclaw.onboarding import run_import_secret_cli

    resolved_api_key = api_key or os.getenv("CIRCLE_API_KEY")
    if not resolved_api_key:
        typer.echo(
            "Error: Circle API key is required.\n"
            "Pass --api-key or set the CIRCLE_API_KEY environment variable.",
            err=True,
        )
        raise typer.Exit(1)

    code = run_import_secret_cli(
        api_key=resolved_api_key,
        entity_secret=entity_secret,
        recovery_file=recovery_file,
    )
    if code != 0:
        raise typer.Exit(code)


def register(app: typer.Typer) -> None:
    """Register onboarding commands on the main Typer app."""
    app.command("doctor")(doctor_cmd)
    app.command("backup-info")(backup_info_cmd)
    app.command("export-env")(export_env_cmd)
    app.command("import-secret")(import_secret_cmd)
