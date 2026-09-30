import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";

const client = new Client({ name: "zen-mini-smoke", version: "0.1.0" });
const transport = new StreamableHTTPClientTransport(new URL("http://127.0.0.1:19090/mcp"));
await client.connect(transport);
const tools = await client.listTools();
console.log("TOOLS=" + tools.tools.map(t => t.name).join(","));
const info = await client.callTool({ name: "gateway_info", arguments: {} });
console.log("GATEWAY_INFO=" + JSON.stringify(info));
const status = await client.callTool({ name: "mini_status", arguments: {} });
console.log("MINI_STATUS=" + JSON.stringify(status).slice(0, 4000));
await client.close();
