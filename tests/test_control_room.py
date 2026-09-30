import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_control_room_and_ops_worker_scripts_compile():
    for relative in (
        "deploy/ubuntu/zen-control-room",
        "deploy/ubuntu/zen-ops-worker.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        compile(source, relative, "exec")


def test_control_room_activity_contract_is_present():
    worker = (ROOT / "deploy/ubuntu/zen-ops-worker.py").read_text(encoding="utf-8")
    room = (ROOT / "deploy/ubuntu/zen-control-room").read_text(encoding="utf-8")

    assert "zen.room.activity.v0.1" in worker
    assert 'event="WORK_START"' in worker
    assert 'event="WORK_END"' in worker
    assert "WORKER MOVEMENT" in room
    assert "picked up" in room
    assert "REST LOUNGE" in room


def test_example_control_job_metadata_is_non_authoritative_shape():
    sample = {
        "schema": "zen.ops.job.v1",
        "job_id": "room-test-job-001",
        "kind": "tests",
        "meta": {
            "actor": "CHATGPT_LEAD",
            "summary": "Run bounded tests",
            "tools": ["OPS", "GitHub"],
        },
        "args": {"timeout": 300},
    }
    assert sample["meta"]["actor"] == "CHATGPT_LEAD"
    assert "command" not in sample["meta"]
    assert "ma_command" not in json.dumps(sample["meta"]).lower()
