# ZEN OPS Recovery Acceptance 001

Status: CLOSED SUCCESS / LIVE MINI VERIFIED

Verified at: 2026-09-30 08:11:51 Asia/Taipei
Source job: `verify-zen-ops-recovery-final-20260930-0815`
Control branch: `zen-ops-control`
Main implementation HEAD at verification: `ce0ab9bbb0a73df25bfc97556d1b0c2fb0bc0e09`

## Result

The canonical Mini OPS recovery path is live and accepted.

Verified live output:

```text
ACTIVE:zen-ops-worker.service=PASS
ENABLED:zen-ops-worker.service=PASS
ENABLED:zen-ops-updater.timer=PASS
ACTIVE:zen-ops-updater.timer=PASS
ENABLED:zen-ops-results.service=PASS
ACTIVE:zen-ops-results.service=PASS
LOCAL_RESULTS_HTTP=PASS
FUNNEL_REASSERT=PASS
ZEN_OPS_RECOVERY_ACCEPTANCE=PASS
ZEN_OPS_RESULT_HTTPS_PORT=10000
```

Worker result status was `completed` with `returncode=0`.

The public recovery result path was also live at acceptance:

```text
https://zen-agent-server.tail3e0394.ts.net:10000
  -> http://127.0.0.1:18991
```

## What this closes

This acceptance closes the reboot/recovery gap for the canonical Git-controlled Mini OPS path:

```text
GitHub zen-ops-control
  -> zen-ops-worker
  -> bounded repo_task
  -> zen-ops-results
  -> Tailscale Funnel :10000
  -> sanitized result retrieval
```

The updater reconciliation changes already in main are therefore no longer merely repository-level fixes; the live Mini path has executed the recovery acceptance successfully.

## Separate remaining issue

The GitHub Actions self-hosted `zen-mini` runner path is a separate backup/diagnostic lane and was still observed queued independently of this acceptance.

That runner state does **not** invalidate this OPS recovery acceptance and does not block the canonical `zen-ops-worker` control path.

If the self-hosted runner is repaired later, treat that as a separate acceptance item. Do not reopen this recovery gate unless the canonical worker/updater/results/Funnel chain regresses.

## Post-acceptance regression check

After the recovery path was accepted, the canonical Mini OPS plane was used to run the full repository suite through job `full-tests-post-ops-recovery-20260930-0820`.

```text
status=completed
returncode=0
1004 passed, 2 warnings, 128 subtests passed in 22.61s
```

This confirms the recovered OPS path can execute the normal repository test workload successfully. The two pytest collection warnings are pre-existing collection warnings, not test failures.
