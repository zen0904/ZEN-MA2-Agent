import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const client = new Client({ name: "zen-mini-smoke", version: "0.2.0" });
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [new URL("./server.mjs", import.meta.url).pathname],
  env: { ...process.env, HOME: "/var/lib/zenui" }
});

await client.connect(transport);
const listed = await client.listTools();
console.log("TOOLS=" + listed.tools.map(t => t.name).sort().join(","));
const info = await client.callTool({ name: "gateway_info", arguments: {} });
console.log("GATEWAY_INFO=" + JSON.stringify(info));
const status = await client.callTool({ name: "mini_status", arguments: {} });
console.log("MINI_STATUS=" + JSON.stringify(status).slice(0, 4000));
await client.close();
