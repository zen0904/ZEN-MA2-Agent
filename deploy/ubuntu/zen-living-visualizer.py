#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

OPS_PUBLIC = Path("/var/lib/zen-ops/public")

STATIONS = {
    "lounge": {"name": "Rest Lounge", "x": 10, "y": 80},
    "research": {"name": "Browser / Research", "x": 12, "y": 18},
    "logs": {"name": "Logs / Monitoring", "x": 30, "y": 16},
    "terminal": {"name": "Terminal", "x": 45, "y": 16},
    "files": {"name": "File Storage", "x": 60, "y": 16},
    "coding": {"name": "Coding", "x": 76, "y": 18},
    "github": {"name": "Git / GitHub", "x": 88, "y": 32},
    "api": {"name": "AI Model / API", "x": 88, "y": 56},
    "compute": {"name": "GPU / Compute", "x": 86, "y": 80},
    "vision": {"name": "Vision", "x": 68, "y": 80},
    "ma": {"name": "MA Bridge / ZEN Operator", "x": 46, "y": 82},
    "sandbox": {"name": "Sandbox / OpenShell", "x": 28, "y": 80},
    "openclaw": {"name": "OpenClaw", "x": 12, "y": 54},
    "network": {"name": "Network / SSH", "x": 12, "y": 36},
    "approval": {"name": "Approval Gate", "x": 55, "y": 52},
    "zen": {"name": "ZEN Core", "x": 35, "y": 52},
}

HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZEN Living System Visualizer</title>
<style>
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#eef3f8;background:#091018}
*{box-sizing:border-box}
body{margin:0;overflow:hidden;background:radial-gradient(circle at 30% 20%,#142231 0,#091018 52%,#060a0f 100%)}
#app{height:100vh;display:grid;grid-template-rows:52px 1fr}
.top{display:flex;align-items:center;gap:18px;padding:0 18px;border-bottom:1px solid #243442;background:rgba(7,12,18,.92);backdrop-filter:blur(8px)}
.brand{font-weight:800;letter-spacing:.08em}
.pill{font-size:12px;padding:5px 9px;border:1px solid #334a5d;border-radius:999px;color:#bcd0df}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:#667}
.dot.on{background:#58d68d;box-shadow:0 0 12px #58d68d}
.main{display:grid;grid-template-columns:minmax(0,1fr) 330px;min-height:0}
.workspace{position:relative;overflow:hidden;background-image:linear-gradient(rgba(255,255,255,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.022) 1px,transparent 1px);background-size:32px 32px}
.workspace:after{content:"";position:absolute;inset:2.5%;border:1px solid #243746;border-radius:26px;pointer-events:none}
.station{position:absolute;transform:translate(-50%,-50%);min-width:115px;padding:11px 12px;border-radius:14px;border:1px solid #345066;background:linear-gradient(180deg,rgba(24,39,52,.96),rgba(15,26,36,.96));box-shadow:0 8px 24px rgba(0,0,0,.28);text-align:center;font-size:12px;color:#bdd0de;transition:.3s}
.station.busy{border-color:#64d99b;box-shadow:0 0 0 1px rgba(100,217,155,.24),0 0 24px rgba(60,205,139,.18)}
.station .name{font-weight:700;color:#edf5fb}
.station .busy-label{margin-top:3px;font-size:10px;color:#61d99c;min-height:13px}
.avatar{position:absolute;transform:translate(-50%,-50%);transition:left .9s cubic-bezier(.2,.8,.2,1),top .9s cubic-bezier(.2,.8,.2,1);z-index:5;cursor:pointer}
.avatar .body{width:44px;height:44px;border-radius:14px;background:linear-gradient(145deg,#d8e3ec,#8297a8);border:2px solid #f1f6fa;box-shadow:0 8px 18px rgba(0,0,0,.35);display:flex;align-items:center;justify-content:center;color:#0b141d;font-size:12px;font-weight:900}
.avatar.working .body{box-shadow:0 0 0 3px rgba(100,217,155,.3),0 0 22px rgba(100,217,155,.42);animation:pulse 1.1s ease-in-out infinite alternate}
.avatar.error .body{box-shadow:0 0 0 3px rgba(255,100,100,.32),0 0 24px rgba(255,80,80,.35)}
.avatar.idle .body{animation:idle 2.8s ease-in-out infinite}
.avatar .label{position:absolute;left:50%;top:49px;transform:translateX(-50%);white-space:nowrap;background:rgba(4,8,12,.78);border:1px solid #2a3c4b;border-radius:8px;padding:3px 7px;font-size:10px;color:#dbe7ef}
.avatar .bubble{position:absolute;left:50%;bottom:51px;transform:translateX(-50%);max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;background:#f3f8fb;color:#12202c;border-radius:10px;padding:4px 7px;font-size:9px;opacity:0;transition:.2s}
.avatar.working .bubble,.avatar.error .bubble{opacity:1}
@keyframes idle{from{transform:translate(-50%,-50%) translateY(0)}50%{transform:translate(-50%,-50%) translateY(-3px)}to{transform:translate(-50%,-50%) translateY(0)}}
@keyframes pulse{from{transform:scale(.98)}to{transform:scale(1.03)}}
.side{border-left:1px solid #243442;background:rgba(8,14,20,.94);display:grid;grid-template-rows:auto auto 1fr;min-height:0}
.section{padding:14px 15px;border-bottom:1px solid #1f303d}
.section h3{margin:0 0 10px;font-size:12px;letter-spacing:.07em;color:#96acbc;text-transform:uppercase}
.task{font-size:13px;line-height:1.45;color:#edf4f8}
.task .muted{color:#8199aa;font-size:11px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.stat{padding:9px;border:1px solid #273c4c;border-radius:10px;background:#0e1821}
.stat b{display:block;font-size:11px;color:#88a1b2}.stat span{font-size:14px}
.events{overflow:auto;padding:12px 14px}
.event{padding:9px 2px;border-bottom:1px solid #1a2934;font-size:11px;line-height:1.35}
.event .time{color:#718797}.event .type{color:#66d69a;font-weight:700;margin:0 6px}.event.error .type{color:#ff7b7b}
.legend{position:absolute;left:20px;bottom:16px;font-size:10px;color:#6e8798;background:rgba(4,8,12,.62);border:1px solid #263947;border-radius:10px;padding:7px 9px;z-index:4}
</style>
</head>
<body>
<div id="app">
  <div class="top">
    <div class="brand">ZEN LIVING SYSTEM</div>
    <div class="pill"><span id="liveDot" class="dot"></span><span id="liveText">CONNECTING</span></div>
    <div class="pill" id="host">zen-agent-server</div>
    <div class="pill">OBSERVATION ONLY</div>
  </div>
  <div class="main">
    <div id="workspace" class="workspace"><div class="legend">real runtime state → station occupancy → avatar movement</div></div>
    <div class="side">
      <div class="section"><h3>Current Task</h3><div id="task" class="task">No active task</div></div>
      <div class="section"><h3>System</h3><div id="stats" class="stats"></div></div>
      <div class="events" id="events"></div>
    </div>
  </div>
</div>
<script>
const workspace=document.getElementById('workspace');
let stations={}, avatars={};
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function ensureStation(id,s){
 if(stations[id]) return stations[id];
 const el=document.createElement('div'); el.className='station'; el.dataset.id=id;
 el.style.left=s.x+'%'; el.style.top=s.y+'%';
 el.innerHTML='<div class="name">'+esc(s.name)+'</div><div class="busy-label"></div>';
 workspace.appendChild(el); stations[id]=el; return el;
}
function initials(name){return name.split(/\s+/).map(x=>x[0]).join('').slice(0,3).toUpperCase()}
function ensureAvatar(a){
 if(avatars[a.id]) return avatars[a.id];
 const el=document.createElement('div'); el.className='avatar idle'; el.dataset.id=a.id;
 el.innerHTML='<div class="bubble"></div><div class="body">'+esc(initials(a.name))+'</div><div class="label">'+esc(a.name)+'</div>';
 el.onclick=()=>showAgent(a.id);
 workspace.appendChild(el); avatars[a.id]=el; return el;
}
let lastState=null, selected=null;
function showAgent(id){selected=id; if(lastState) renderTask(lastState)}
function renderTask(s){
 const a=selected ? s.agents.find(x=>x.id===selected) : s.agents.find(x=>x.status==='WORKING'||x.status==='ERROR');
 const t=document.getElementById('task');
 if(!a){t.innerHTML='No active task<div class="muted">Agents are idle / monitoring.</div>';return}
 t.innerHTML='<b>'+esc(a.name)+'</b> · '+esc(a.status)+'<br>'+esc(a.task||'No active task')+'<div class="muted">station: '+esc(s.stations[a.station]?.name||a.station)+'</div>';
}
function render(s){
 lastState=s;
 document.getElementById('liveDot').className='dot on';
 document.getElementById('liveText').textContent='LIVE';
 document.getElementById('host').textContent=s.host||'zen-agent-server';
 Object.entries(s.stations).forEach(([id,st])=>ensureStation(id,st));
 Object.values(stations).forEach(el=>{el.classList.remove('busy');el.querySelector('.busy-label').textContent=''});
 const occupied={};
 s.agents.forEach(a=>{ if(a.status==='WORKING'||a.status==='ERROR'||a.status==='WAITING'){occupied[a.station]=(occupied[a.station]||[]).concat(a.name)} });
 Object.entries(occupied).forEach(([id,names])=>{if(stations[id]){stations[id].classList.add('busy');stations[id].querySelector('.busy-label').textContent=names.join(', ')}});
 s.agents.forEach(a=>{
   const el=ensureAvatar(a), st=s.stations[a.station]||s.stations.lounge;
   el.style.left=st.x+'%'; el.style.top=st.y+'%';
   el.className='avatar '+(a.status==='WORKING'?'working':a.status==='ERROR'?'error':'idle');
   el.querySelector('.bubble').textContent=a.task||a.status;
   el.querySelector('.label').textContent=a.name+' · '+a.status;
 });
 const stats=document.getElementById('stats'); stats.innerHTML='';
 Object.entries(s.system||{}).forEach(([k,v])=>{const d=document.createElement('div');d.className='stat';d.innerHTML='<b>'+esc(k)+'</b><span>'+esc(v)+'</span>';stats.appendChild(d)});
 const ev=document.getElementById('events'); ev.innerHTML='<h3 style="margin:0 0 8px;font-size:12px;color:#96acbc">EVENT STREAM</h3>';
 (s.events||[]).slice().reverse().forEach(e=>{const d=document.createElement('div');d.className='event '+(e.status==='failed'||e.type==='ERROR'?'error':'');d.innerHTML='<span class="time">'+esc(e.time||'')+'</span><span class="type">'+esc(e.type)+'</span>'+esc(e.summary||'');ev.appendChild(d)});
 renderTask(s);
}
async function tick(){
 try{const r=await fetch('/api/state?ts='+Date.now(),{cache:'no-store'}); if(!r.ok)throw new Error('HTTP '+r.status); render(await r.json())}
 catch(e){document.getElementById('liveDot').className='dot';document.getElementById('liveText').textContent='DISCONNECTED'}
}
tick(); setInterval(tick,1000);
</script>
</body></html>"""

def sh(argv: list[str], timeout: float = 1.5) -> str:
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        return p.stdout.strip()
    except Exception:
        return ""

def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}

def service(name: str) -> str:
    value = sh(["systemctl", "is-active", name], 0.8)
    return value or "unknown"

def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.08):
            return True
    except OSError:
        return False

def process_snapshot() -> str:
    return sh(["ps", "-eo", "args"], 1.0).lower()

def station_for(text: str, status: str) -> str:
    t = text.lower()
    if status == "waiting_for_approval" or "approval" in t:
        return "approval"
    if status in {"failed", "error", "timeout", "rejected"}:
        return "logs"
    rules = [
        ("github", ("github", " git ", "commit", "push", "pull request")),
        ("research", ("browser", "web", "research", "crawl", "search")),
        ("coding", ("codex", "coding", "code", "pytest", "build")),
        ("vision", ("vision", "image", "video", "gdtf", "mvr")),
        ("ma", ("ma bridge", "grandma", "ma2", "ma3", "lighting", "operator")),
        ("openclaw", ("openclaw",)),
        ("network", ("ssh", "tailscale", "gateway", "network")),
        ("files", ("file", "storage", "drive", "document")),
        ("api", ("api", "provider", "model", "openai", "qwen", "claude", "gpt")),
        ("sandbox", ("sandbox", "openshell")),
        ("logs", ("log", "journal", "monitor", "status")),
    ]
    for station, needles in rules:
        if any(n in t for n in needles):
            return station
    return "terminal"

def normalized_events(limit: int = 24) -> list[dict[str, str]]:
    data = read_json(OPS_PUBLIC / "activity.json")
    raw = data.get("events") if isinstance(data.get("events"), list) else []
    out: list[dict[str, str]] = []
    for item in raw[-limit:]:
        if not isinstance(item, dict):
            continue
        event = str(item.get("event") or "WORK")
        status = str(item.get("status") or "")
        if event == "WORK_START":
            typ = "TOOL_STARTED"
        elif event == "WORK_END" and status == "completed":
            typ = "TASK_COMPLETE"
        elif event == "WORK_END":
            typ = "TOOL_FAILED"
        else:
            typ = event
        stamp = str(item.get("time") or "")
        try:
            dt = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone()
            stamp = dt.strftime("%H:%M:%S")
        except Exception:
            pass
        out.append({
            "time": stamp,
            "type": typ,
            "status": status,
            "actor": str(item.get("actor") or "ZEN"),
            "summary": str(item.get("summary") or item.get("job_id") or ""),
        })
    return out

def mem_summary() -> str:
    try:
        rows = Path("/proc/meminfo").read_text().splitlines()
        vals = {}
        for line in rows:
            if ":" in line:
                k, v = line.split(":", 1)
                vals[k] = int(v.strip().split()[0])
        total = vals.get("MemTotal", 0)
        avail = vals.get("MemAvailable", 0)
        used = max(0, total - avail)
        if total:
            return f"{used/1048576:.1f}/{total/1048576:.1f} GiB"
    except Exception:
        pass
    return "unknown"

def load_summary() -> str:
    try:
        a, b, c = os.getloadavg()
        return f"{a:.2f} {b:.2f} {c:.2f}"
    except Exception:
        return "unknown"

def build_state() -> dict[str, Any]:
    latest = read_json(OPS_PUBLIC / "latest.json")
    proc = process_snapshot()
    status = str(latest.get("status") or "idle").lower()
    meta = latest.get("meta") if isinstance(latest.get("meta"), dict) else {}
    summary = str(meta.get("summary") or latest.get("job_id") or "No active task")
    tools = [str(x) for x in meta.get("tools", [])] if isinstance(meta.get("tools"), list) else []
    text = " ".join([summary, " ".join(tools), str(latest.get("kind") or "")])
    running = status == "running"

    agents: list[dict[str, str]] = []
    zen_station = station_for(text, status) if running else "lounge"
    agents.append({"id":"zen","name":"ZEN Agent","status":"WORKING" if running else ("ERROR" if status in {"failed","timeout","rejected"} else "IDLE"),"station":zen_station,"task":summary if running or status in {"failed","timeout","rejected"} else ""})
    agents.append({"id":"ops","name":"ZEN Ops","status":"WORKING" if running else "IDLE","station":station_for(text,status) if running else "zen","task":summary if running else ""})
    agents.append({"id":"openclaw","name":"OpenClaw","status":"IDLE" if port_open(18789) else "ERROR","station":"openclaw" if port_open(18789) else "logs","task":"Gateway active" if port_open(18789) else "Gateway unavailable"})

    codex = any(x in proc for x in (" codex ", "codex exec", "@openai/codex", "codex-linux"))
    agents.append({"id":"coding","name":"Coding Agent","status":"WORKING" if codex else "IDLE","station":"coding" if codex else "lounge","task":"Code task visible in process table" if codex else ""})

    research = running and any(x in text.lower() for x in ("web","browser","research","search","crawl"))
    agents.append({"id":"research","name":"Research Agent","status":"WORKING" if research else "IDLE","station":"research" if research else "lounge","task":summary if research else ""})

    git_active = running and any(x in text.lower() for x in ("git","github","commit","push"))
    agents.append({"id":"git","name":"Git Worker","status":"WORKING" if git_active else "IDLE","station":"github" if git_active else "lounge","task":summary if git_active else ""})

    vision_active = running and any(x in text.lower() for x in ("vision","image","video","gdtf","mvr"))
    agents.append({"id":"vision","name":"Vision Agent","status":"WORKING" if vision_active else "IDLE","station":"vision" if vision_active else "lounge","task":summary if vision_active else ""})

    # Provider avatars require explicit task/runtime metadata. Do not infer\n    # provider activity from the resident ChatGPT GUI process name.\n    provider_text = text.lower()
    for aid, name, keys in (
        ("gpt","GPT Provider",("openai","gpt")),
        ("qwen","Qwen Provider",("qwen",)),
        ("claude","Claude Provider",("claude",)),
    ):
        active = running and any(k in provider_text for k in keys)
        agents.append({"id":aid,"name":name,"status":"WORKING" if active else "IDLE","station":"api" if active else "lounge","task":summary if active else ""})

    system = {
        "ZEN Ops": service("zen-ops-worker"),
        "OpenClaw": "active" if port_open(18789) else "down",
        "Tailscale": service("tailscaled"),
        "RDC": service("desktop-commander-remote"),
        "ChatGPT GUI": service("zen-chatgpt-desktop"),
        "Load": load_summary(),
        "Memory": mem_summary(),
    }
    return {
        "schema":"zen.living_visualizer.state.v0.1",
        "host": socket.gethostname(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "stations": STATIONS,
        "agents": agents,
        "events": normalized_events(),
        "system": system,
        "authority":"OBSERVATION_ONLY",
    }

class Handler(BaseHTTPRequestHandler):
    server_version = "ZENLivingVisualizer/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_bytes(self, code: int, content_type: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-ZEN-Authority", "observation-only")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.send_bytes(200, "text/html; charset=utf-8", HTML.encode("utf-8"))
            return
        if path == "/health":
            body = json.dumps({"status":"ok","authority":"observation-only","schema":"zen.living_visualizer.health.v0.1"}).encode()
            self.send_bytes(200, "application/json", body)
            return
        if path == "/api/state":
            body = json.dumps(build_state(), ensure_ascii=False).encode("utf-8")
            self.send_bytes(200, "application/json; charset=utf-8", body)
            return
        self.send_bytes(404, "application/json", b'{"error":"not_found"}')

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18992)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
