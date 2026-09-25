import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

function fail(message, code = 2) {
  process.stdout.write(JSON.stringify({ ok: false, error: String(message) }));
  process.exit(code);
}

const [inputPath, openclawRoot, configPath, agentId] = process.argv.slice(2);
if (!inputPath || !openclawRoot || !configPath || !agentId) {
  fail("Expected input path, OpenClaw root, config path, and agent id.");
}

try {
  const sdkPath = path.join(
    openclawRoot,
    "dist",
    "plugin-sdk",
    "simple-completion-runtime.js",
  );
  const {
    prepareSimpleCompletionModelForAgent,
    completeWithPreparedSimpleCompletionModel,
  } = await import(pathToFileURL(sdkPath).href);

  const request = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const cfg = JSON.parse(await fs.readFile(configPath, "utf8"));
  if (
    typeof request?.system_prompt !== "string" ||
    typeof request?.user_prompt !== "string"
  ) {
    fail("Inference input must contain system_prompt and user_prompt strings.");
  }

  const prepared = await prepareSimpleCompletionModelForAgent({
    cfg,
    agentId,
    skipAgentDiscovery: true,
    allowMissingApiKeyModes: ["aws-sdk"],
  });
  if (prepared && "error" in prepared) {
    fail(prepared.error);
  }

  const result = await completeWithPreparedSimpleCompletionModel({
    model: prepared.model,
    auth: prepared.auth,
    cfg,
    context: {
      systemPrompt: request.system_prompt,
      messages: [
        {
          role: "user",
          content: request.user_prompt,
          timestamp: Date.now(),
        },
      ],
      tools: [],
    },
    options: {
      maxTokens:
        typeof prepared.model?.maxTokens === "number" &&
        Number.isFinite(prepared.model.maxTokens)
          ? prepared.model.maxTokens
          : undefined,
    },
  });

  const text = (result?.content ?? [])
    .filter((block) => block?.type === "text" && typeof block.text === "string")
    .map((block) => block.text)
    .join("\n")
    .trim();

  if (!text) {
    fail("OpenClaw SDK completion returned no text output.");
  }

  process.stdout.write(
    JSON.stringify({
      ok: true,
      capability: "model.run",
      transport: "sdk-local",
      provider: prepared.selection?.provider ?? null,
      model: prepared.selection?.modelId ?? null,
      attempts: [],
      outputs: [{ text, mediaUrl: null }],
    }),
  );
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}
