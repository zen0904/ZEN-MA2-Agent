from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import monotonic
from typing import Any

from .events import EventBus
from .config import save_preferences
from .build_identity import load_build_identity
from .extensions import ExtensionManager
from .network import internet_online, lan_ipv4_addresses
from .pairing import PairingManager
from .router import IntentRouter, ResponseType
from .runtime import AgentRuntime
from .skill_system import SkillError, SkillRegistry
from .state.providers import AdapterResponseError, AdapterUnsupported, CueProvider, EffectProvider, ExecutorProvider, ExportFileGroupMembershipProvider, FixtureProvider, GroupMembershipProvider, GroupMembershipProviderError, GroupMembershipProviderUnavailable, GroupProvider, LayoutExportProvider, LayoutInventoryProvider, PageProvider, PresetProvider, SequenceProvider, ZenStateAdapter
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

    def __init__(self, runtime: AgentRuntime | None = None, group_membership_provider: GroupMembershipProvider | None = None):
        self.runtime = runtime or AgentRuntime()
        self.build_identity = load_build_identity(self.runtime.root)
        self.events = EventBus()
        self.pairing = PairingManager()
        self.chat: list[dict[str, Any]] = []
        self.actions: dict[str, ActionRecord] = {}
        self.state = StateStore()
        self.group_membership_provider = group_membership_provider or ExportFileGroupMembershipProvider()
        self.layout_export_provider = LayoutExportProvider()
        self.skills = SkillRegistry(self.runtime.root)
        self.skills.discover()
        self.router = IntentRouter()
        self.extensions = ExtensionManager(self.runtime.root)
        self.progress = "Idle"
        self._last_state = ""
        self._active_action_id: str | None = None
        self._internet_status = False
        self._internet_checked_at = 0.0
        self.last_chat_routing: dict[str, Any] | None = None
        self.runtime.log("startup", {"build_identity": self.build_identity, "runtime_root": str(self.runtime.root)})

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
        for resource in self.state.RESOURCES:
            self.state.mark_stale(resource)
        self.events.emit("connection", self.snapshot())

    def set_internet_access(self, mode: str) -> None:
        mode = mode.upper()
        if mode not in {"AUTO", "OFFLINE", "ONLINE"}:
            raise ValueError("Internet access must be AUTO, OFFLINE, or ONLINE.")
        self.runtime.preferences["internet_access"] = mode
        save_preferences(self.runtime.preferences, self.runtime.root)
        self.events.emit("internet", self.snapshot())

    def refresh_state(self, resource: str, *, group_no: int | None = None, layout_no: int | None = None, sequence: int | None = None) -> dict[str, Any]:
        """Refresh a named read-only state resource through an allow-listed provider."""
        self.progress = f"Reading MA2 {resource.title()}"
        try:
            if resource == "groups":
                provider = GroupProvider()
                snapshot = self.state.put_groups(provider.parse(self.runtime.read_state(provider.command)))
            elif resource == "fixtures":
                provider = FixtureProvider()
                snapshot = self.state.put_fixtures(provider.parse(self.runtime.read_state(provider.command)))
            elif resource == "sequences":
                provider = SequenceProvider()
                snapshot = self.state.put("sequences", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list")
            elif resource == "presets":
                provider = PresetProvider(); preset_type = "ALL" if sequence is None else str(sequence).upper()
                values = provider.parse(self.runtime.read_state(provider.command(preset_type)), preset_type)
                existing = self.state.get("presets"); retained=[item for item in (existing.values if existing else []) if item.get("preset_type") != preset_type]
                snapshot = self.state.put("presets", [*retained,*values], source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "effects":
                provider=EffectProvider(); snapshot=self.state.put("effects", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "pages":
                provider=PageProvider(); snapshot=self.state.put("pages", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "executors":
                provider=ExecutorProvider(); snapshot=self.state.put("executors", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list", capability={"requires_local_filesystem":False})
            elif resource == "cues":
                if not isinstance(sequence, int) or sequence < 1:
                    raise ValueError("Cue inventory requires a positive sequence number.")
                provider = CueProvider()
                cues = provider.parse(self.runtime.read_state(provider.command(sequence)), sequence)
                existing = self.state.get("cues")
                retained = [item for item in (existing.values if existing else []) if item.get("sequence") != sequence]
                snapshot = self.state.put("cues", [*retained, *cues], source="ma2_telnet_list")
            elif resource == "layouts" and layout_no is None:
                provider = LayoutInventoryProvider()
                snapshot = self.state.put("layouts", provider.parse(self.runtime.read_state(provider.command)), source="ma2_telnet_list")
            elif resource == "group_membership":
                if not isinstance(group_no, int) or isinstance(group_no, bool) or group_no < 1:
                    raise ValueError("Group membership requires a positive group number.")
                value = self.group_membership_provider.get_group_membership(
                    self.runtime,
                    group_no,
                    self.runtime.preferences.get("state_adapter"),
                )
                snapshot = self.state.upsert(resource, "group_no", value, source=self.group_membership_provider.source)
            elif resource == "layout_items":
                if not isinstance(layout_no, int) or isinstance(layout_no, bool) or layout_no < 1: raise ValueError("Layout requires a positive number.")
                value=self.layout_export_provider.get_layout(self.runtime, layout_no, self.runtime.preferences.get("state_adapter"))
                snapshot=self.state.upsert(resource,"layout",value,source=self.layout_export_provider.source,capability=self.layout_export_provider.capabilities(self.runtime,self.runtime.preferences.get("state_adapter")))
            elif resource in {"selection", "programmer"}:
                adapter = ZenStateAdapter()
                request, parser = self._adapter_state_request(resource, group_no=group_no, layout_no=layout_no)
                settings = self.runtime.preferences.get("state_adapter")
                output = self.runtime.read_adapter_state(
                    plugin_slot=adapter.plugin_slot(settings),
                    request=request.wire,
                    timeout_seconds=adapter.timeout_seconds(settings),
                )
                value = parser(adapter, output, request)
                snapshot = self.state.put(resource, [value], source=adapter.source)
            else:
                raise ValueError(f"State resource is not implemented: {resource}")
        except AdapterUnsupported as exc:
            snapshot = self.state.record_error(resource, str(exc), source=ZenStateAdapter.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "UNSUPPORTED", "error": snapshot.error}
        except AdapterResponseError as exc:
            snapshot = self.state.record_error(resource, str(exc), source=ZenStateAdapter.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "ERROR", "error": snapshot.error}
        except GroupMembershipProviderUnavailable as exc:
            snapshot = self.state.record_error(resource, f"UNSUPPORTED {exc}", source=self.group_membership_provider.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "UNSUPPORTED", "error": snapshot.error}
        except GroupMembershipProviderError as exc:
            snapshot = self.state.record_error(resource, str(exc), source=self.group_membership_provider.source)
            self.progress = "Idle"
            self.events.emit("state", self.snapshot())
            return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "ERROR", "error": snapshot.error}
        self.progress = "Idle"
        self.events.emit("state", self.snapshot())
        return {"resource": resource, "count": len(snapshot.values), "values": snapshot.values, "status": "available"}

    @staticmethod
    def _adapter_state_request(resource: str, *, group_no: int | None, layout_no: int | None) -> tuple[Any, Any]:
        if resource == "selection":
            return ZenStateAdapter.request("selection"), lambda adapter, output, request: adapter.unsupported_resource(output, request)
        if resource == "programmer":
            return ZenStateAdapter.request("programmer"), lambda adapter, output, request: adapter.unsupported_resource(output, request)
        raise ValueError(f"No adapter request for state resource: {resource}")

    def request_group_membership(self, group_no: int) -> dict[str, Any]:
        groups = self.state.get("groups")
        if not groups or groups.stale or groups.error:
            self.refresh_state("groups")
        result = self.refresh_state("group_membership", group_no=group_no)
        result["group"] = next((item for item in result["values"] if item.get("group_no") == group_no), None)
        return result

    def get_selection(self) -> dict[str, Any]:
        result = self.refresh_state("selection")
        result["selection"] = result["values"][0] if result["values"] else None
        return result

    def get_programmer_summary(self) -> dict[str, Any]:
        result = self.refresh_state("programmer")
        result["programmer"] = result["values"][0] if result["values"] else None
        return result

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
        self.last_chat_routing = {
            "CHAT_INPUT": text,
            "ROUTER_INTENT": route.intent.kind if route.intent else None,
            "ROUTER_PARAMETERS": route.intent.parameters if route.intent else None,
            "ROUTER_HANDLER": "state_answer" if route.response_type is ResponseType.ANSWER else route.response_type.value,
            "PROVIDER": self._provider_for_intent(route.intent),
        }
        self.runtime.log("chat_routing", self.last_chat_routing)
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
            return self._answer_state(route.intent)
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
        self.runtime.log("chat_response", {"RESPONSE_TYPE": response_type.value, "message": message})
        self.events.emit("chat", self.snapshot())
        return {"type": response_type.value, "message": message, "action": None, **extra}

    def _answer_state(self, intent: Any) -> dict[str, Any]:
        try:
            kind, parameters = intent.kind, intent.parameters
            if kind == "state_group_membership_name":
                groups = self.state.get("groups")
                if not groups or groups.stale or groups.error:
                    self.refresh_state("groups")
                    groups = self.state.get("groups")
                wanted = parameters["group_name"].casefold()
                group = next((item for item in (groups.values if groups else []) if item["name"].casefold() == wanted), None)
                if not group:
                    return self._respond(ResponseType.NEEDS_CLARIFICATION, f"No Group named {parameters['group_name']} is available in the current Group inventory.", intent=intent)
                result = self.request_group_membership(group["number"])
            elif kind == "state_group_membership":
                result = self.request_group_membership(parameters["group_no"])
            elif kind == "layout_items_query":
                result = self.refresh_state("layout_items", layout_no=parameters["layout_no"])
            elif kind == "state_selection":
                result = self.get_selection()
            elif kind == "state_programmer":
                result = self.get_programmer_summary()
            elif kind == "state_cues":
                result = self.refresh_state("cues", sequence=parameters["sequence"])
            elif kind in {"state_presets", "preset_list"}:
                result = self.refresh_state("presets", sequence=parameters["preset_type"])
            elif kind in {"state_effects", "effect_list", "effect_lookup"}: result = self.refresh_state("effects")
            elif kind in {"state_sequence_executors", "sequence_executor_lookup", "page_executor_list"}: result = self.refresh_state("executors")
            else:
                result = self.refresh_state(kind.removeprefix("state_"))
        except (ConnectionError, PermissionError, ValueError) as exc:
            return self._respond(ResponseType.ERROR, str(exc), intent=intent)
        if result["status"] != "available":
            return self._respond(ResponseType.ANSWER, result.get("error") or f"{result['resource']} is unavailable.", intent=intent, state=result)
        return self._respond(ResponseType.ANSWER, self._format_state_answer(intent, result), intent=intent, state=result)

    @staticmethod
    def _format_state_answer(intent: Any, result: dict[str, Any]) -> str:
        values = result["values"]
        kind = intent.kind
        if kind in {"state_groups", "state_fixtures", "state_sequences"}:
            return f"{result['resource'].title()} ({result['count']})\n" + ("\n".join(f"{item['number']}: {item['name']}" for item in values) or "No entries returned.")
        if kind == "state_layouts":
            return f"Layouts ({result['count']})\n" + ("\n".join(f"{item['layout']}: {item.get('name', '')}" for item in values) or "No entries returned.")
        if kind in {"state_group_membership", "state_group_membership_name"}:
            group_no = intent.parameters.get("group_no")
            group = next((item for item in values if group_no is None or item.get("group_no") == group_no), values[-1] if values else None)
            return f"Group {group['group_no']} {group['name']}\nFixtures ({len(group['fixtures'])}): " + ", ".join(str(item) for item in group["fixtures"])
        if kind == "layout_items_query":
            layout = next(item for item in values if item["layout"] == intent.parameters["layout_no"])
            rows = [f"{item['type']} {item['reference']}: x={item['x']}, y={item['y']}" for item in layout["items"]]
            return f"Layout {layout['layout']} {layout.get('name', '')}\n" + ("\n".join(rows) or "Empty layout.")
        if kind == "state_selection":
            selection = values[0]
            return "Selected Fixtures: " + (", ".join(str(item) for item in selection["fixtures"]) or "none")
        if kind == "state_programmer":
            programmer = values[0]
            return "Programmer: " + ("active values present" if programmer["has_active_values"] else "empty")
        if kind == "state_cues":
            sequence_cues = [item for item in values if item.get("sequence") == intent.parameters["sequence"]]
            return f"Sequence {intent.parameters['sequence']} Cues ({len(sequence_cues)})\n" + ("\n".join(f"{item['number']}: {item['name']}" for item in sequence_cues) or "No cues returned.")
        if kind in {"state_presets", "preset_list"}: return f"{intent.parameters['preset_type'].title()} Presets ({len(values)})\n" + ("\n".join(f"{item['number']}: {item['name']}" for item in values) or "No entries returned.")
        if kind in {"state_effects", "effect_list"}: return f"Effects ({len(values)})\n" + ("\n".join(f"{item['number']}: {item['name']}" for item in values) or "No entries returned.")
        if kind == "effect_lookup":
            item=next((item for item in values if item["number"]==intent.parameters["effect"]),None); return f"Effect {intent.parameters['effect']}: {item['name']}" if item else f"Effect {intent.parameters['effect']} not found."
        if kind in {"state_sequence_executors", "sequence_executor_lookup"}:
            rows=[item for item in values if item.get("assignment_type")=="sequence" and item.get("assignment")==intent.parameters["sequence"]]
            return f"Sequence {intent.parameters['sequence']} Executors ({len(rows)})\n" + ("\n".join(f"{item['location']}: {item.get('label') or ''}" for item in rows) or "No executor assignment returned.")
        if kind == "page_executor_list":
            rows=[item for item in values if item.get("page")==intent.parameters["page"]]; return f"Page {intent.parameters['page']} Executors ({len(rows)})\n" + ("\n".join(f"{item['location']}: {item.get('label') or ''}" for item in rows) or "No executor assignment returned.")
        return f"{result['resource'].title()} ({result['count']})"

    @staticmethod
    def _provider_for_intent(intent: Any | None) -> str | None:
        if intent is None:
            return None
        providers = {
            "layout_items_query": "LayoutExportProvider",
            "state_layouts": "LayoutInventoryProvider",
            "preset_list": "PresetProvider",
            "effect_list": "EffectProvider",
            "effect_lookup": "EffectProvider",
            "sequence_executor_lookup": "ExecutorProvider",
            "page_executor_list": "ExecutorProvider",
        }
        return providers.get(intent.kind)

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
