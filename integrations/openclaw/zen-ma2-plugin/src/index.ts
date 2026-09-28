import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const DEFAULT_OPERATOR_BASE_URL = "http://127.0.0.1:8876";
const DEFAULT_CONTROLLER_BASE_URL = "http://127.0.0.1:18876";
const DEFAULT_LIGHTING_ADAPTER_ID = "LIGHTING_GRANDMA2";
const DEPARTMENT_PREVIEW_TOOL_NAMES = new Set([
  "zen.design.request",
  "zen.preview",
  "zen.position.preview",
  "zen.position.raw.preview",
  "zen.position.calibration.preview",
]);

export type ZenPluginConfig = {
  operatorBaseUrl?: string;
  controllerBaseUrl?: string;
};

type ZenEndpoint = "operator" | "controller";

export function endpointForTool(toolName: string): ZenEndpoint {
  return toolName === "zen.department.status" || DEPARTMENT_PREVIEW_TOOL_NAMES.has(toolName)
    ? "controller"
    : "operator";
}

const ConfigSchema = Type.Object(
  {
    operatorBaseUrl: Type.Optional(
      Type.String({
        description: "MA-local ZEN Operator API base URL. Default is loopback 127.0.0.1:8876.",
      }),
    ),
    controllerBaseUrl: Type.Optional(
      Type.String({
        description: "Show Agent Controller bounded facade for status and preview-only delegation. Default is loopback 127.0.0.1:18876.",
      }),
    ),
  },
  { additionalProperties: false },
);

function loopbackBaseUrl(value: string, fieldName: string): string {
  const normalized = value.replace(/\/+$/, "");
  let parsed: URL;
  try {
    parsed = new URL(normalized);
  } catch {
    throw new Error(`ZEN ${fieldName} must be a valid URL.`);
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(`ZEN ${fieldName} must use http or https.`);
  }
  const host = parsed.hostname.toLowerCase();
  if (!["127.0.0.1", "localhost", "::1", "[::1]"].includes(host)) {
    throw new Error(`ZEN ${fieldName} accepts loopback endpoints only.`);
  }
  return normalized;
}

function operatorBaseUrl(config: ZenPluginConfig): string {
  return loopbackBaseUrl(
    config.operatorBaseUrl || DEFAULT_OPERATOR_BASE_URL,
    "operatorBaseUrl",
  );
}

function controllerBaseUrl(config: ZenPluginConfig): string {
  return loopbackBaseUrl(
    config.controllerBaseUrl || DEFAULT_CONTROLLER_BASE_URL,
    "controllerBaseUrl",
  );
}

export function baseUrlForTool(toolName: string, config: ZenPluginConfig): string {
  return endpointForTool(toolName) === "controller"
    ? controllerBaseUrl(config)
    : operatorBaseUrl(config);
}

type ZenToolResult = {
  schema: "zen.tool_result.v0.1";
  tool: string;
  status: "SUCCESS" | "NOT_IMPLEMENTED" | "REJECTED" | "FAILED";
  result: unknown;
  error: unknown;
  request_id?: string | null;
};

function isZenToolResult(value: unknown): value is ZenToolResult {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  return (
    record.schema === "zen.tool_result.v0.1" &&
    typeof record.tool === "string" &&
    ["SUCCESS", "NOT_IMPLEMENTED", "REJECTED", "FAILED"].includes(String(record.status)) &&
    Object.prototype.hasOwnProperty.call(record, "result") &&
    Object.prototype.hasOwnProperty.call(record, "error")
  );
}

export function requestForTool(
  toolName: string,
  args: Record<string, unknown>,
): { requestTool: string; arguments: Record<string, unknown> } {
  if (!DEPARTMENT_PREVIEW_TOOL_NAMES.has(toolName)) {
    return { requestTool: toolName, arguments: args };
  }
  return {
    requestTool: "zen.department.preview",
    arguments: {
      adapter_id: DEFAULT_LIGHTING_ADAPTER_ID,
      tool_name: toolName,
      arguments: args,
    },
  };
}

function unwrapDepartmentPreview(
  originalToolName: string,
  payload: unknown,
): unknown {
  if (!DEPARTMENT_PREVIEW_TOOL_NAMES.has(originalToolName)) return payload;
  if (!isZenToolResult(payload) || payload.tool !== "zen.department.preview") {
    throw new Error("ZEN Controller returned an invalid department preview envelope.");
  }
  if (payload.status !== "SUCCESS") return payload;
  if (!payload.result || typeof payload.result !== "object" || Array.isArray(payload.result)) {
    throw new Error("ZEN Controller department preview result is invalid.");
  }
  const delegation = payload.result as Record<string, unknown>;
  if (
    delegation.schema !== "zen.department_preview.v0.1" ||
    delegation.authority !== "REMOTE_PREVIEW_ONLY" ||
    delegation.ma2_writes !== 0 ||
    delegation.remote_tool !== originalToolName
  ) {
    throw new Error("ZEN Controller department preview contract mismatch.");
  }
  if (delegation.delegation_status !== "SUCCESS") {
    const rejected = delegation.delegation_status === "REJECTED";
    return {
      schema: "zen.tool_result.v0.1",
      tool: originalToolName,
      status: rejected ? "REJECTED" : "FAILED",
      result: null,
      error:
        delegation.error && typeof delegation.error === "object"
          ? delegation.error
          : {
              code: rejected ? "DEPARTMENT_PREVIEW_REJECTED" : "DEPARTMENT_PREVIEW_FAILED",
              message: "ZEN Controller did not complete preview delegation.",
            },
      request_id: payload.request_id ?? null,
    } satisfies ZenToolResult;
  }
  const remoteResult = delegation.remote_result;
  if (!isZenToolResult(remoteResult) || remoteResult.tool !== originalToolName) {
    throw new Error("ZEN Controller returned an invalid remote preview result.");
  }
  return remoteResult;
}

async function invokeZen(
  toolName: string,
  args: Record<string, unknown>,
  config: ZenPluginConfig,
  signal?: AbortSignal,
): Promise<unknown> {
  const root = baseUrlForTool(toolName, config);
  const request = requestForTool(toolName, args);
  const response = await fetch(
    `${root}/zen/v0.1/tools/${encodeURIComponent(request.requestTool)}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ arguments: request.arguments }),
      signal,
    },
  );
  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(`ZEN Operator API returned non-JSON HTTP ${response.status}.`);
  }
  if (!response.ok) {
    throw new Error(`ZEN Operator API HTTP ${response.status}: ${JSON.stringify(payload)}`);
  }
  return unwrapDepartmentPreview(toolName, payload);
}

export default defineToolPlugin({
  id: "zen-ma2",
  name: "ZEN MA2",
  description:
    "Typed OpenClaw tools for the ZEN grandMA2 assistant. ZEN remains the safety, preview, approval, builder and MA authority.",
  configSchema: ConfigSchema,
  tools: (tool) => [
    tool({
      name: "zen_status",
      label: "ZEN Status",
      description: "Read ZEN Field Core, MA2, workers and workflow status. Read-only.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.status", {}, config, context.signal),
    }),
    tool({
      name: "zen_ma_status",
      label: "ZEN MA Status",
      description: "Read current ZEN MA bridge and MA2 connection status. Read-only.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.ma.status", {}, config, context.signal),
    }),
    tool({
      name: "zen_ma_visual",
      label: "ZEN MA Visual",
      description:
        "Capture the current grandMA2 onPC window and return bounded pixel-grounded visual observations. Read-only; the vision model has no MA write authority.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.ma.visual", {}, config, context.signal),
    }),
    tool({
      name: "zen_ma_stage_visual",
      label: "ZEN MA Stage Visual",
      description:
        "Navigate only among the fixed grandMA2 onPC Screen 2/3/4 controls, then capture and verify whether Stage/3D View is visible. No MA command, programming, playback, approval, or Show-write authority.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.ma.stage.visual", {}, config, context.signal),
    }),
    tool({
      name: "zen_design_request",
      label: "ZEN Design Request",
      description:
        "Send the user's natural-language lighting/programming request to ZEN. This only plans/previews through ZEN's typed safety path; it does not itself approve MA2 writes.",
      parameters: Type.Object(
        {
          request: Type.String({
            minLength: 1,
            maxLength: 2048,
            description: "The user's lighting/programming request, preserved faithfully.",
          }),
        },
        { additionalProperties: false },
      ),
      execute: async ({ request }, config, context) =>
        invokeZen("zen.design.request", { request }, config, context.signal),
    }),
    tool({
      name: "zen_preview",
      label: "ZEN Preview",
      description:
        "Read the current or specified ZEN action preview, including action id, safety, commands and approval gates. Read-only.",
      parameters: Type.Object(
        {
          actionId: Type.Optional(
            Type.String({ minLength: 1, maxLength: 128, description: "ZEN action id. Omit for current preview." }),
          ),
        },
        { additionalProperties: false },
      ),
      execute: async ({ actionId }, config, context) =>
        invokeZen("zen.preview", { action_id: actionId ?? null }, config, context.signal),
    }),
    tool({
      name: "zen_position_preview",
      label: "ZEN Position Application Preview",
      description:
        "Freshly revalidate one exact Position applicability probe and register an approval-gated ZEN Preview. Never approves or writes MA2.",
      parameters: Type.Object({
        expectedShowFingerprint: Type.String({ minLength: 64, maxLength: 64 }),
        groupId: Type.Integer({ minimum: 1 }),
        expectedGroupName: Type.String({ minLength: 1, maxLength: 256 }),
        expectedExactRefs: Type.Array(Type.String({ minLength: 1, maxLength: 32 }), { minItems: 1, maxItems: 128 }),
        presetRef: Type.String({ minLength: 3, maxLength: 32 }),
        expectedPresetLabel: Type.String({ minLength: 1, maxLength: 256 }),
      }, { additionalProperties: false }),
      execute: async ({ expectedShowFingerprint, groupId, expectedGroupName, expectedExactRefs, presetRef, expectedPresetLabel }, config, context) =>
        invokeZen("zen.position.preview", {
          expected_show_fingerprint: expectedShowFingerprint,
          group_id: groupId,
          expected_group_name: expectedGroupName,
          expected_exact_refs: expectedExactRefs,
          preset_ref: presetRef,
          expected_preset_label: expectedPresetLabel,
        }, config, context.signal),
    }),
    tool({
      name: "zen_position_raw_preview",
      label: "ZEN Raw Position Cue Preview",
      description:
        "Freshly verify an exact Group and register a Pan/Tilt raw Cue proof Preview. Does not approve, write MA2, or create Position Preset applicability.",
      parameters: Type.Object({
        expectedShowFingerprint: Type.String({ minLength: 64, maxLength: 64 }),
        groupId: Type.Integer({ minimum: 1 }),
        expectedGroupName: Type.String({ minLength: 1, maxLength: 256 }),
        expectedExactRefs: Type.Array(Type.String({ minLength: 1, maxLength: 32 }), { minItems: 1, maxItems: 128 }),
      }, { additionalProperties: false }),
      execute: async ({ expectedShowFingerprint, groupId, expectedGroupName, expectedExactRefs }, config, context) =>
        invokeZen("zen.position.raw.preview", {
          expected_show_fingerprint: expectedShowFingerprint,
          group_id: groupId,
          expected_group_name: expectedGroupName,
          expected_exact_refs: expectedExactRefs,
        }, config, context.signal),
    }),
    tool({
      name: "zen_position_calibration_preview",
      label: "ZEN Position Calibration Preview",
      description:
        "Register one approval-gated Position calibration transaction that will prove raw Pan/Tilt CueData and one new Agent-owned Position Preset application. Preview only; never approves or writes MA2.",
      parameters: Type.Object({
        expectedShowFingerprint: Type.String({ minLength: 64, maxLength: 64 }),
        groupId: Type.Integer({ minimum: 1 }),
        expectedGroupName: Type.String({ minLength: 1, maxLength: 256 }),
        expectedExactRefs: Type.Array(Type.String({ minLength: 1, maxLength: 32 }), { minItems: 1, maxItems: 128 }),
      }, { additionalProperties: false }),
      execute: async ({ expectedShowFingerprint, groupId, expectedGroupName, expectedExactRefs }, config, context) =>
        invokeZen("zen.position.calibration.preview", {
          expected_show_fingerprint: expectedShowFingerprint,
          group_id: groupId,
          expected_group_name: expectedGroupName,
          expected_exact_refs: expectedExactRefs,
        }, config, context.signal),
    }),
    tool({
      name: "zen_position_semantic_bindings",
      label: "ZEN Semantic Position Bindings",
      description:
        "List fresh verified Position application candidates and current semantic Position mappings. Read-only; no MA2 writes.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.position.semantic.bindings", {}, config, context.signal),
    }),
    tool({
      name: "zen_department_status",
      label: "ZEN Department Status",
      description:
        "Read controller-visible department adapter states. Read-only federation; no remote approval, shell, raw MA command, or write authority.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.department.status", {}, config, context.signal),
    }),
    tool({
      name: "zen_worker_status",
      label: "ZEN Worker Status",
      description: "Read ZEN remote AI worker availability and states. Read-only.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.worker.status", {}, config, context.signal),
    }),
    tool({
      name: "zen_watchdog_status",
      label: "ZEN Watchdog Status",
      description: "Read bounded ZEN watchdog health state. Read-only.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.watchdog.status", {}, config, context.signal),
    }),
    tool({
      name: "zen_host_status",
      label: "ZEN Host Status",
      description: "Read bounded ZEN host CPU, memory, disk and supported temperature state. Read-only.",
      parameters: Type.Object({}, { additionalProperties: false }),
      execute: async (_params, config, context) =>
        invokeZen("zen.host.status", {}, config, context.signal),
    }),
  ],
});
