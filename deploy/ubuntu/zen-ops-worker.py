#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTROL_REPO = Path("/var/lib/zen-ops/control.git")
STATE_DIR = Path("/var/lib/zen-ops")
PUBLIC_DIR = STATE_DIR / "public"
JOBS_DIR = STATE_DIR / "jobs"
STATE_FILE = STATE_DIR / "worker-state.json"
REMOTE = "https://github.com/zen0904/ZEN-MA2-Agent.git"
CONTROL_REF = "refs/remotes/origin/zen-ops-control"
JOB_PATH = "ops/job.json"
POLL_SECONDS = 10
JOB_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,96}$")
SAFE_CWDS = ("/opt/zen", "/var/lib/zen-ops", "/tmp")
BLOCKED_TEXT = (
    "/etc/shadow",
    "/root/.ssh",
    "/root/.openclaw",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "api_key",
    "password=",
    "token=",
)
ALLOWED_SERVICES = {
    "zen-show-controller",
    "zen-controller-readonly-facade",
    "zen-lighting-operator-proxy",
    "zen-glances",
    "zen-sentinel",
    "zen-meshcentral",
    "zen-ops-results",
    "ssh",
    "tailscaled",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(
    argv: list[str],
    *,
    cwd: str | None = None,
    timeout: int = 120,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        env={
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/node/bin",
            "LANG": "C.UTF-8",
        },
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def sanitize(text: str, limit: int = 200_000) -> str:
    text = text[:limit]
    for line in text.splitlines():
        low = line.lower()
        if any(marker.lower() in low for marker in BLOCKED_TEXT):
            text = text.replace(line, "[REDACTED]")
    return text


def ensure_control_repo() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONTROL_REPO.exists():
        run(["git", "init", "--bare", str(CONTROL_REPO)], timeout=30)
        run(["git", "-C", str(CONTROL_REPO), "remote", "add", "origin", REMOTE], timeout=30)


def fetch_control_ref() -> bool:
    proc = run(
        [
            "git", "-C", str(CONTROL_REPO), "fetch", "--quiet", "--force", "--depth=1",
            "origin", "refs/heads/zen-ops-control:" + CONTROL_REF,
        ],
        timeout=60,
    )
    return proc.returncode == 0


def read_control_job() -> dict[str, Any] | None:
    proc = run(
        ["git", "-C", str(CONTROL_REPO), "show", f"{CONTROL_REF}:{JOB_PATH}"],
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def load_state() -> dict[str, Any]:
    try:
        data = json.loads(STATE_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def validate_job(job: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    if job.get("schema") != "zen.ops.job.v1":
        raise ValueError("unsupported schema")
    job_id = str(job.get("job_id", ""))
    if not JOB_ID_RE.fullmatch(job_id):
        raise ValueError("invalid job_id")
    kind = str(job.get("kind", ""))
    args = job.get("args", {})
    if not isinstance(args, dict):
        raise ValueError("args must be an object")
    return job_id, kind, args


def safe_cwd(value: Any) -> str:
    cwd = str(value or "/opt/zen")
    resolved = str(Path(cwd).resolve())
    if not any(resolved == base or resolved.startswith(base + "/") for base in SAFE_CWDS):
        raise ValueError("cwd is outside the allowed Mini work roots")
    return resolved


def execute(job_id: str, kind: str, args: dict[str, Any]) -> dict[str, Any]:
    timeout = max(1, min(int(args.get("timeout", 1800)), 7200))
    started = now()

    if kind == "shell":
        command = str(args.get("command", "")).strip()
        if not command:
            raise ValueError("shell command is empty")
        if any(marker.lower() in command.lower() for marker in BLOCKED_TEXT):
            raise ValueError("shell command references a blocked secret-bearing target")
        cwd = safe_cwd(args.get("cwd"))
        proc = run(
            [
                "runuser", "-u", "zenops", "--",
                "/bin/bash", "-lc", command,
            ],
            cwd=cwd,
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "service":
        action = str(args.get("action", "status"))
        service = str(args.get("service", ""))
        if service not in ALLOWED_SERVICES:
            raise ValueError("service is not allowlisted")
        if action not in {"status", "restart", "start", "stop"}:
            raise ValueError("service action is not allowlisted")
        argv = ["systemctl", action, service]
        if action == "status":
            argv += ["--no-pager", "--full"]
        proc = run(argv, timeout=min(timeout, 120))
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "apt_install":
        packages = args.get("packages", [])
        if not isinstance(packages, list) or not packages:
            raise ValueError("packages must be a non-empty list")
        clean = []
        for item in packages:
            name = str(item)
            if not re.fullmatch(r"[A-Za-z0-9.+:-]{1,120}", name):
                raise ValueError(f"invalid package name: {name}")
            clean.append(name)
        proc = run(
            ["apt-get", "install", "-y", "--no-install-recommends", *clean],
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "repo_sync":
        repo = "/opt/zen/ZEN-MA2-Agent"
        fetch = run(["git", "-C", repo, "fetch", "origin", "main"], timeout=120)
        if fetch.returncode != 0:
            return {
                "returncode": fetch.returncode,
                "output": sanitize(fetch.stdout),
                "started_at": started,
                "finished_at": now(),
            }
        proc = run(["git", "-C", repo, "merge", "--ff-only", "origin/main"], timeout=120)
        return {
            "returncode": proc.returncode,
            "output": sanitize(fetch.stdout + proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "repo_task":
        task = str(args.get("task", "")).strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,96}", task):
            raise ValueError("invalid repo task name")
        base = Path("/opt/zen/zen-ops-runtime/deploy/ops_tasks").resolve()
        path = (base / (task if task.endswith(".sh") else task + ".sh")).resolve()
        if not str(path).startswith(str(base) + "/"):
            raise ValueError("repo task escaped task root")
        if not path.is_file():
            raise ValueError("repo task does not exist in the deployed main runtime")
        task_args = args.get("task_args", [])
        if not isinstance(task_args, list) or len(task_args) > 32:
            raise ValueError("task_args must be a short list")
        clean_args = [str(x)[:512] for x in task_args]
        proc = run(["/bin/bash", str(path), *clean_args], timeout=timeout)
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "tests":
        proc = run(
            ["/opt/zen/venv/bin/python", "-m", "pytest", "-q"],
            cwd="/opt/zen/ZEN-MA2-Agent",
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "mcp_probe":
        server = str(args.get("server", ""))
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", server):
            raise ValueError("invalid MCP server name")
        proc = run(["openclaw", "mcp", "probe", server, "--json"], timeout=min(timeout, 120))
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "console":
        mode = str(args.get("mode", "toggle"))
        if mode not in {"ma", "monitor", "toggle", "auto"}:
            raise ValueError("invalid console mode")
        proc = run(["/usr/local/bin/zen-console-mode", mode], timeout=20)
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "process_list":
        pattern = str(args.get("pattern", "")).strip()
        proc = run(
            ["ps", "-eo", "pid,ppid,etime,%cpu,%mem,user,args", "--sort=-%cpu"],
            timeout=min(timeout, 30),
        )
        output = proc.stdout
        if pattern:
            try:
                rx = re.compile(pattern, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"invalid process pattern: {exc}") from exc
            lines = output.splitlines()
            output = "\n".join([lines[0], *[line for line in lines[1:] if rx.search(line)]]) + "\n"
        return {
            "returncode": proc.returncode,
            "output": sanitize(output),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "journal":
        service = str(args.get("service", ""))
        if service not in ALLOWED_SERVICES:
            raise ValueError("service is not allowlisted")
        lines = max(1, min(int(args.get("lines", 200)), 1000))
        proc = run(
            ["journalctl", "-u", service, "-n", str(lines), "--no-pager"],
            timeout=min(timeout, 60),
        )
        return {
            "returncode": proc.returncode,
            "output": sanitize(proc.stdout),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "tool_inventory":
        commands = [
            ["restic", "version"],
            ["docker", "--version"],
            ["midimonster", "-v"],
            ["rtpmidid-cli", "--help"],
            ["ltcgen", "--help"],
            ["bd", "--version"],
            ["supergateway", "--version"],
            ["codex-acp", "--version"],
            ["gemini", "--version"],
        ]
        chunks = []
        rc = 0
        for cmd in commands:
            proc = run(cmd, timeout=30)
            rc |= proc.returncode
            chunks.append("$ " + " ".join(cmd) + "\n" + proc.stdout)
        return {
            "returncode": rc,
            "output": sanitize("\n".join(chunks)),
            "started_at": started,
            "finished_at": now(),
        }

    if kind == "read_file":
        path = Path(str(args.get("path", ""))).resolve()
        if not any(str(path) == base or str(path).startswith(base + "/") for base in SAFE_CWDS):
            raise ValueError("read_file path is outside the allowed roots")
        limit = max(1, min(int(args.get("limit", 100_000)), 200_000))
        data = path.read_text(errors="replace")[:limit]
        return {
            "returncode": 0,
            "output": sanitize(data),
            "started_at": started,
            "finished_at": now(),
        }

    raise ValueError(f"unsupported job kind: {kind}")


def publish(job_id: str, payload: dict[str, Any]) -> None:
    write_json(JOBS_DIR / job_id / "result.json", payload)
    write_json(PUBLIC_DIR / f"{job_id}.json", payload)
    write_json(PUBLIC_DIR / "latest.json", payload)


def process_once() -> None:
    if not fetch_control_ref():
        return
    job = read_control_job()
    if job is None:
        return
    job_id, kind, args = validate_job(job)
    state = load_state()
    if state.get("last_job_id") == job_id:
        return

    running = {
        "schema": "zen.ops.result.v1",
        "job_id": job_id,
        "kind": kind,
        "status": "running",
        "received_at": now(),
    }
    publish(job_id, running)

    try:
        detail = execute(job_id, kind, args)
        status = "completed" if detail.get("returncode") == 0 else "failed"
        result = {
            **running,
            "status": status,
            **detail,
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            **running,
            "status": "timeout",
            "returncode": 124,
            "output": sanitize((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
            "finished_at": now(),
        }
    except Exception as exc:
        result = {
            **running,
            "status": "rejected",
            "returncode": 125,
            "output": sanitize(repr(exc)),
            "finished_at": now(),
        }

    publish(job_id, result)
    write_json(STATE_FILE, {"last_job_id": job_id, "updated_at": now()})


def main() -> int:
    ensure_control_repo()
    while True:
        try:
            process_once()
        except Exception as exc:
            write_json(
                PUBLIC_DIR / "worker-error.json",
                {
                    "schema": "zen.ops.worker_error.v1",
                    "status": "error",
                    "error": sanitize(repr(exc)),
                    "updated_at": now(),
                },
            )
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
