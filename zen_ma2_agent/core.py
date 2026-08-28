from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import monotonic
from typing import Any

from .events import EventBus
from .config import save_preferences
from .extensions import ExtensionManager
from .network import internet_online, lan_ipv4_addresses
from .pairing import PairingManager
from .router import IntentRouter, ResponseType
from .runtime import AgentRuntime
from .skill_system import SkillError, SkillRegistry
from .state.providers import FixtureProvider, GroupProvider
from .state.store import StateStore
from .telnet_client import ConnectionState
from .workflow import WorkflowPlan


@dataclass
class ActionRecord:
    id: str
    workflow: WorkflowPlan
    status: str = "PENDING_APPROVAL"
    result: str | None = None

    @property
    def plan(self) -> dict[str, Any]:
        return self.workflow.as_dict()


class AgentCore:
    """Single control boundary used by Desktop UI and mobile HTTP/WebSocket UI."""

    def __init__(self, runtime: AgentRuntime | None = None):
        self.runtime = runtime or AgentRuntime()
        self.events = EventBus()
        self.pairing = PairingManager()
        self.chat: list[dict[str, Any]] = []
        self.actions: dict[str, ActionRecord] = {}
        self.state = StateStore()
        self.skills = SkillRegistry(self.runtime.root)
        self.skills.discover()
        self.router = IntentRouter()
        self.extensions = ExtensionManager(self.runtime.root)
        self.progress = "Idle"
        self._last_state = ""
        self._active_action_id: str | None = None
        self._internet_status = False
        self._internet_checked_at = 0.0

    def snapshot(self) -> dict[str, Any]:
        ma2 = self.runtime.preferences["ma2"]
        mode = self.runtime.preferences.get("internet_access", "AUTO")
        if mode == "OFFLINE":
            online = False
        elif mode == "ONLINE":
            online = True
        else:
            if monotonic() - self._internet_checked_at > 5:
                self._internet_status = internet_online()
                self._internet_checked_at = monotonic()
            online = self._internet_status
        return {
            "connection": {"state": self.runtime.state.value, "ready": self.runtime.ready, "status": self.runtime.status_text(), "host": ma2["host"], "port": ma2["port"], "user": self.runtime.client.authenticated_user if self.runtime.client else None},
            "internet": "ONLINE" if online else "OFFLINE",
            "phone_connected": self.pairing.connected_count,
            "progress": self.progress,
            "chat": list(self.chat[-40:]),
            "actions": [{"id": item.id, "status": item.status, "result": item.result, **item.plan} for item in self.actions.values()],
            "state_browser": self.state.summary(),
            "skills": self.skills.list(),
            "proposals": [proposal.summary() for proposal in self.extensions.proposals.values()],
        }

    def tick(self) -> None:
        self.runtime.poll_connection()
        state = self.runtime.status_text()
        if state != self._last_state:
            self._last_state = state
            self.events.emit("connection", self.snapshot())

    def connect(self, host: str, port: object, username: str, password: str = "") -> str:
        response = self.runtime.connect(host, port, username, password)
        self.events.emit("connection", self.snapshot())
        return response

    def disconnect(self) -> None:
        self.runtime.disconnect()
        self.events.emit("connection", self.snapshot())

    def set_internet_access(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"AUTO", "OFFLINE", "ONLINE"}:
            raise ValueError("Internet access must be AUTO, OFFLINE, or ONLINE.")
        self.runtime.preferences["internet_access"] = mode
        save_preferences(self.runtime.preferences, self.runtime.root)
        self.events.emit("internet", self.snapshot())

    def refresh_state(self, resource: str) -> dict[str, Any]:
        providers = {"groups": (GroupProvider(), self.state.put_groups), "fixtures": (FixtureProvider(), self.state.put_fixtures)}
        try:
            provider, store = providers[resource]
        except KeyError as exc:
            raise ValueError(f"State resource is not implemented: {resource}") from exc
        self.progress = f"Reading MA2 {resource.title()}"
        output = self.runtime.read_state(provider.command)
        snapshot = store(provider.parse(output))
        self.progress = "Idle"
        self.events.emit("state", self.snapshot())
        return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values}

    def set_skill_enabled(self, skill_id: str, enabled: bool) -> dict[str, Any]:
        manifest = self.skills.set_enabled(skill_id, enabled)
        self.events.emit("skills", self.snapshot())
        return manifest.summary()

    def propose_skill(self, name: str, intent: str, required_state: list[str], safety: str) -> dict[str, Any]:
        proposal = self.extensions.propose(name, intent, required_state, safety)
        self.events.emit("proposal", self.snapshot())
        return proposal.summary()

    def install_skill_proposal(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.extensions.install(proposal_id)
        self.skills.discover()
        self.events.emit("skills", self.snapshot())
        return proposal.summary()

    def handle_request(self, text: str, source: str = "desktop") -> dict[str, Any]:
        """Shared Desktop/Mobile natural-language routing entrypoint."""
        self.chat.append({"role": "user", "source": source, "text": text})
        self.progress = "Understanding request"
        self.events.emit("progress", {"stage": self.progress})
        route = self.router.route(text, self.skills)
        if route.response_type is ResponseType.NEEDS_CLARIFICATION:
            return self._respond(ResponseType.NEEDS_CLARIFICATION, "I understand this needs an MA2 workflow, but need a target or action. For example: ‘選 Group HYBRID’, ‘有哪些 Group’, or ‘複製 Group 1 到 2’.")
        if route.response_type is ResponseType.NOT_IMPLEMENTED:
            assert route.intent and route.capability
            message = (f"Request: {route.normalized_text}\nIntent: {route.intent.kind}\n"
                       f"Matched capability: {route.capability.name}\nStatus: NOT IMPLEMENTED\n"
                       f"Safety: {route.capability.safety}\n"
                       f"Proposed next step: Enable, install, or implement the {route.capability.name} workflow.")
            return self._respond(ResponseType.NOT_IMPLEMENTED, message, intent=route.intent, capability=route.capability.id)
        if route.response_type is ResponseType.ANSWER:
            assert route.intent
            try:
                result = self.refresh_state(route.intent.kind.removeprefix("state_"))
            except ConnectionError as exc:
                return self._respond(ResponseType.ERROR, str(exc), intent=route.intent)
            items = "\n".join(f"{item['number']}: {item['name']}" for item in result["values"]) or "No entries returned."
            return self._respond(ResponseType.ANSWER, f"{result['resource'].title()} ({result['count']})\n{items}", intent=route.intent, state=result)
        try:
            assert route.intent
            workflow = self.skills.plan_intent(route.intent, self.state, self.runtime.preferences)
            self.runtime.log("workflow_preview", workflow.as_dict())
        except (SkillError, ConnectionError) as exc:
            return self._respond(ResponseType.ERROR, str(exc) or "Unable to prepare a safe workflow.", intent=route.intent)
        action_id = uuid.uuid4().hex[:12]
        if self._active_action_id:
            previous = self.actions.get(self._active_action_id)
            if previous and previous.status == "PENDING_APPROVAL":
                previous.status = "CANCELLED"
        record = ActionRecord(action_id, workflow)
        self.actions[action_id] = record
        self._active_action_id = action_id
        response = "Workflow plan ready for review." if workflow.executable else workflow.preview_note
        self.chat.append({"role": "assistant", "kind": ResponseType.ACTION_PLAN.value, "text": response, "action_id": action_id})
        self.progress = "Waiting for approval"
        self.events.emit("plan", self.snapshot())
        return {"type": ResponseType.ACTION_PLAN.value, "message": response, "action": {"id": action_id, "status": record.status, **record.plan}}

    def submit_request(self, text: str, source: str = "desktop") -> dict[str, Any]:
        """Backward-compatible alias; all callers should use handle_request."""
        return self.handle_request(text, source)

    def _respond(self, response_type: ResponseType, message: str, **extra: Any) -> dict[str, Any]:
        self.chat.append({"role": "assistant", "kind": response_type.value, "text": message})
        self.progress = "Idle"
        self.events.emit("chat", self.snapshot())
        return {"type": response_type.value, "message": message, "action": None, **extra}

    def cancel_action(self, action_id: str) -> bool:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            return False
        action.status = "CANCELLED"
        if self._active_action_id == action_id:
            self._active_action_id = None
        self.progress = "Idle"
        self.events.emit("plan", self.snapshot())
        return True

    def approve_action(self, action_id: str, *, danger_confirmed: bool = False) -> dict[str, Any]:
        action = self.actions.get(action_id)
        if not action or action.status != "PENDING_APPROVAL":
            raise ValueError("Action is not awaiting approval.")
        if action_id != self._active_action_id:
            raise ValueError("This preview is no longer the active action.")
        if not self.runtime.ready:
            raise PermissionError("MA2 must be READY before an approved action can execute.")
        if action.workflow.safety == "DANGEROUS" and not danger_confirmed:
            raise PermissionError("Dangerous actions require a second confirmation.")
        action.status = "APPROVED"
        self.progress = "Executing"
        self.events.emit("progress", {"stage": self.progress})
        try:
            commands = self.skills.approved_commands(action.workflow.task.skill_id, action.workflow)
            results = self.runtime.execute_approved_commands(commands)
            result = "\n".join(item for item in results if item) or "Approved MA2 workflow commands sent"
            action.status, action.result = "EXECUTED", result
            self._active_action_id = None
            self.chat.append({"role": "assistant", "kind": "result", "text": action.result, "action_id": action_id})
            self.progress = "Verifying"
        except Exception as exc:
            action.status, action.result = "FAILED", str(exc)
            self._active_action_id = None
            self.progress = "Idle"
            self.events.emit("error", {"message": str(exc)})
            raise
        self.events.emit("execution", self.snapshot())
        return {"id": action.id, "status": action.status, "result": action.result}

    def phone_urls(self, port: int) -> list[str]:
        return [f"http://{address}:{port}/?nonce={self.pairing.nonce}" for address in lan_ipv4_addresses()]
