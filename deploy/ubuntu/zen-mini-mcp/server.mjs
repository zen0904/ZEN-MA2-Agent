import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile, readdir, stat } from "node:fs/promises";
import path from "node:path";

import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";

const execFileAsync = promisify(execFile);
const VERSION = "0.2.0";

const SAFE_FILES = {
  updater_heartbeat: "/var/lib/zen-ops/public/updater-heartbeat.json",
  latest_result: "/var/lib/zen-ops/public/latest.json",
  project_control: "/opt/zen/zen-ops-runtime/data/zen_project_control.json",
  agents: "/opt/zen/zen-ops-runtime/AGENTS.md",
  obsidian_zen_boundary: "/var/lib/zenui/obsidian-mind/brain/ZEN Agent Server.md",
  obsidian_north_star: "/var/lib/zenui/obsidian-mind/brain/North Star.md"
};

const SERVICE_UNITS = [
  "zen-ops-worker.service",
  "zen-ops-updater.timer",
  "zen-ops-results.service",
  "zen-chatgpt-desktop.service",
  "zen-mini-taskbar.service",
  "tailscaled.service"
];

function result(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return { content: [{ type: "text", text }] };
}

async function run(file, args = [], timeout = 8000) {
  const { stdout, stderr } = await execFileAsync(file, args, {
    timeout,
    maxBuffer: 1024 * 1024,
    env: { ...process.env, PATH: "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" }
  });
  return { stdout: stdout.trim(), stderr: stderr.trim() };
}

async function serviceState(unit) {
  try {
    const { stdout } = await run("systemctl", ["show", unit, "--no-pager",
      "-p", "Id", "-p", "LoadState", "-p", "ActiveState", "-p", "SubState",
      "-p", "UnitFileState", "-p", "ExecMainStatus"]);
    return Object.fromEntries(stdout.split("\n").filter(Boolean).map(line => {
      const i = line.indexOf("=");
      return i < 0 ? [line, ""] : [line.slice(0, i), line.slice(i + 1)];
    }));
  } catch (error) {
    return { Id: unit, error: String(error?.message || error) };
  }
}

async function miniStatus() {
  const [hostname, uptime, meminfo, loadavg, df, services] = await Promise.all([
    readFile("/etc/hostname", "utf8").then(s => s.trim()).catch(() => "unknown"),
    readFile("/proc/uptime", "utf8").then(s => Number(s.split(/\s+/)[0])).catch(() => null),
    readFile("/proc/meminfo", "utf8").catch(() => ""),
    readFile("/proc/loadavg", "utf8").then(s => s.trim()).catch(() => ""),
    run("df", ["-B1", "--output=size,used,avail,pcent,target", "/"]).then(r => r.stdout).catch(() => ""),
    Promise.all(SERVICE_UNITS.map(serviceState))
  ]);

  const mem = Object.fromEntries(meminfo.split("\n").filter(Boolean).map(line => {
    const m = line.match(/^([^:]+):\s+(\d+)/);
    return m ? [m[1], Number(m[2]) * 1024] : null;
  }).filter(Boolean));

  return {
    hostname,
    uptime_seconds: uptime,
    loadavg,
    memory_bytes: {
      total: mem.MemTotal ?? null,
      available: mem.MemAvailable ?? null
    },
    root_filesystem: df,
    services
  };
}

async function zenProjectStatus() {
  let projectControl = null;
  try { projectControl = JSON.parse(await readFile(SAFE_FILES.project_control, "utf8")); } catch {}
  const git = {};
  try { git.head = (await run("git", ["-c", "safe.directory=/opt/zen/zen-ops-runtime", "-C", "/opt/zen/zen-ops-runtime", "rev-parse", "HEAD"])).stdout; } catch {}
  try { git.branch = (await run("git", ["-c", "safe.directory=/opt/zen/zen-ops-runtime", "-C", "/opt/zen/zen-ops-runtime", "branch", "--show-current"])).stdout; } catch {}
  try { git.status = (await run("git", ["-c", "safe.directory=/opt/zen/zen-ops-runtime", "-C", "/opt/zen/zen-ops-runtime", "status", "--short"])).stdout; } catch {}
  return { git, project_control: projectControl };
}

async function recentOpsResults(limit) {
  const dir = "/var/lib/zen-ops/public";
  const names = (await readdir(dir)).filter(n => n.endsWith(".json"));
  const rows = await Promise.all(names.map(async name => {
    const s = await stat(path.join(dir, name));
    return { name, mtime: s.mtime.toISOString(), size: s.size };
  }));
  return rows.sort((a,b) => b.mtime.localeCompare(a.mtime)).slice(0, limit);
}

async function walkMarkdown(root, maxFiles = 1500) {
  const out = [];
  async function walk(dir) {
    if (out.length >= maxFiles) return;
    let entries = [];
    try { entries = await readdir(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (out.length >= maxFiles) break;
      if (e.name === ".git" || e.name === "node_modules" || e.name.startsWith(".obsidian")) continue;
      const full = path.join(dir, e.name);
      if (e.isDirectory()) await walk(full);
      else if (e.isFile() && e.name.endsWith(".md")) out.push(full);
    }
  }
  await walk(root);
  return out;
}

async function obsidianSearch(query, limit) {
  const root = "/var/lib/zenui/obsidian-mind";
  const files = await walkMarkdown(root);
  const q = query.toLowerCase();
  const matches = [];
  for (const file of files) {
    if (matches.length >= limit) break;
    let text = "";
    try { text = await readFile(file, "utf8"); } catch { continue; }
    const idx = text.toLowerCase().indexOf(q);
    if (idx < 0) continue;
    const start = Math.max(0, idx - 220);
    const end = Math.min(text.length, idx + q.length + 420);
    matches.push({
      path: path.relative(root, file),
      snippet: text.slice(start, end).replace(/\s+/g, " ").trim()
    });
  }
  return { query, count: matches.length, matches };
}

function createServer() {
  const server = new McpServer({ name: "zen-mini", version: VERSION });

  server.registerTool("mini_status", {
    description: "Read health, uptime, storage, memory and allowlisted service state from this ZEN Mac mini. Read-only."
  }, async () => result(await miniStatus()));

  server.registerTool("zen_project_status", {
    description: "Read the current ZEN runtime Git state and canonical project-control JSON. Read-only."
  }, async () => result(await zenProjectStatus()));

  server.registerTool("service_status", {
    description: "Read one allowlisted Mini systemd service state. Read-only.",
    inputSchema: z.object({ unit: z.enum(SERVICE_UNITS) })
  }, async ({ unit }) => result(await serviceState(unit)));

  server.registerTool("read_safe_file", {
    description: "Read one explicitly allowlisted ZEN or Obsidian governance/status file. No arbitrary paths.",
    inputSchema: z.object({ key: z.enum(Object.keys(SAFE_FILES)) })
  }, async ({ key }) => {
    const file = SAFE_FILES[key];
    const text = await readFile(file, "utf8");
    return result({ key, path: file, text: text.slice(0, 120000) });
  });

  server.registerTool("recent_ops_results", {
    description: "List recent ZEN Ops result JSON files with timestamps and sizes. Read-only.",
    inputSchema: z.object({ limit: z.number().int().min(1).max(50).default(20) })
  }, async ({ limit }) => result(await recentOpsResults(limit)));

  server.registerTool("obsidian_search", {
    description: "Lexically search the local Obsidian Mind vault for persistent agent memory. Read-only.",
    inputSchema: z.object({
      query: z.string().min(2).max(200),
      limit: z.number().int().min(1).max(20).default(8)
    })
  }, async ({ query, limit }) => result(await obsidianSearch(query, limit)));

  server.registerTool("gateway_info", {
    description: "Describe this bounded local ZEN Mini MCP."
  }, async () => result({
    name: "zen-mini",
    version: VERSION,
    transport: "stdio",
    mode: "read-only",
    ma2_writes: false,
    ma3_writes: false,
    arbitrary_shell: false,
    arbitrary_file_read: false
  }));

  return server;
}

serveStdio(createServer);
