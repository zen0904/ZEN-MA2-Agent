import { describe, expect, it } from "vitest";
import entry from "./index.js";
import { getToolPluginMetadata } from "openclaw/plugin-sdk/tool-plugin";

describe("zen-ma2", () => {
  it("declares the bounded ZEN tool surface", () => {
    expect(getToolPluginMetadata(entry)?.tools.map((tool) => tool.name)).toEqual([
      "zen_status",
      "zen_ma_status",
      "zen_ma_visual",
      "zen_design_request",
      "zen_preview",
      "zen_position_preview",
      "zen_position_raw_preview",
      "zen_position_calibration_preview",
      "zen_approve",
      "zen_worker_status",
      "zen_watchdog_status",
      "zen_host_status",
    ]);
  });

  it("does not expose raw shell or raw MA command tools", () => {
    const names = getToolPluginMetadata(entry)?.tools.map((tool) => tool.name) ?? [];
    expect(names.some((name) => /shell|exec|telnet|raw_ma|command/i.test(name))).toBe(false);
  });
});
