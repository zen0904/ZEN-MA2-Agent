import { describe, expect, it } from "vitest";
import entry, { baseUrlForTool, endpointForTool } from "./index.js";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

describe("zen-ma2", () => {
  it("declares the bounded ZEN tool surface", () => {
    expect(getToolPluginMetadata(entry)?.tools.map((tool) => tool.name)).toEqual([
      "zen_status",
      "zen_ma_status",
      "zen_ma_visual",
      "zen_ma_stage_visual",
      "zen_design_request",
      "zen_preview",
      "zen_position_preview",
      "zen_position_raw_preview",
      "zen_position_calibration_preview",
      "zen_position_semantic_bindings",
      "zen_position_semantic_bind",
      "zen_approve",
      "zen_department_status",
      "zen_worker_status",
      "zen_watchdog_status",
      "zen_host_status",
    ]);
  });

  it("routes show-level status to the controller and MA tools to the local adapter", () => {
    expect(endpointForTool("zen.department.status")).toBe("controller");
    expect(endpointForTool("zen.ma.status")).toBe("operator");
    expect(baseUrlForTool("zen.department.status", {})).toBe("http://127.0.0.1:18876");
    expect(baseUrlForTool("zen.ma.status", {})).toBe("http://127.0.0.1:8876");
    expect(() =>
      baseUrlForTool("zen.department.status", { controllerBaseUrl: "http://100.122.169.17:18876" }),
    ).toThrow(/loopback/);
  });

  it("does not expose raw shell or raw MA command tools", () => {
    const names = getToolPluginMetadata(entry)?.tools.map((tool) => tool.name) ?? [];
    expect(names.some((name) => /shell|exec|telnet|raw_ma|command/i.test(name))).toBe(false);
  });
});
