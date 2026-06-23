"""Unit tests for scan_secrets.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

# Import from the scripts directory
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scan_secrets import (
    Finding,
    collect_files,
    get_staged_files,
    redact,
    scan_file,
    should_skip,
    PATTERNS,
)


# --- Pattern detection tests ---


class TestAWSPatterns:
    """Test detection of AWS-specific credential patterns."""

    def test_detects_aws_access_key_id(self, tmp_path: Path) -> None:
        f = tmp_path / "config.py"
        f.write_text('AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "AWS Access Key ID"
        assert "AKIA" in findings[0].context
        assert "AKIAIOSFODNN7EXAMPLE" not in findings[0].context  # redacted

    def test_detects_aws_secret_access_key(self, tmp_path: Path) -> None:
        f = tmp_path / "creds.env"
        f.write_text('aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "AWS Secret Access Key"

    def test_detects_aws_session_token(self, tmp_path: Path) -> None:
        # Session tokens are very long base64 strings
        token = "A" * 120
        f = tmp_path / "session.env"
        f.write_text(f'aws_session_token = "{token}"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "AWS Session Token"

    def test_detects_aws_mws_key(self, tmp_path: Path) -> None:
        f = tmp_path / "mws.py"
        f.write_text('MWS_KEY = "amzn.mws.4ea38b7b-f563-7709-4bae-87aea0000000"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "AWS MWS Key"

    def test_does_not_flag_partial_akia(self, tmp_path: Path) -> None:
        """AKIA must be followed by exactly 16 uppercase alphanumeric chars."""
        f = tmp_path / "code.py"
        f.write_text('x = "AKIA_short"\n')  # too short
        findings = scan_file(f)
        assert len(findings) == 0


class TestGenericTokenPatterns:
    """Test detection of non-AWS tokens and keys."""

    def test_detects_github_token(self, tmp_path: Path) -> None:
        f = tmp_path / "ci.yml"
        f.write_text('token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "GitHub Token"

    def test_detects_gitlab_token(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "GitLab Token"

    def test_detects_slack_token(self, tmp_path: Path) -> None:
        f = tmp_path / "bot.py"
        # Construct token at runtime to avoid triggering GitHub push protection
        token = "xoxb" + "-123456789012-1234567890123-AbCdEfGhIjKlMnOpQrStUv"
        f.write_text(f'SLACK_TOKEN = "{token}"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Slack Token"

    def test_detects_openai_api_key(self, tmp_path: Path) -> None:
        f = tmp_path / "llm.py"
        f.write_text('OPENAI_KEY = "sk-proj1234567890abcdefghij"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "OpenAI API Key"

    def test_detects_anthropic_api_key(self, tmp_path: Path) -> None:
        f = tmp_path / "config.toml"
        f.write_text('api_key = "sk-ant-api03-abcdefghijklmnopqrst"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Anthropic API Key"


class TestPrivateKeys:
    """Test detection of private key material."""

    def test_detects_rsa_private_key(self, tmp_path: Path) -> None:
        f = tmp_path / "key.pem"
        f.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Private Key"

    def test_detects_ec_private_key(self, tmp_path: Path) -> None:
        f = tmp_path / "ec.pem"
        f.write_text("-----BEGIN EC PRIVATE KEY-----\nMHQC...\n-----END EC PRIVATE KEY-----\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Private Key"

    def test_detects_openssh_private_key(self, tmp_path: Path) -> None:
        f = tmp_path / "id_ed25519"
        f.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nb3Blb...\n-----END OPENSSH PRIVATE KEY-----\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Private Key"


class TestConnectionStrings:
    """Test detection of connection strings with embedded passwords."""

    def test_detects_postgres_connection_string(self, tmp_path: Path) -> None:
        f = tmp_path / "db.py"
        f.write_text('DATABASE_URL = "postgres://admin:s3cret_pass@db.example.com:5432/mydb"\n')
        findings = scan_file(f)
        assert any(finding.pattern == "Connection String with Password" for finding in findings)

    def test_detects_mysql_connection_string(self, tmp_path: Path) -> None:
        f = tmp_path / "app.conf"
        f.write_text('url = "mysql://root:hunter2@localhost:3306/app"\n')
        findings = scan_file(f)
        assert any(finding.pattern == "Connection String with Password" for finding in findings)

    def test_detects_mongodb_connection_string(self, tmp_path: Path) -> None:
        f = tmp_path / "mongo.env"
        f.write_text('MONGO_URI=mongodb://user:password123@cluster0.example.net:27017/db\n')
        findings = scan_file(f)
        assert any(finding.pattern == "Connection String with Password" for finding in findings)


class TestPasswordAssignments:
    """Test detection of hard-coded passwords in source."""

    def test_detects_password_assignment(self, tmp_path: Path) -> None:
        f = tmp_path / "config.py"
        f.write_text('DB_PASSWORD = "super_secret_password_123"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Password Assignment"

    def test_detects_api_key_assignment(self, tmp_path: Path) -> None:
        f = tmp_path / "settings.py"
        f.write_text('api_key: "abcdef1234567890abcdef"\n')
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Password Assignment"

    def test_ignores_short_values(self, tmp_path: Path) -> None:
        """Values under 8 characters are likely placeholders."""
        f = tmp_path / "config.py"
        f.write_text('password = "short"\n')
        findings = scan_file(f)
        assert len(findings) == 0


class TestEnvSecretAssignment:
    """Test detection of exported env secrets."""

    def test_detects_exported_secret_key(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("export SECRET_KEY=django-insecure-abc123def456\n")
        findings = scan_file(f)
        assert len(findings) == 1
        assert findings[0].pattern == "Env Secret Assignment"

    def test_detects_database_url(self, tmp_path: Path) -> None:
        f = tmp_path / ".env"
        f.write_text("DATABASE_URL=postgres://user:pass@host/db\n")
        findings = scan_file(f)
        # Could match both Env Secret Assignment and Connection String
        assert len(findings) >= 1


# --- Skip logic tests ---


class TestShouldSkip:
    """Test file and directory skip logic."""

    def test_skips_binary_extensions(self) -> None:
        assert should_skip(Path("image.png")) is True
        assert should_skip(Path("archive.zip")) is True
        assert should_skip(Path("lib.dll")) is True
        assert should_skip(Path("styles.woff2")) is True

    def test_skips_lock_files(self) -> None:
        assert should_skip(Path("package-lock.json.lock")) is True

    def test_skips_known_directories(self) -> None:
        assert should_skip(Path("node_modules/package/index.js")) is True
        assert should_skip(Path(".git/config")) is True
        assert should_skip(Path("__pycache__/module.cpython-311.pyc")) is True
        assert should_skip(Path(".venv/lib/site-packages/pkg.py")) is True

    def test_does_not_skip_normal_source(self) -> None:
        assert should_skip(Path("src/main.py")) is False
        assert should_skip(Path("config.yaml")) is False
        assert should_skip(Path(".env")) is False
        assert should_skip(Path("Dockerfile")) is False


# --- Redaction tests ---


class TestRedact:
    """Test that secrets are properly redacted in output."""

    def test_redacts_long_secrets(self) -> None:
        import re
        line = 'key = "AKIAIOSFODNN7EXAMPLE"'
        pattern = re.compile(r"AKIA[0-9A-Z]{16}")
        match = pattern.search(line)
        result = redact(line, match)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "AKIA" in result  # First 4 chars visible

    def test_redacts_short_secrets(self) -> None:
        """Secrets of 8 chars or fewer are fully redacted (no visible prefix)."""
        import re
        line = "token=abcd1234"
        pattern = re.compile(r"abcd1234")
        match = pattern.search(line)
        result = redact(line, match)
        assert "abcd1234" not in result
        assert result == "token=********"


# --- Comment skipping tests ---


class TestCommentSkipping:
    """Test that example/placeholder comments are skipped."""

    def test_skips_example_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "readme.py"
        f.write_text('# Example: AKIAIOSFODNN7EXAMPLE\n')
        findings = scan_file(f)
        assert len(findings) == 0

    def test_skips_placeholder_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "config.py"
        f.write_text('# Placeholder: sk-projXXXXXXXXXXXXXXXXXXXX\n')
        findings = scan_file(f)
        assert len(findings) == 0

    def test_does_not_skip_non_example_comments(self, tmp_path: Path) -> None:
        f = tmp_path / "config.py"
        f.write_text('# Production config\nAWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        findings = scan_file(f)
        assert len(findings) == 1


# --- File collection tests ---


class TestCollectFiles:
    """Test recursive file collection."""

    def test_collects_source_files(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "src" / "util.py").write_text("x = 1")
        files = collect_files(tmp_path)
        assert len(files) == 2

    def test_skips_excluded_directories(self, tmp_path: Path) -> None:
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "pkg.js").write_text("module.exports = {}")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.js").write_text("const x = 1;")
        files = collect_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "app.js"

    def test_skips_binary_files(self, tmp_path: Path) -> None:
        (tmp_path / "logo.png").write_bytes(b"\x89PNG")
        (tmp_path / "code.py").write_text("x = 1")
        files = collect_files(tmp_path)
        assert len(files) == 1
        assert files[0].name == "code.py"


# --- Staged files tests ---


class TestGetStagedFiles:
    """Test git staged file retrieval."""

    @patch("scan_secrets.subprocess.run")
    def test_returns_staged_files(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="file1.py\nfile2.py\n", stderr=""
        )
        result = get_staged_files()
        assert result == ["file1.py", "file2.py"]

    @patch("scan_secrets.subprocess.run")
    def test_returns_empty_on_no_staged(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = get_staged_files()
        assert result == []

    @patch("scan_secrets.subprocess.run")
    def test_returns_empty_on_git_error(self, mock_run) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        result = get_staged_files()
        assert result == []

    @patch("scan_secrets.subprocess.run")
    def test_returns_empty_when_git_not_found(self, mock_run) -> None:
        mock_run.side_effect = FileNotFoundError()
        result = get_staged_files()
        assert result == []


# --- Integration-style tests ---


class TestScanFileIntegration:
    """End-to-end tests scanning realistic file content."""

    def test_multi_secret_file(self, tmp_path: Path) -> None:
        """A file with multiple different secrets should report each."""
        content = """
import boto3

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
GITHUB_TOKEN = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
"""
        f = tmp_path / "secrets.py"
        f.write_text(content)
        findings = scan_file(f)
        patterns_found = {finding.pattern for finding in findings}
        assert "AWS Access Key ID" in patterns_found
        assert "AWS Secret Access Key" in patterns_found
        assert "GitHub Token" in patterns_found

    def test_clean_file_has_no_findings(self, tmp_path: Path) -> None:
        """Normal source code should not trigger false positives."""
        content = """
import os
from pathlib import Path

def get_config():
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432")),
        "name": os.environ.get("DB_NAME", "myapp"),
    }

if __name__ == "__main__":
    config = get_config()
    print(f"Connecting to {config['host']}:{config['port']}")
"""
        f = tmp_path / "clean.py"
        f.write_text(content)
        findings = scan_file(f)
        assert len(findings) == 0

    def test_unreadable_file_returns_empty(self, tmp_path: Path) -> None:
        """Files that can't be read should be handled gracefully."""
        f = tmp_path / "nope.py"
        f.write_text("secret = 'x'")
        f.chmod(0o000)
        try:
            findings = scan_file(f)
            # On some systems this may still be readable by owner
            # The important thing is it doesn't raise
            assert isinstance(findings, list)
        finally:
            f.chmod(0o644)  # restore for cleanup
