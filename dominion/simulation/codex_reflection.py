"""GEPA reflection through the subscription-authenticated Codex CLI.

The CLI runs in an empty, read-only working directory with the entire task on
stdin. Saved ChatGPT authentication stays with Codex; no OAuth tokens are read
or copied by this adapter.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time


def subscription_environment():
    """Remove API credentials/routing only in the child, preserving user state."""
    excluded = {
        "OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY", "CODEX_ACCESS_TOKEN",
        "OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_ORG_ID", "OPENAI_ORGANIZATION",
        "OPENAI_PROJECT_ID", "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN",
    }
    return {key: value for key, value in os.environ.items()
            if key not in excluded and not key.endswith("_API_KEY")}


class CodexReflection:
    """A GEPA LM callable with persisted responses and subscription token usage."""

    # GEPA expects a numeric estimate. Public reports use null for API dollars
    # because subscription usage is not an API billing estimate.
    total_cost = 0.0

    def __init__(self, log_dir: Path, *, model=None, timeout=300, executable="codex"):
        self.executable = shutil.which(executable)
        if self.executable is None:
            raise RuntimeError("Codex CLI not found; install it and run codex login with ChatGPT")
        if timeout <= 0:
            raise ValueError("Reflection timeout must be positive")
        self.log_dir = Path(log_dir).resolve()
        self.model = model
        self.timeout = timeout
        self.calls = 0
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.cached_tokens_in = 0
        self.usage_reported = False
        self.env = subscription_environment()
        status = subprocess.run(
            [self.executable, "login", "status"], env=self.env,
            capture_output=True, text=True, timeout=30,
        )
        if status.returncode or "logged in using chatgpt" not in (status.stdout + status.stderr).lower():
            raise RuntimeError("Codex CLI must be signed in with ChatGPT; run codex login first")
        version = subprocess.run([self.executable, "--version"], env=self.env,
                                 capture_output=True, text=True, timeout=30)
        if version.returncode:
            raise RuntimeError("Could not identify the Codex CLI version")
        self.version = version.stdout.strip()

    def __call__(self, prompt):
        if not isinstance(prompt, str):
            raise ValueError("Codex reflection expects a text prompt")
        self.calls += 1
        folder = self.log_dir / f"request-{self.calls:03d}"
        folder.mkdir(parents=True, exist_ok=False)
        response_path = folder / "response.txt"
        instructions = (
            "You are the reflection model for a bounded Dominion strategy optimization experiment. "
            "All information needed is in the prompt below. Do not inspect files, invoke tools, "
            "run commands, or delegate work. Propose a strategy using only the supplied game "
            "feedback and supported schema. Return only the complete strategy JSON object; "
            "no explanation, no prose instructions, and no additional fields.\n\n"
        ) + prompt
        (folder / "prompt.txt").write_text(instructions)
        started = time.monotonic()
        with TemporaryDirectory(prefix="dominion-reflection-") as work_dir:
            command = [
                self.executable, "exec", "--ignore-user-config", "--ephemeral",
                "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
                "--disable", "shell_tool", "--disable", "apps",
                "--json", "-c", 'forced_login_method="chatgpt"',
                "-c", 'approval_policy="never"', "-c", 'web_search="disabled"', "--cd", work_dir,
                "--output-last-message", str(response_path),
            ]
            if self.model:
                command.extend(["--model", self.model])
            command.append("-")
            try:
                result = subprocess.run(
                    command, input=instructions, env=self.env, capture_output=True,
                    text=True, timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as exc:
                for filename, partial in (("events.jsonl", exc.stdout), ("stderr.txt", exc.stderr)):
                    if isinstance(partial, bytes):
                        partial = partial.decode(errors="replace")
                    (folder / filename).write_text(partial or "")
                (folder / "metadata.json").write_text(json.dumps({
                    "status": "timeout", "elapsed_seconds": time.monotonic() - started,
                }, indent=2))
                raise RuntimeError(f"Codex reflection timed out; see {folder}") from exc
        (folder / "events.jsonl").write_text(result.stdout)
        (folder / "stderr.txt").write_text(result.stderr)
        usage = {}
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") in {"turn.completed", "thread.completed"}:
                self.usage_reported = True
                for key, value in (event.get("usage") or {}).items():
                    if isinstance(value, int):
                        usage[key] = usage.get(key, 0) + value
        self.total_tokens_in += usage.get("input_tokens", 0)
        self.total_tokens_out += usage.get("output_tokens", 0)
        self.cached_tokens_in += usage.get("cached_input_tokens", 0)
        (folder / "metadata.json").write_text(json.dumps({
            "returncode": result.returncode, "usage": usage,
            "elapsed_seconds": time.monotonic() - started,
            "billing_mode": "chatgpt_subscription", "model_override": self.model,
            "cli_version": self.version,
        }, indent=2))
        if result.returncode or not response_path.exists() or not response_path.read_text().strip():
            raise RuntimeError(f"Codex reflection failed; see {folder / 'stderr.txt'}")
        return response_path.read_text().strip()
