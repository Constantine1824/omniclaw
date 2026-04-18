"""Unit tests for setup module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from omniclaw.onboarding import (
    SetupError,
    backup_info,
    create_env_file,
    doctor,
    generate_entity_secret,
    load_managed_entity_secret,
    print_backup_info,
    print_doctor_status,
    run_export_env_cli,
    run_import_secret_cli,
    store_managed_credentials,
    verify_setup,
)


def _isolated_env(tmpdir: str) -> dict[str, str]:
    """Return a clean env dict that avoids 'Could not determine home directory' on Windows."""
    xdg = str(Path(tmpdir) / "xdg")
    env: dict[str, str] = {"XDG_CONFIG_HOME": xdg}
    if os.name == "nt":
        env["APPDATA"] = str(Path(tmpdir) / "appdata")
        env["USERPROFILE"] = tmpdir
    return env


class TestGenerateEntitySecret:
    """Tests for generate_entity_secret()."""

    def test_generates_64_char_hex(self) -> None:
        """Test secret is 64 hex characters."""
        secret = generate_entity_secret()

        assert len(secret) == 64
        # Verify it's valid hex
        int(secret, 16)

    def test_generates_unique_secrets(self) -> None:
        """Test each call generates a unique secret."""
        secrets = [generate_entity_secret() for _ in range(10)]

        assert len(set(secrets)) == 10  # All unique


class TestCreateEnvFile:
    """Tests for create_env_file()."""

    def test_creates_env_file(self) -> None:
        """Test .env file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            result = create_env_file(
                api_key="TEST_API_KEY",
                entity_secret="a" * 64,
                env_path=env_path,
            )

            assert result.exists()
            content = result.read_text()
            assert "CIRCLE_API_KEY=TEST_API_KEY" in content
            assert f"ENTITY_SECRET={'a' * 64}" in content
            if os.name != "nt":
                mode = result.stat().st_mode & 0o777
                assert mode == 0o600

    def test_raises_if_exists_no_overwrite(self) -> None:
        """Test error if file exists and overwrite=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("existing")

            with pytest.raises(SetupError, match="already exists"):
                create_env_file(
                    api_key="key",
                    entity_secret="a" * 64,
                    env_path=env_path,
                    overwrite=False,
                )

    def test_overwrites_if_flag_set(self) -> None:
        """Test overwrite works when flag is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("old content")

            result = create_env_file(
                api_key="NEW_KEY",
                entity_secret="b" * 64,
                env_path=env_path,
                overwrite=True,
            )

            content = result.read_text()
            assert "CIRCLE_API_KEY=NEW_KEY" in content

    def test_includes_network_config(self) -> None:
        """Test network is included in .env."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            create_env_file(
                api_key="key",
                entity_secret="a" * 64,
                env_path=env_path,
                network="ARC",
            )

            content = env_path.read_text()
            assert "OMNICLAW_NETWORK=ARC" in content


class TestVerifySetup:
    """Tests for verify_setup()."""

    def test_returns_status_dict(self) -> None:
        """Test verify_setup returns expected keys."""
        result = verify_setup()

        assert "circle_sdk_installed" in result
        assert "api_key_set" in result
        assert "entity_secret_set" in result
        assert "ready" in result

    def test_detects_missing_env_vars(self) -> None:
        """Test detection when env vars not set."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            result = verify_setup()

            assert result["api_key_set"] is False
            assert result["entity_secret_set"] is False
            assert result["ready"] is False

    def test_detects_set_env_vars(self) -> None:
        """Test detection when env vars are set."""
        env = {
            "CIRCLE_API_KEY": "test_key",
            "ENTITY_SECRET": "test_secret",
        }

        with patch.dict(os.environ, env):
            result = verify_setup()

            assert result["api_key_set"] is True
            assert result["entity_secret_set"] is True


class TestManagedCredentials:
    """Tests for managed config credentials."""

    def test_create_env_file_stores_managed_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"

            with patch.dict(os.environ, _isolated_env(tmpdir), clear=True):
                create_env_file(
                    api_key="TEST_API_KEY",
                    entity_secret="a" * 64,
                    env_path=env_path,
                )

                assert load_managed_entity_secret("TEST_API_KEY") == "a" * 64

    def test_store_and_load_managed_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            store_managed_credentials(
                "TEST_API_KEY",
                "b" * 64,
                source="test",
            )

            assert load_managed_entity_secret("TEST_API_KEY") == "b" * 64

    def test_doctor_reports_managed_secret_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**_isolated_env(tmpdir), "CIRCLE_API_KEY": "TEST_API_KEY"}

            with patch.dict(os.environ, env, clear=True):
                store_managed_credentials(
                    "TEST_API_KEY",
                    "c" * 64,
                    source="test",
                )
                status = doctor()

                assert status["managed_entity_secret_set"] is True
                assert status["active_entity_secret_source"] == "managed_config"

    def test_print_doctor_status_json(self, capsys) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**_isolated_env(tmpdir), "CIRCLE_API_KEY": "TEST_API_KEY"}
            with patch.dict(os.environ, env, clear=True):
                print_doctor_status(as_json=True)
                output = capsys.readouterr().out
                data = json.loads(output)
                assert "ready" in data
                assert "config_dir" in data


# ---------------------------------------------------------------------------
# New test classes for CLI onboarding & recovery commands (spec 002)
# ---------------------------------------------------------------------------


class TestBackupInfo:
    """Tests for backup_info() and print_backup_info()."""

    def test_returns_expected_keys(self) -> None:
        """backup_info() dict has every documented key."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            info = backup_info()

        expected_keys = {
            "config_dir",
            "managed_credentials_path",
            "managed_credentials_exists",
            "recovery_file_path",
            "recovery_file_exists",
            "recovery_file_permissions",
            "env_file_path",
            "env_file_exists",
            "warnings",
        }
        assert expected_keys.issubset(info.keys())

    def test_warns_when_no_credentials(self) -> None:
        """Warning surfaced when managed credentials are missing."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            info = backup_info()

        assert any("managed credentials" in w.lower() for w in info["warnings"])

    def test_warns_when_no_recovery_file(self) -> None:
        """Warning surfaced when recovery file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            info = backup_info()

        assert any("recovery file" in w.lower() for w in info["warnings"])

    def test_credentials_found_when_present(self) -> None:
        """managed_credentials_exists is True after store_managed_credentials()."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            store_managed_credentials("TEST_KEY", "a" * 64, source="test")
            info = backup_info()

        assert info["managed_credentials_exists"] is True

    def test_print_backup_info_json(self, capsys) -> None:
        """--json flag produces valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            print_backup_info(as_json=True)

        output = capsys.readouterr().out
        data = json.loads(output)
        assert "config_dir" in data
        assert isinstance(data["warnings"], list)

    def test_print_backup_info_human(self, capsys) -> None:
        """Human-readable output includes expected labels."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            print_backup_info(as_json=False)

        output = capsys.readouterr().out
        assert "OmniClaw Backup Info" in output
        assert "Config directory:" in output
        assert "Recommended actions:" in output


class TestExportCredentials:
    """Tests for run_export_env_cli()."""

    def test_fails_without_api_key(self, capsys) -> None:
        """Exit 1 when no API key is available."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            code = run_export_env_cli(api_key=None)

        assert code == 1
        assert "API key" in capsys.readouterr().err

    def test_fails_without_entity_secret(self, capsys) -> None:
        """Exit 1 when API key exists but no entity secret anywhere."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {**_isolated_env(tmpdir), "CIRCLE_API_KEY": "test_key"}
            with patch.dict(os.environ, env, clear=True):
                code = run_export_env_cli(api_key="test_key")

        assert code == 1
        assert "entity secret" in capsys.readouterr().err.lower()

    def test_shell_format_output(self, capsys) -> None:
        """Shell format produces export statements."""
        env = {
            "CIRCLE_API_KEY": "test_key",
            "ENTITY_SECRET": "a" * 64,
        }
        with patch.dict(os.environ, env):
            code = run_export_env_cli(api_key="test_key", fmt="shell")

        assert code == 0
        stdout = capsys.readouterr().out
        assert 'export CIRCLE_API_KEY="test_key"' in stdout
        assert f'export ENTITY_SECRET="{"a" * 64}"' in stdout

    def test_dotenv_format_output(self, capsys) -> None:
        """Dotenv format produces VAR=value lines."""
        env = {
            "CIRCLE_API_KEY": "test_key",
            "ENTITY_SECRET": "b" * 64,
        }
        with patch.dict(os.environ, env):
            code = run_export_env_cli(api_key="test_key", fmt="dotenv")

        assert code == 0
        stdout = capsys.readouterr().out
        assert "CIRCLE_API_KEY=test_key" in stdout
        assert "export" not in stdout

    def test_writes_to_file(self) -> None:
        """--output writes to file instead of stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "creds.env"
            env = {
                "CIRCLE_API_KEY": "test_key",
                "ENTITY_SECRET": "c" * 64,
            }
            with patch.dict(os.environ, env):
                code = run_export_env_cli(
                    api_key="test_key",
                    fmt="dotenv",
                    output=str(out_path),
                )

            assert code == 0
            assert out_path.exists()
            content = out_path.read_text()
            assert "CIRCLE_API_KEY=test_key" in content

    def test_refuses_overwrite_without_force(self) -> None:
        """Exit 1 when output file exists and --force not set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "creds.env"
            out_path.write_text("existing")
            env = {
                "CIRCLE_API_KEY": "test_key",
                "ENTITY_SECRET": "d" * 64,
            }
            with patch.dict(os.environ, env):
                code = run_export_env_cli(
                    api_key="test_key",
                    output=str(out_path),
                    force=False,
                )

            assert code == 1

    def test_overwrites_with_force(self) -> None:
        """--force allows overwriting existing output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "creds.env"
            out_path.write_text("old")
            env = {
                "CIRCLE_API_KEY": "test_key",
                "ENTITY_SECRET": "e" * 64,
            }
            with patch.dict(os.environ, env):
                code = run_export_env_cli(
                    api_key="test_key",
                    fmt="dotenv",
                    output=str(out_path),
                    force=True,
                )

            assert code == 0
            assert "CIRCLE_API_KEY=test_key" in out_path.read_text()


class TestImportEntitySecret:
    """Tests for run_import_secret_cli()."""

    def test_rejects_short_secret(self, capsys) -> None:
        """Exit 1 for secrets shorter than 64 chars."""
        code = run_import_secret_cli(api_key="key", entity_secret="abc123")
        assert code == 1
        assert "64 hex characters" in capsys.readouterr().err

    def test_rejects_non_hex_secret(self, capsys) -> None:
        """Exit 1 for 64-char non-hex strings."""
        bad_secret = "g" * 64  # 'g' is not valid hex
        code = run_import_secret_cli(api_key="key", entity_secret=bad_secret)
        assert code == 1
        assert "hexadecimal" in capsys.readouterr().err

    def test_rejects_missing_recovery_file(self, capsys) -> None:
        """Exit 1 when --recovery-file points to a nonexistent path."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            code = run_import_secret_cli(
                api_key="key",
                entity_secret="a" * 64,
                recovery_file="/nonexistent/recovery.dat",
            )
        assert code == 1
        assert "not found" in capsys.readouterr().err.lower()

    def test_stores_valid_secret(self, capsys) -> None:
        """Exit 0 and secret is stored for valid input."""
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ, _isolated_env(tmpdir), clear=True
        ):
            code = run_import_secret_cli(
                api_key="TEST_KEY",
                entity_secret="a" * 64,
            )

            assert code == 0
            assert load_managed_entity_secret("TEST_KEY") == "a" * 64

        output = capsys.readouterr().out
        assert "imported successfully" in output.lower()

    def test_stores_with_recovery_file(self, capsys) -> None:
        """Recovery file path is accepted when file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recovery = Path(tmpdir) / "recovery.dat"
            recovery.write_text("recovery_data")

            with patch.dict(os.environ, _isolated_env(tmpdir), clear=True):
                code = run_import_secret_cli(
                    api_key="TEST_KEY",
                    entity_secret="b" * 64,
                    recovery_file=str(recovery),
                )

            assert code == 0
            output = capsys.readouterr().out
            assert "recovery" in output.lower()
