from zen_ma2_agent.core import AgentCore
from zen_ma2_agent.desktop import run_desktop
from zen_ma2_agent.web_server import MobileServer


def main() -> int:
    core = AgentCore()
    mobile = core.runtime.preferences.get("mobile", {})
    server = MobileServer(core, int(mobile.get("port", 8765)))
    if mobile.get("enabled", True):
        server.start()
    try:
        return run_desktop(core, server)
    finally:
        server.stop()


if __name__ == "__main__":
    raise SystemExit(main())
