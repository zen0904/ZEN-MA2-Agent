import { Type } from "typebox";
import { defineToolPlugin } from "openclaw/plugin-sdk/tool-plugin";

const DEFAULT_BASE_URL = "http://127.0.0.1:8876";

const ConfigSchema = Type.Object(
  {
    operatorBaseUrl: Type.Optional(
      Type.String({
        description: "ZEN Operator API base URL. Development default is loopback-only.",
      }),
    ),
  },
  { additionalProperties: false },
);

function baseUrl(config: { operatorBaseUrl?: string }): string {
  const value = (config.operatorBaseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
  let parsed: URL;
  try {
    parsed = new URL(value);
  } catch {
    throw new Error("ZEN operatorBaseUrl must be a valid URL.");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("ZEN operatorBaseUrl must use http or https.");
  }
  const host = parsed.hostname.toLowerCase();
  if (!["127.0.0.1", "localhost", "::1", "[::1]"].includes(host)) {
    throw new Error("ZEN development plugin accepts loopback Operator API only.");
  }
  return value;
}

async function invokeZen(
  toolName: string,
  args: Record<string, unknown>,
  config: { operatorBaseUrl?: string },
  signal?: AbortSignal,
): Promise<unknown> {
  const response = await fetch(
    `${baseUrl(config)}/zen/v0.1/tools/${encodeURIComponent(toolName)}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ arguments: args }),
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
  return payload;
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
      name: "zen_approve",
      label: "ZEN Approve",
      description:
        "Approve one exact ZEN preview. ONLY call this after the human explicitly approves that preview in the current conversation. Never infer approval. ZEN still performs its own safety and fresh-state checks before any MA2 write.",
      parameters: Type.Object(
        {
          actionId: Type.String({ minLength: 1, maxLength: 128, description: "Exact action id shown by zen_preview." }),
          dangerConfirmed: Type.Optional(
            Type.Boolean({
              description:
                "Set true only when ZEN marks the action DANGEROUS and the human explicitly gives the required second confirmation.",
            }),
          ),
        },
        { additionalProperties: false },
      ),
      execute: async ({ actionId, dangerConfirmed }, config, context) =>
        invokeZen(
          "zen.approve",
          { action_id: actionId, danger_confirmed: dangerConfirmed ?? false },
          config,
          context.signal,
        ),
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
