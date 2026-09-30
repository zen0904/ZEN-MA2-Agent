#!/usr/bin/env python3
from __future__ import annotations

import curses
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

OPS_PUBLIC = Path("/var/lib/zen-ops/public")
RUNTIME = Path("/opt/zen/zen-ops-runtime")
REGISTRY_PATHS = (
    RUNTIME / "data/ZEN_RUNTIME_ENTITY_REGISTRY.json",
    OPS_PUBLIC / "entity-registry.json",
    OPS_PUBLIC / "registry.json",
)
STATE_MAP_PATH = RUNTIME / "data/ZEN_TUI_STATE_MAP.json"

KNOWN_KINDS = {"provider", "agent", "tool", "service"}
PRIORITY = {"error": 0, "waiting": 1, "active": 2, "unknown": 3, "idle": 4}
ACCENT_256 = (180, 181, 151, 145, 110, 174, 109, 187)


@dataclass
class Entity:
    kind: str
    id: str
    name: str
    state: str
    raw_state: str
    group: str | None = None
    parent: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    display: dict[str, Any] = field(default_factory=dict)
    state_since: float = 0.0
    parse_error: str | None = None


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run(argv: list[str], timeout: float = 0.8) -> str:
    try:
        p = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        return p.stdout.strip()
    except Exception:
        return ""


def tcp_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.08):
            return True
    except OSError:
        return False


def load_state_map() -> dict[str, str]:
    data = read_json(STATE_MAP_PATH)
    raw = data.get("map", {}) if isinstance(data, dict) else {}
    return {str(k).lower(): str(v).lower() for k, v in raw.items()}


def normalize_state(raw: Any, state_map: dict[str, str]) -> str:
    value = str(raw if raw is not None else "unknown").strip().lower().replace("-", "_").replace(" ", "_")
    mapped = state_map.get(value)
    return mapped if mapped in PRIORITY else "unknown"


def registry_entries() -> tuple[list[dict[str, Any]], list[str]]:
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    errors: list[str] = []
    for path in REGISTRY_PATHS:
        if not path.exists():
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            errors.append(f"{path.name}: invalid JSON root")
            continue

        candidates: list[tuple[str | None, Any]] = []
        if isinstance(data.get("entities"), list):
            candidates.extend((None, x) for x in data["entities"])

        for plural, kind in (("providers", "provider"), ("agents", "agent"), ("tools", "tool"), ("services", "service")):
            value = data.get(plural)
            if isinstance(value, list):
                candidates.extend((kind, x) for x in value)

        for hinted_kind, item in candidates:
            if not isinstance(item, dict):
                errors.append(f"{path.name}: non-object registry entry")
                continue
            kind = str(item.get("kind") or hinted_kind or "unknown").strip().lower()
            ident = str(item.get("id") or "").strip()
            if not ident:
                errors.append(f"{path.name}: missing id for kind={kind}")
                continue
            copy = dict(item)
            copy["kind"] = kind
            entries[(kind, ident)] = copy
    return list(entries.values()), errors


def latest_activity() -> dict[str, Any]:
    latest = read_json(OPS_PUBLIC / "latest.json")
    if not isinstance(latest, dict):
        latest = {}
    meta = latest.get("meta") if isinstance(latest.get("meta"), dict) else {}
    tools = meta.get("tools") if isinstance(meta.get("tools"), list) else []
    return {
        "job_id": str(latest.get("job_id") or ""),
        "status": str(latest.get("status") or "idle"),
        "summary": str(meta.get("summary") or latest.get("job_id") or ""),
        "tools": [str(x) for x in tools],
        "kind": str(latest.get("kind") or ""),
        "actor": str(meta.get("actor") or ""),
    }


def service_state(check: dict[str, Any]) -> str:
    typ = str(check.get("type") or "").lower()
    if typ == "systemd":
        name = str(check.get("name") or "")
        return "active" if run(["systemctl", "is-active", name]) == "active" else "error"
    if typ == "tcp":
        host = str(check.get("host") or "127.0.0.1")
        try:
            port = int(check.get("port"))
        except Exception:
            return "unknown"
        return "active" if tcp_open(host, port) else "error"
    return "unknown"


def aliases(item: dict[str, Any]) -> list[str]:
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    values = meta.get("aliases")
    if isinstance(values, list):
        return [str(x).lower() for x in values if str(x).strip()]
    return []


def build_entities(state_map: dict[str, str], activity: dict[str, Any], state_clock: dict[tuple[str, str], tuple[str, float]]) -> list[Entity]:
    rows, parse_errors = registry_entries()
    hay = " ".join([
        activity["job_id"], activity["summary"], activity["kind"], activity["actor"], " ".join(activity["tools"])
    ]).lower()
    activity_state = normalize_state(activity["status"], state_map)
    entities: list[Entity] = []

    for item in rows:
        kind = str(item.get("kind") or "unknown").lower()
        ident = str(item.get("id") or "")
        name = str((item.get("display") or {}).get("label") if isinstance(item.get("display"), dict) else "" or item.get("name") or ident)
        group = item.get("group")
        parent = item.get("parent")
        meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
        display = item.get("display") if isinstance(item.get("display"), dict) else {}

        raw = str(item.get("state") or "unknown")
        check = meta.get("check") if isinstance(meta.get("check"), dict) else None
        if check:
            raw = service_state(check)
        else:
            hits = aliases(item)
            matched = bool(hits and any(x in hay for x in hits))
            if kind in {"provider", "tool"}:
                raw = "active" if activity_state == "active" and matched else raw
            elif kind == "agent":
                if ident in {"zen", "ops"}:
                    raw = activity_state if activity_state in {"active", "waiting", "error"} else raw
                elif activity_state == "active" and matched:
                    raw = "active"

        state = normalize_state(raw, state_map)
        key = (kind, ident)
        previous = state_clock.get(key)
        if previous is None or previous[0] != state:
            state_clock[key] = (state, time.time())
        since = state_clock[key][1]

        err = None
        if kind not in KNOWN_KINDS:
            err = f"unknown kind: {kind}"
        elif state == "unknown":
            err = f"unknown state: {raw}"
        elif not group:
            err = "missing group"

        entities.append(Entity(kind, ident, name, state, raw, str(group) if group else None,
                               str(parent) if parent else None, meta, display, since, err))

    for index, message in enumerate(parse_errors, 1):
        entities.append(Entity("unknown", f"parse-error-{index}", "Registry entry", "unknown", "parse_error",
                               "other", None, {"reason": message}, {}, time.time(), message))

    return sorted(entities, key=lambda e: (PRIORITY.get(e.state, 99), -e.state_since, e.kind, e.id))


class Telemetry:
    def __init__(self) -> None:
        self.cpu_prev: tuple[int, int] | None = None
        self.net_prev: tuple[float, int, int] | None = None

    def cpu(self) -> str:
        try:
            vals = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            total = sum(vals)
            prev = self.cpu_prev
            self.cpu_prev = (total, idle)
            if not prev:
                return "--"
            dt = total - prev[0]
            di = idle - prev[1]
            return f"{max(0,min(100,100*(1-di/dt))):.0f}%" if dt > 0 else "0%"
        except Exception:
            return "N/A"

    def temp(self) -> str:
        vals: list[float] = []
        try:
            for z in Path("/sys/class/thermal").glob("thermal_zone*"):
                try:
                    typ = (z/"type").read_text().strip().lower()
                    raw = float((z/"temp").read_text().strip())
                    v = raw/1000 if abs(raw)>1000 else raw
                    if -20 <= v <= 130 and any(k in typ for k in ("x86_pkg_temp","coretemp","package")):
                        vals.append(v)
                except Exception:
                    pass
        except Exception:
            pass
        return f"{max(vals):.0f}°C" if vals else "N/A"

    def memory(self) -> str:
        try:
            rows = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k,v=line.split(":",1); rows[k]=int(v.strip().split()[0])
            total=rows["MemTotal"]; used=total-rows.get("MemAvailable",0)
            return f"{used/1048576:.1f} / {total/1048576:.1f} GB"
        except Exception:
            return "N/A"

    def disk(self) -> str:
        try:
            st=os.statvfs("/"); total=st.f_frsize*st.f_blocks; free=st.f_frsize*st.f_bavail
            return f"{(total-free)/(1024**3):.0f} / {total/(1024**3):.0f} GB"
        except Exception:
            return "N/A"

    def fan(self) -> str:
        for h in Path("/sys/class/hwmon").glob("hwmon*"):
            try:
                if "applesmc" not in (h/"name").read_text().strip().lower():
                    continue
                vals=[int(float(p.read_text().strip())) for p in h.glob("fan*_input")]
                if vals:
                    return f"{max(vals)} RPM"
            except Exception:
                pass
        return "N/A"

    def default_if(self) -> str:
        try:
            for line in Path("/proc/net/route").read_text().splitlines()[1:]:
                f=line.split()
                if len(f)>=4 and f[1]=="00000000" and int(f[3],16)&2:
                    return f[0]
        except Exception:
            pass
        return "N/A"

    def network(self) -> tuple[str, str, str]:
        iface=self.default_if()
        if iface=="N/A":
            return iface,"N/A","N/A"
        try:
            rx=tx=0
            for line in Path("/proc/net/dev").read_text().splitlines():
                if ":" not in line: continue
                name,data=line.split(":",1)
                if name.strip()==iface:
                    f=data.split(); rx=int(f[0]); tx=int(f[8]); break
            now=time.monotonic(); prev=self.net_prev; self.net_prev=(now,rx,tx)
            if not prev or now<=prev[0]:
                return iface,"--","--"
            dt=now-prev[0]
            return iface,self.rate((rx-prev[1])/dt),self.rate((tx-prev[2])/dt)
        except Exception:
            return iface,"N/A","N/A"

    @staticmethod
    def rate(v: float) -> str:
        units=("B/s","KB/s","MB/s","GB/s"); i=0; v=max(0.0,v)
        while v>=1024 and i<len(units)-1:
            v/=1024; i+=1
        return f"{v:.1f} {units[i]}"

    def uptime(self) -> str:
        try:
            sec=int(float(Path("/proc/uptime").read_text().split()[0])); d,sec=divmod(sec,86400); h,sec=divmod(sec,3600); m=sec//60
            return f"{d}d {h}h" if d else f"{h}h {m}m"
        except Exception:
            return "N/A"

    def load(self) -> str:
        try:
            return " ".join(f"{x:.2f}" for x in os.getloadavg())
        except Exception:
            return "N/A"


def stable_accent(entity: Entity) -> int:
    raw=(entity.group or entity.kind).encode("utf-8")
    return ACCENT_256[int.from_bytes(hashlib.blake2b(raw,digest_size=2).digest(),"big") % len(ACCENT_256)]


class App:
    def __init__(self, stdscr: Any) -> None:
        self.s=stdscr
        self.mode="living"
        self.selected=0
        self.expanded_idle=False
        self.state_clock: dict[tuple[str,str],tuple[str,float]]={}
        self.state_map=load_state_map()
        self.telemetry=Telemetry()
        self.last_payload=""
        self.last_draw=0.0
        self.force=True
        self.setup_colors()

    def setup_colors(self) -> None:
        curses.curs_set(0)
        curses.use_default_colors()
        self.s.keypad(True)
        self.s.timeout(500)
        if curses.has_colors():
            curses.start_color()
            colors = curses.COLORS
            def pair(n:int, fg:int) -> None:
                curses.init_pair(n, fg if fg < colors else curses.COLOR_WHITE, -1)
            pair(1,223); pair(2,245); pair(3,180); pair(4,167); pair(5,108); pair(6,110); pair(7,174)
            for i,c in enumerate(ACCENT_256,20): pair(i,c)

    def attr(self, name:str, entity:Entity|None=None) -> int:
        if not curses.has_colors(): return 0
        if name=="title": return curses.color_pair(1)|curses.A_BOLD
        if name=="muted": return curses.color_pair(2)
        if name=="waiting": return curses.color_pair(3)
        if name=="error": return curses.color_pair(4)
        if name=="active": return curses.color_pair(5)
        if name=="unknown": return curses.color_pair(7)
        if entity:
            return curses.color_pair(20 + (ACCENT_256.index(stable_accent(entity))))
        return 0

    def put(self,y:int,x:int,text:str,attr:int=0,maxw:int|None=None) -> None:
        h,w=self.s.getmaxyx()
        if y<0 or y>=h or x>=w: return
        text=str(text).replace("\t","  ")
        if maxw is None: maxw=w-x-1
        try:self.s.addnstr(y,x,text,max(0,maxw),attr)
        except curses.error: pass

    def divider(self,y:int,label:str="") -> None:
        _,w=self.s.getmaxyx()
        if label:
            left=max(2,(w-len(label)-2)//2)
            self.put(y,0,"─"*left,self.attr("muted"))
            self.put(y,left+1,label,self.attr("muted"))
            self.put(y,left+len(label)+2,"─"*max(0,w-left-len(label)-3),self.attr("muted"))
        else:self.put(y,0,"─"*(w-1),self.attr("muted"))

    def state_mark(self,e:Entity) -> tuple[str,int]:
        return {
            "error":("×",self.attr("error")),
            "waiting":("◐",self.attr("waiting")),
            "active":("●",self.attr("active")),
            "unknown":("?",self.attr("unknown")),
            "idle":("○",self.attr("muted")),
        }.get(e.state,("?",self.attr("unknown")))

    def collect(self) -> dict[str,Any]:
        act=latest_activity()
        entities=build_entities(self.state_map,act,self.state_clock)
        iface,rx,tx=self.telemetry.network()
        sys={
            "CPU":self.telemetry.cpu(),"Temp":self.telemetry.temp(),"Memory":self.telemetry.memory(),
            "Disk":self.telemetry.disk(),"Fan":self.telemetry.fan(),"IF":iface,"RX":rx,"TX":tx,
            "Uptime":self.telemetry.uptime(),"Load":self.telemetry.load(),
        }
        return {"activity":act,"entities":entities,"system":sys}

    def header(self,data:dict[str,Any],row:int) -> int:
        ents=data["entities"]; counts={k:sum(e.state==k for e in ents) for k in PRIORITY}
        self.put(row,2,"ZEN",self.attr("title")); self.put(row,7,"Living Workspace",self.attr("muted"))
        right=f"{self.mode.upper()}   ×{counts['error']}  ◐{counts['waiting']}  ●{counts['active']}  ○{counts['idle']}"
        _,w=self.s.getmaxyx(); self.put(row,max(2,w-len(right)-2),right,self.attr("muted"))
        return row+2

    def current(self,data:dict[str,Any],row:int,compact:bool=False) -> int:
        a=data["activity"]; status=normalize_state(a["status"],self.state_map)
        self.put(row,2,"Current",self.attr("title")); row+=1
        if a["job_id"]:
            mark={"active":"●","waiting":"◐","error":"×"}.get(status,"○")
            at={"active":self.attr("active"),"waiting":self.attr("waiting"),"error":self.attr("error")}.get(status,self.attr("muted"))
            self.put(row,4,f"{mark} {a['summary'] or a['job_id']}",at); row+=1
            if not compact:
                self.put(row,6,f"{a['actor'] or 'ZEN'}  ·  {a['kind'] or 'task'}  ·  {a['status']}",self.attr("muted")); row+=1
        else:
            self.put(row,4,"○ No active task",self.attr("muted")); row+=1
        return row+1

    def attention(self,data:dict[str,Any],row:int) -> int:
        items=[e for e in data["entities"] if e.state in {"error","waiting","unknown"}]
        self.put(row,2,"Attention",self.attr("title")); row+=1
        if not items:
            self.put(row,4,"No blockers",self.attr("muted")); return row+2
        for e in items[:5]:
            mark,at=self.state_mark(e); detail=e.parse_error or e.raw_state
            self.put(row,4,f"{mark} {e.name:<18} {detail}",at); row+=1
        return row+1

    def activity(self,data:dict[str,Any],row:int,max_items:int=8) -> int:
        items=[e for e in data["entities"] if e.state=="active" and e.kind!="provider"]
        self.put(row,2,"Activity",self.attr("title")); row+=1
        if not items:
            self.put(row,4,"Quiet",self.attr("muted")); return row+2
        for e in items[:max_items]:
            mark,at=self.state_mark(e); parent=f"  ↳ {e.parent}" if e.parent else ""
            self.put(row,4,f"{mark} {e.name:<18} {e.kind}{parent}",at); row+=1
        return row+1

    def providers(self,data:dict[str,Any],row:int) -> int:
        items=[e for e in data["entities"] if e.kind=="provider"]
        items.sort(key=lambda e:(PRIORITY.get(e.state,9),e.name.lower()))
        self.put(row,2,"Providers",self.attr("title")); row+=1
        visible=[e for e in items if e.state!="idle"] + ([e for e in items if e.state=="idle"] if self.expanded_idle else [])
        for e in visible[:8]:
            mark,at=self.state_mark(e)
            self.put(row,4,f"{mark} {e.name:<18} {e.state}",at); row+=1
        idle=sum(e.state=="idle" for e in items)
        if idle and not self.expanded_idle:
            self.put(row,4,f"▸ + {idle} idle providers   [Enter] expand",self.attr("muted")); row+=1
        return row+1

    def approval(self,data:dict[str,Any],row:int) -> int:
        a=data["activity"]; waiting=normalize_state(a["status"],self.state_map)=="waiting"
        self.divider(row,"approval boundary"); row+=1
        self.put(row,2,"◐ WAITING FOR APPROVAL" if waiting else "No task waiting",
                 self.attr("waiting") if waiting else self.attr("muted")); return row+2

    def system(self,data:dict[str,Any],row:int,wide:bool) -> int:
        s=data["system"]; self.put(row,2,"System",self.attr("title")); row+=1
        if wide:
            self.put(row,4,f"CPU     {s['CPU']:<7} {s['Temp']:<7}   Memory  {s['Memory']}",0); row+=1
            self.put(row,4,f"Disk    {s['Disk']:<18}  Fan     {s['Fan']}",0); row+=1
            self.put(row,4,f"Network {s['IF']:<10} ↓ {s['RX']:<12} ↑ {s['TX']}",0); row+=1
            self.put(row,4,f"Uptime  {s['Uptime']:<12} Load {s['Load']}   GPU Usage N/A · Temp No Sensor",self.attr("muted")); row+=1
        else:
            self.put(row,4,f"CPU {s['CPU']} {s['Temp']}  RAM {s['Memory']}",0); row+=1
            self.put(row,4,f"↓ {s['RX']}  ↑ {s['TX']}  {s['IF']}",0); row+=1
        return row+1

    def diagnostic(self,data:dict[str,Any],row:int) -> int:
        self.put(row,2,"Entities",self.attr("title")); row+=1
        for e in data["entities"][:12]:
            mark,at=self.state_mark(e)
            self.put(row,4,f"{mark} {e.kind:<9} {e.name:<20} {e.state:<8} {e.group or 'unassigned'}",at); row+=1
        return row

    def footer(self,row:int) -> None:
        h,w=self.s.getmaxyx(); text="1 Living   2 Control   3 Diagnostic   Enter Expand   q Quit"
        self.put(h-2,max(2,(w-len(text))//2),text,self.attr("muted"))

    def render(self,data:dict[str,Any]) -> None:
        self.s.erase(); h,w=self.s.getmaxyx(); compact=w<92 or h<28
        row=self.header(data,1)
        if self.mode=="living":
            row=self.current(data,row,compact)
            if not compact: row=self.attention(data,row)
            row=self.activity(data,row,5 if compact else 8)
            if row<h-10: row=self.providers(data,row)
            if row<h-7: row=self.approval(data,row)
            if row<h-3: row=self.system(data,row,w>=105)
        elif self.mode=="control":
            row=self.current(data,row,False)
            row=self.activity(data,row,10)
            row=self.providers(data,row)
            row=self.approval(data,row)
            if row<h-3: row=self.system(data,row,w>=105)
        else:
            row=self.attention(data,row)
            row=self.system(data,row,w>=105)
            if row<h-5: row=self.diagnostic(data,row)
        self.footer(row); self.s.refresh()

    def loop(self) -> None:
        next_collect=0.0; data:dict[str,Any]={}
        while True:
            now=time.monotonic()
            if now>=next_collect or self.force:
                data=self.collect(); next_collect=now+1.0; self.force=False
                payload=json.dumps({
                    "mode":self.mode,
                    "activity":data["activity"],
                    "entities":[(e.kind,e.id,e.state,e.raw_state) for e in data["entities"]],
                    "system":data["system"],
                    "expanded":self.expanded_idle,
                },sort_keys=True)
                if payload!=self.last_payload:
                    self.render(data); self.last_payload=payload; self.last_draw=now
            key=self.s.getch()
            if key in (ord("q"),ord("Q")): return
            if key==ord("1"): self.mode="living"; self.force=True
            elif key==ord("2"): self.mode="control"; self.force=True
            elif key==ord("3"): self.mode="diagnostic"; self.force=True
            elif key in (10,13,curses.KEY_ENTER): self.expanded_idle=not self.expanded_idle; self.force=True
            elif key==curses.KEY_RESIZE: self.force=True


def main() -> int:
    curses.wrapper(lambda s: App(s).loop())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
