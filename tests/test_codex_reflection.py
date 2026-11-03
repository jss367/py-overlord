"""Subscription auth, subprocess isolation, usage accounting, and failures."""

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from dominion.simulation.codex_reflection import CodexReflection


def test_codex_uses_subscription_stdin_and_reports_usage(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-forward")
    monkeypatch.setenv("CODEX_API_KEY", "other-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid")
    monkeypatch.setattr("shutil.which", lambda _: "/test/codex")
    requests = []

    def run(command, **kwargs):
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert "CODEX_API_KEY" not in kwargs["env"]
        assert "OPENAI_BASE_URL" not in kwargs["env"]
        if command[1:] == ["login", "status"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using ChatGPT")
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="codex-cli test", stderr="")
        requests.append((command, kwargs))
        assert Path(command[command.index("--cd") + 1]).is_dir()
        assert not list(Path(command[command.index("--cd") + 1]).iterdir())
        Path(command[command.index("--output-last-message") + 1]).write_text('{"plan": "test"}')
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "type": "turn.completed", "usage": {
                "input_tokens": 123, "output_tokens": 45, "cached_input_tokens": 10,
            },
        }))

    monkeypatch.setattr(subprocess, "run", run)
    lm = CodexReflection(tmp_path / "requests")
    assert lm("Feedback with $() and `literal` characters") == '{"plan": "test"}'
    command, kwargs = requests[0]
    assert command[-1] == "-"
    assert '--ignore-user-config' in command and '--ephemeral' in command
    assert 'forced_login_method="chatgpt"' in command
    assert 'web_search="disabled"' in command
    assert 'shell_tool' in command and 'apps' in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "Feedback with $() and `literal` characters" in kwargs["input"]
    assert "shell" not in kwargs
    assert os.environ["OPENAI_API_KEY"] == "test-key-never-forward"
    assert lm.calls == 1 and lm.total_tokens_in == 123 and lm.total_tokens_out == 45
    assert lm.cached_tokens_in == 10
    assert lm.version == "codex-cli test"
    assert lm.usage_reported
    assert (tmp_path / "requests/request-001/events.jsonl").exists()


def test_api_login_is_rejected_before_generation(tmp_path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/test/codex")
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: SimpleNamespace(
        returncode=0, stdout="", stderr="Logged in using an API key",
    ))
    with pytest.raises(RuntimeError, match="signed in with ChatGPT"):
        CodexReflection(tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("failure", ["timeout", "exit", "no_response"])
def test_cli_failures_are_not_reflections(tmp_path, monkeypatch, failure):
    monkeypatch.setattr("shutil.which", lambda _: "/test/codex")

    def run(command, **kwargs):
        if command[1:] == ["login", "status"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using ChatGPT")
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="codex-cli test", stderr="")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 10)
        return SimpleNamespace(returncode=1 if failure == "exit" else 0,
                               stdout="", stderr="fixture failure")

    monkeypatch.setattr(subprocess, "run", run)
    lm = CodexReflection(tmp_path)
    with pytest.raises(RuntimeError, match="timed out|failed"):
        lm("Task")
    assert (tmp_path / "request-001/metadata.json").exists()
