"""Portable entrypoint shared by Windows and macOS launchers.

All mutable state is resolved through ZEN_HOME.  Git safety is intentionally
conservative: fetch/status may be automatic, while dirty/diverged work is
never overwritten or merged by this program.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def home() -> Path:
    raw = os.environ.get("ZEN_HOME", "").strip()
    if not raw:
        raise SystemExit("ZEN_HOME is required; use a portable launcher.")
    return Path(raw).resolve()


def repo() -> Path:
    path = home() / "repo" / "ZEN-MA2-Agent"
    if not (path / ".git").exists():
        raise SystemExit(f"Portable Git working copy is missing: {path}")
    return path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    path = repo()
    return subprocess.run(
        ["git", "-c", f"safe.directory={path}", "-C", str(path), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True, check=check,
    )


def _git_output(*args: str) -> str:
    result = git(*args)
    return result.stdout.strip()


def git_status(fetch: bool = True) -> dict[str, str]:
    fetch_state = "NOT_RUN"
    if fetch:
        result = git("fetch", "origin", check=False)
        fetch_state = "OK" if result.returncode == 0 else "FAILED"
    dirty = _git_output("status", "--porcelain")
    branch = _git_output("branch", "--show-current")
    local = _git_output("rev-parse", "HEAD")
    remote_result = git("rev-parse", "origin/main", check=False)
    if remote_result.returncode:
        relation = "ORIGIN_MAIN_UNAVAILABLE"
        remote = ""
    else:
        remote = remote_result.stdout.strip()
        if dirty:
            relation = "LOCAL_CHANGES_PRESENT"
        elif local == remote:
            relation = "UP_TO_DATE"
        else:
            ahead, behind = _git_output("rev-list", "--left-right", "--count", "HEAD...origin/main").split()
            relation = "BEHIND" if ahead == "0" else "AHEAD" if behind == "0" else "DIVERGED_REVIEW_REQUIRED"
    return {"GIT_SYNC_STATUS": relation, "fetch": fetch_state, "branch": branch, "local_head": local, "origin_main": remote, "dirty": "YES" if dirty else "NO"}


def update() -> dict[str, str]:
    state = git_status(fetch=True)
    if state["GIT_SYNC_STATUS"] == "BEHIND":
        result = git("pull", "--ff-only", "origin", "main", check=False)
        state["pull"] = "FAST_FORWARD_OK" if result.returncode == 0 else "FAILED"
        return git_status(fetch=False) | {"pull": state["pull"]}
    state["pull"] = "NOT_NEEDED" if state["GIT_SYNC_STATUS"] == "UP_TO_DATE" else "NOT_RUN"
    return state


def _log(event: str, payload: dict[str, object]) -> None:
    path = home() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, "data": payload}
    with (path / "portable_launcher.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def provider_self_test() -> dict[str, object]:
    sys.path.insert(0, str(repo()))
    from zen_ma2_agent.llm import ProviderRouter, ProviderUnavailable

    router = ProviderRouter.from_portable_config()
    payload: dict[str, object] = {"ZEN_HOME": str(home()), "provider_mode": router.mode, "slots": [slot.safe_identity() for slot in router.slots]}
    # The portable self-test is a transport/schema probe, not a request for a
    # particular artistic role.  Prefer the legacy/general DESIGNER role when
    # it is eligible, but probe a configured role when a deliberately scoped
    # local slot only exposes the multi-agent role names.
    probe_role = "DESIGNER"
    if not any(slot.supports(probe_role) for slot in router.configured_slots()):
        probe_role = next(
            (
                role
                for slot in router.configured_slots()
                for role in slot.roles
            ),
            probe_role,
        )
    payload["probe_role"] = probe_role
    try:
        content, slot = router.complete(
            role=probe_role,
            system="Return exactly one JSON object: {\"schema\":\"zen.provider_probe.v0.1\",\"ready\":true}.",
            user="Perform the portable ZEN provider connectivity probe.",
        )
        probe = json.loads(content.removeprefix("```json").removesuffix("```").strip())
        if probe != {"schema": "zen.provider_probe.v0.1", "ready": True}:
            raise ValueError("Provider response did not satisfy the structured probe contract.")
        payload |= {"AUTONOMOUS_DESIGNER_AVAILABLE": "YES", "provider_slot": slot.number, "provider_type": slot.provider_type, "model": slot.model}
    except (ProviderUnavailable, ValueError, json.JSONDecodeError) as exc:
        payload |= {"AUTONOMOUS_DESIGNER_AVAILABLE": "NO", "reason": str(exc)}
    _log("provider_self_test", payload)
    return payload


def provider_pool_status() -> dict[str, object]:
    """Report provider-pool readiness without probing or exposing secrets."""
    sys.path.insert(0, str(repo()))
    from zen_ma2_agent.llm import ProviderRouter

    result = ProviderRouter.from_portable_config().pool_readiness()
    _log("provider_pool_status", result)
    return result


def ma2_connectivity(config_path: Path | None = None, socket_factory=socket.create_connection) -> dict[str, object]:
    """Perform a no-command TCP reachability check for the current host's MA2.

    This is intentionally not an authentication/Show-state claim.  The normal
    ZEN runtime remains responsible for its existing authenticated readiness
    and command safety checks.
    """
    path = config_path or home() / "config" / "settings.json"
    host, port = "127.0.0.1", 30000
    try:
        settings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        ma2 = settings.get("ma2", {}) if isinstance(settings, dict) else {}
        host = str(ma2.get("host", host)).strip() or host
        port = int(ma2.get("port", port))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"MA2_CONNECTIVITY": "CONFIG_INVALID", "host": host, "port": port}
    try:
        connection = socket_factory((host, port), timeout=1.5)
        connection.close()
    except OSError as exc:
        return {"MA2_CONNECTIVITY": "NOT_REACHABLE", "host": host, "port": port, "reason": type(exc).__name__}
    return {"MA2_CONNECTIVITY": "TCP_REACHABLE", "host": host, "port": port}


def autonomous_design(request_file: Path) -> dict[str, object]:
    if not request_file.is_file():
        raise SystemExit(f"Design request file does not exist: {request_file}")
    request = request_file.read_text(encoding="utf-8").strip()
    if not request:
        raise SystemExit("Design request file is empty.")
    sys.path.insert(0, str(repo()))
    from zen_ma2_agent.llm import ProviderRouter, ProviderUnavailable, design_with_provider
    from zen_ma2_agent.llm.autonomous_designer import DesignValidationError, write_run_provenance

    try:
        run = design_with_provider(ProviderRouter.from_portable_config(), request=request, repo_root=repo())
    except (ProviderUnavailable, DesignValidationError) as exc:
        result = {"AUTONOMOUS_DESIGNER_AVAILABLE": "NO", "reason": str(exc), "CODEX_ARTISTIC_INTERVENTION": "NONE"}
        _log("autonomous_design_unavailable", result)
        return result
    path = write_run_provenance(run)
    result = {
        "AUTONOMOUS_DESIGNER_AVAILABLE": "YES", "ZEN_RUN_ID": run.run_id, "run_path": str(path),
        "provider_slot": run.provider_slot, "provider_type": run.provider_type, "model": run.model,
        "context_hash": run.context_hash, "design_output_hash": run.output_hash,
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    _log("autonomous_design", result)
    return result


def multi_agent_design(
    request_file: Path,
    *,
    run_id: str | None = None,
    restart_run: bool = False,
    current_show_snapshot_file: Path | None = None,
    current_show_profile_file: Path | None = None,
) -> dict[str, object]:
    if not request_file.is_file():
        raise SystemExit(f"Design request file does not exist: {request_file}")
    request = request_file.read_text(encoding="utf-8").strip()
    if not request:
        raise SystemExit("Design request file is empty.")
    sys.path.insert(0, str(repo()))
    from zen_ma2_agent.llm import CurrentShowSnapshotInput, MultiAgentRunError, ProviderRouter, run_multi_agent_design

    current_show_snapshot = None
    if current_show_snapshot_file is not None:
        if not current_show_snapshot_file.is_file():
            raise SystemExit(f"Current Show snapshot does not exist: {current_show_snapshot_file}")
        try:
            snapshot_data = json.loads(current_show_snapshot_file.read_text(encoding="utf-8"))
            profile_data = None
            if current_show_profile_file is not None:
                if not current_show_profile_file.is_file():
                    raise SystemExit(f"Current Show profile does not exist: {current_show_profile_file}")
                profile_data = json.loads(current_show_profile_file.read_text(encoding="utf-8"))
            current_show_snapshot = CurrentShowSnapshotInput(snapshot_data, profile_data)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Current Show snapshot input is invalid: {type(exc).__name__}") from exc
    elif current_show_profile_file is not None:
        raise SystemExit("--current-show-profile requires --current-show-snapshot.")

    try:
        run = run_multi_agent_design(
            ProviderRouter.from_portable_config(),
            request=request,
            repo_root=repo(),
            run_id=run_id,
            restart_run=restart_run,
            current_show_snapshot=current_show_snapshot,
        )
    except MultiAgentRunError as exc:
        result = {
            "AUTONOMOUS_DESIGNER_AVAILABLE": "NO",
            "MULTI_AGENT_RUNTIME": "FAILED",
            "reason": str(exc),
            "CODEX_ARTISTIC_INTERVENTION": "NONE",
        }
        _log("multi_agent_design_failed", result)
        return result
    result = {
        "AUTONOMOUS_DESIGNER_AVAILABLE": "YES",
        "MULTI_AGENT_RUNTIME": "IMPLEMENTED",
        "ZEN_RUN_ID": run.run_id,
        "run_path": str(run.run_path),
        "resumed_from": run.resumed_from,
        "final_design_path": str(run.run_path / "final_design.json"),
        "context_hash": run.context_hash,
        "final_output_hash": __import__("hashlib").sha256(
            json.dumps(run.final_design, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "CURRENT_SHOW_FINGERPRINT": json.loads((run.run_path / "run.json").read_text(encoding="utf-8")).get("CURRENT_SHOW_FINGERPRINT"),
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    _log("multi_agent_design", result)
    return result


def knowledge_ingest(source_meta_file: Path, source_text_file: Path, *, max_records: int = 8) -> dict[str, object]:
    """Stage a bounded, review-first extraction from caller-supplied source text.

    The launcher never fetches URLs.  Source metadata and transient text must
    be supplied by an already-approved research/discovery layer.
    """
    if not source_meta_file.is_file():
        raise SystemExit(f"Knowledge source metadata does not exist: {source_meta_file}")
    if not source_text_file.is_file():
        raise SystemExit(f"Knowledge source text does not exist: {source_text_file}")
    try:
        source = json.loads(source_meta_file.read_text(encoding="utf-8"))
        source_text = source_text_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Knowledge ingestion input is invalid: {type(exc).__name__}") from exc
    sys.path.insert(0, str(repo()))
    from zen_ma2_agent.knowledge_ingestion import extract_knowledge_candidates, stage_ingestion_batch
    from zen_ma2_agent.knowledge_store import load_canonical_store
    from zen_ma2_agent.llm import ProviderRouter

    store = load_canonical_store(
        repo() / "data" / "external_lighting_knowledge_source_registry_001.json",
        repo() / "data" / "external_lighting_knowledge_pack_001.json",
    )
    batch, slot = extract_knowledge_candidates(
        ProviderRouter.from_portable_config(),
        source=source,
        source_text=source_text,
        canonical_records=store["records"],
        max_records=max_records,
    )
    path = stage_ingestion_batch(batch)
    result = {
        "KNOWLEDGE_INGESTION": "STAGED_NEEDS_REVIEW",
        "batch_path": str(path),
        "batch_id": batch["batch_id"],
        "source_id": batch["source"]["source_id"],
        "record_count": len(batch["records"]),
        "duplicate_candidate_count": len(batch["duplicate_candidates"]),
        "provider": slot.safe_identity(),
        "source_text_stored": False,
        "canonical_write_performed": False,
        "ma2_write_performed": False,
        "CODEX_ARTISTIC_INTERVENTION": "NONE",
    }
    _log("knowledge_ingest", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="ZEN USB portable launcher")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--git-status", action="store_true")
    choice.add_argument("--update", action="store_true")
    choice.add_argument("--push", action="store_true")
    choice.add_argument("--provider-self-test", action="store_true")
    choice.add_argument("--provider-pool-status", action="store_true")
    choice.add_argument("--ma2-connectivity", action="store_true")
    choice.add_argument("--design-request", type=Path)
    choice.add_argument("--multi-agent-design", type=Path)
    choice.add_argument("--knowledge-ingest", nargs=2, type=Path, metavar=("SOURCE_META", "SOURCE_TEXT"))
    parser.add_argument("--run-id")
    parser.add_argument("--restart-run", action="store_true")
    parser.add_argument("--current-show-snapshot", type=Path)
    parser.add_argument("--current-show-profile", type=Path)
    parser.add_argument("--knowledge-max-records", type=int, default=8)
    args = parser.parse_args()
    if (args.current_show_snapshot or args.current_show_profile) and not args.multi_agent_design:
        parser.error("--current-show-snapshot and --current-show-profile require --multi-agent-design.")
    if args.current_show_profile and not args.current_show_snapshot:
        parser.error("--current-show-profile requires --current-show-snapshot.")
    if args.git_status:
        result: dict[str, object] = git_status()
    elif args.update:
        result = update()
    elif args.push:
        state = git_status(fetch=True)
        if state["dirty"] == "YES" or state["GIT_SYNC_STATUS"] == "DIVERGED_REVIEW_REQUIRED":
            result = state | {"push": "NOT_RUN"}
        else:
            pushed = git("push", "origin", "main", check=False)
            result = git_status(fetch=False) | {"push": "OK" if pushed.returncode == 0 else "GIT_PUSH_AVAILABLE_NO"}
    elif args.provider_self_test:
        result = provider_self_test()
    elif args.provider_pool_status:
        result = provider_pool_status()
    elif args.ma2_connectivity:
        result = ma2_connectivity()
    elif args.design_request:
        if args.run_id or args.restart_run:
            parser.error("--run-id and --restart-run require --multi-agent-design.")
        result = autonomous_design(args.design_request)
    elif args.multi_agent_design:
        result = multi_agent_design(
            args.multi_agent_design,
            run_id=args.run_id,
            restart_run=args.restart_run,
            current_show_snapshot_file=args.current_show_snapshot,
            current_show_profile_file=args.current_show_profile,
        )
    elif args.knowledge_ingest:
        if args.run_id or args.restart_run:
            parser.error("--run-id and --restart-run are not valid with --knowledge-ingest.")
        result = knowledge_ingest(*args.knowledge_ingest, max_records=args.knowledge_max_records)
    else:
        if args.run_id or args.restart_run or args.current_show_snapshot or args.current_show_profile:
            parser.error("--run-id, --restart-run, and current Show snapshot options require --multi-agent-design.")
        result = git_status()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
