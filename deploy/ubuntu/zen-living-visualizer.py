#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

OPS_PUBLIC = Path("/var/lib/zen-ops/public")

STATIONS = {
    "lounge": {"name": "Rest Lounge", "x": 10, "y": 84},
    "research": {"name": "Browser / Research", "x": 19, "y": 30},
    "vision": {"name": "Vision", "x": 18, "y": 48},
    "api": {"name": "AI Model / API", "x": 8, "y": 60},
    "network": {"name": "Network / SSH", "x": 23, "y": 11},
    "compute": {"name": "Compute", "x": 46, "y": 11},
    "zen": {"name": "ZEN Core", "x": 36, "y": 49},
    "openclaw": {"name": "OpenClaw", "x": 50, "y": 34},
    "coding": {"name": "Coding", "x": 54, "y": 50},
    "sandbox": {"name": "Sandbox / OpenShell", "x": 53, "y": 69},
    "github": {"name": "Git / GitHub", "x": 66, "y": 49},
    "terminal": {"name": "Terminal", "x": 48, "y": 88},
    "approval": {"name": "Approval Gate", "x": 77, "y": 50},
    "ma": {"name": "MA Bridge", "x": 91, "y": 50},
    "files": {"name": "Storage", "x": 82, "y": 84},
    "logs": {"name": "Logs / Monitoring", "x": 93, "y": 82},
}

HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ZEN Living System</title>
<style>
:root{
 --floor:#0a0a0c;--surface:#141417;--station:#1c1c21;--text:#ececf0;--muted:#777982;
 --line:rgba(255,255,255,.045);--line2:rgba(255,255,255,.085);--active:#00e5ff;
 --wait:#ffab00;--error:#ff3366;--stuck:#78909c;--ok:#d9dee3;
 --ease:cubic-bezier(.16,1,.3,1);--mono:"JetBrains Mono","Fira Code",ui-monospace,SFMono-Regular,Consolas,monospace;
 --sans:Inter,Geist,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif
}
*{box-sizing:border-box}
html,body{width:100%;height:100%;margin:0;overflow:hidden;background:var(--floor);color:var(--text);font-family:var(--sans)}
body:before{content:"";position:fixed;inset:0;pointer-events:none;background:
 radial-gradient(circle at 35% 42%,rgba(255,255,255,.018),transparent 30%),
 linear-gradient(rgba(255,255,255,.012) 1px,transparent 1px),
 linear-gradient(90deg,rgba(255,255,255,.012) 1px,transparent 1px);
 background-size:auto,32px 32px,32px 32px}
#app{height:100%;display:grid;grid-template-rows:42px minmax(0,1fr)}
.topbar{z-index:20;display:flex;align-items:center;gap:14px;padding:0 16px;border-bottom:1px solid var(--line);background:rgba(10,10,12,.94)}
.brand{font-size:12px;font-weight:600;letter-spacing:.16em}.brand span{color:var(--muted);font-weight:400}
.top-spacer{flex:1}
.chip{height:22px;display:inline-flex;align-items:center;gap:6px;padding:0 8px;border:1px solid var(--line2);font:500 9px var(--mono);letter-spacing:.06em;color:#9da0a8;background:rgba(255,255,255,.018)}
.dot{width:5px;height:5px;border-radius:50%;background:#555}.dot.live{background:var(--active);box-shadow:0 0 8px rgba(0,229,255,.55)}
.dot.warn{background:var(--wait)}.dot.bad{background:var(--error)}
#stage{position:relative;min-height:0;overflow:hidden}
#world{position:absolute;inset:0;overflow:hidden}
#world.health-ok{box-shadow:inset 0 0 70px rgba(255,255,255,.012)}
#world.health-bad{box-shadow:inset 0 0 100px rgba(255,51,102,.07)}
.zone-label{position:absolute;font:500 9px var(--mono);letter-spacing:.18em;color:rgba(255,255,255,.13);text-transform:uppercase;pointer-events:none}
#flow{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
.flow-line{stroke:rgba(255,255,255,.045);stroke-width:1;fill:none;vector-effect:non-scaling-stroke}
.flow-line.gate{stroke:rgba(255,171,0,.15)}
.handoff-line{stroke:rgba(0,229,255,.45);stroke-width:1.4;stroke-dasharray:4 7;fill:none;opacity:0;vector-effect:non-scaling-stroke}
.handoff-line.show{animation:trace 1s linear forwards}
@keyframes trace{0%{opacity:0;stroke-dashoffset:36}20%{opacity:1}100%{opacity:0;stroke-dashoffset:0}}
.station{position:absolute;transform:translate(-50%,-50%);width:112px;min-height:66px;padding:9px 10px 8px;border:1px solid rgba(255,255,255,.035);border-radius:4px;background:linear-gradient(180deg,rgba(29,29,34,.92),rgba(20,20,23,.94));box-shadow:0 2px 8px rgba(0,0,0,.42);transition:border-color .24s var(--ease),box-shadow .24s var(--ease),opacity .24s var(--ease);cursor:default}
.station.structural{width:126px;min-height:76px}
.station.infra{opacity:.68}
.station .edge{position:absolute;left:-1px;top:-1px;bottom:-1px;width:2px;background:transparent;transition:.25s var(--ease)}
.station .label{font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(236,236,240,.34);transition:.2s}
.station .sub{margin-top:6px;font:400 9px var(--mono);color:rgba(255,255,255,.25);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.station.active{border-color:rgba(0,229,255,.13);box-shadow:0 8px 18px rgba(0,0,0,.48),0 0 24px rgba(0,229,255,.035)}
.station.active .edge{background:var(--active)}.station.active .label{color:#f2f5f7}
.station.waiting{border-color:rgba(255,171,0,.22)}.station.waiting .edge{background:var(--wait);animation:breathe 2s ease-in-out infinite}
.station.error{border-color:rgba(255,51,102,.24);filter:saturate(.72)}.station.error .edge{background:var(--error)}
.station.stuck{border-color:rgba(120,144,156,.24);filter:saturate(.45)}.station.stuck .edge{background:var(--stuck)}
@keyframes breathe{0%,100%{opacity:.28}50%{opacity:1}}
.station:hover{border-color:rgba(255,255,255,.18);opacity:1}
.station:hover:after{content:"";position:absolute;inset:-5px;border:1px dashed rgba(255,255,255,.14);pointer-events:none}
#approval.station{width:34px;min-height:210px;padding:0;background:linear-gradient(180deg,rgba(255,255,255,.018),rgba(255,255,255,.008));display:flex;align-items:center;justify-content:center}
#approval .label{writing-mode:vertical-rl;transform:rotate(180deg);font:500 8px var(--mono);letter-spacing:.14em}
#approval.waiting{box-shadow:0 0 34px rgba(255,171,0,.08)}
.avatar{position:absolute;z-index:8;transform:translate(-50%,-50%);transition:left var(--move,.8s) cubic-bezier(.65,0,.35,1),top var(--move,.8s) cubic-bezier(.65,0,.35,1);pointer-events:auto}
.avatar .core{width:9px;height:9px;border-radius:50%;background:#dfe4e8;border:1px solid rgba(255,255,255,.85);box-shadow:0 0 8px rgba(255,255,255,.12)}
.avatar.command .core{width:16px;height:16px;background:transparent;border:2px solid rgba(0,229,255,.9);box-shadow:0 0 10px rgba(0,229,255,.16)}
.avatar .name{position:absolute;left:50%;top:14px;transform:translateX(-50%);white-space:nowrap;font:500 9px var(--mono);color:rgba(255,255,255,.36);opacity:0;transition:.18s}
.avatar.command .name,.avatar.working .name,.avatar.waiting .name,.avatar.error .name,.avatar:hover .name{opacity:1;color:#dadddf}
.avatar.working .core{box-shadow:0 0 14px rgba(0,229,255,.5);background:#f8fbfc}
.avatar.waiting .core{border-color:var(--wait);box-shadow:0 0 12px rgba(255,171,0,.35)}
.avatar.error .core{background:var(--error);border-color:var(--error);box-shadow:0 0 12px rgba(255,51,102,.38)}
.avatar.stuck .core{background:var(--stuck);border-color:var(--stuck)}
.task-token{position:absolute;z-index:9;transform:translate(-50%,-50%);max-width:190px;height:18px;padding:2px 8px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.075);font:500 9px var(--mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;box-shadow:0 8px 16px rgba(0,0,0,.45);opacity:0;transition:left .8s cubic-bezier(.65,0,.35,1),top .8s cubic-bezier(.65,0,.35,1),opacity .2s}
.task-token.show{opacity:1}.task-token.waiting{border-color:rgba(255,171,0,.34)}.task-token.error{border-color:rgba(255,51,102,.35)}
.provider-rack{display:grid;grid-template-columns:repeat(3,1fr);gap:5px;margin-top:8px}
.provider{height:22px;border:1px solid rgba(255,255,255,.04);display:flex;align-items:center;justify-content:center;font:500 8px var(--mono);color:rgba(255,255,255,.24);position:relative;overflow:hidden}
.provider:after{content:"";position:absolute;inset:auto 0 0;height:1px;background:transparent}
.provider.active{color:#e9eef0}.provider.gpt.active:after{background:#10a37f;box-shadow:0 0 8px #10a37f}.provider.claude.active:after{background:#d97757;box-shadow:0 0 8px #d97757}.provider.qwen.active:after{background:#7b61ff;box-shadow:0 0 8px #7b61ff}
.compute-grid{display:grid;grid-template-columns:repeat(8,4px);gap:3px;margin-top:8px}.compute-grid i{width:4px;height:4px;background:rgba(255,255,255,.055)}.compute-grid i.on{background:#e9edf0;box-shadow:0 0 4px rgba(255,255,255,.18)}
.telemetry-row{display:flex;align-items:center;justify-content:space-between;margin-top:5px;font:400 8px var(--mono);color:rgba(255,255,255,.28)}
.fan-ring{width:10px;height:10px;border:1px dashed rgba(255,255,255,.28);border-radius:50%;animation:fan 1.4s linear infinite;animation-play-state:paused}
@keyframes fan{to{transform:rotate(360deg)}}
.gpu-slot{margin-top:6px;padding:3px 4px;border:1px dashed rgba(255,255,255,.08);font:400 7px var(--mono);color:rgba(255,255,255,.18);text-align:center}
.net-tracks{margin-top:8px;display:grid;gap:5px}.track{height:2px;background:rgba(255,255,255,.04);overflow:hidden;position:relative}.particle{position:absolute;width:10px;height:2px;background:var(--active);opacity:0;animation:net 1.6s linear infinite}.particle.tx{right:0;animation-name:netrev}
@keyframes net{0%{left:-12px;opacity:0}15%{opacity:.6}100%{left:100%;opacity:0}}@keyframes netrev{0%{right:-12px;opacity:0}15%{opacity:.45}100%{right:100%;opacity:0}}
.storage-bar{position:absolute;left:0;right:0;bottom:0;height:0;background:rgba(255,255,255,.035);transition:height .5s var(--ease);pointer-events:none}
.health-mark{position:absolute;right:18px;bottom:14px;display:flex;align-items:center;gap:7px;font:500 8px var(--mono);letter-spacing:.08em;color:rgba(255,255,255,.24)}
.health-mark b{width:5px;height:5px;border-radius:50%;background:var(--ok);box-shadow:0 0 8px rgba(255,255,255,.12)}
.health-mark.bad b{background:var(--error);box-shadow:0 0 10px rgba(255,51,102,.35)}
.zone-divider{position:absolute;top:11%;bottom:12%;left:76%;border-left:1px solid rgba(255,171,0,.07);pointer-events:none}
#inspect{position:absolute;right:14px;top:14px;width:260px;max-height:calc(100% - 28px);z-index:30;padding:12px;border:1px solid var(--line2);background:rgba(10,10,12,.94);box-shadow:0 16px 40px rgba(0,0,0,.5);transform:translateX(calc(100% + 30px));transition:transform .28s var(--ease);overflow:auto}
#inspect.open{transform:translateX(0)}#inspect h3{margin:0 0 8px;font-size:10px;letter-spacing:.12em;text-transform:uppercase}#inspect .close{position:absolute;right:8px;top:7px;color:#777;background:none;border:0;font-size:16px}
.inspect-line{display:flex;justify-content:space-between;gap:14px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.035);font:400 9px var(--mono);color:#7e8188}.inspect-line b{font-weight:500;color:#d7d9dd;text-align:right}
.event{padding:6px 0;border-bottom:1px solid rgba(255,255,255,.03);font:400 8px var(--mono);color:#676a70}.event strong{color:#a9adb3;font-weight:500;margin-right:6px}.event.err strong{color:var(--error)}
#event-toggle{position:absolute;right:18px;top:14px;z-index:12;height:22px;padding:0 8px;border:1px solid var(--line);background:rgba(10,10,12,.7);color:#65686e;font:500 8px var(--mono);letter-spacing:.08em}
body.mode-control .station.infra{opacity:.28}
body.mode-diagnostic #event-toggle{border-color:rgba(255,51,102,.18);color:#b4a1a6}
@media(max-width:760px){.station{transform:translate(-50%,-50%) scale(.86)}.station.structural{transform:translate(-50%,-50%) scale(.82)}}
</style>
</head>
<body class="mode-living">
<div id="app">
 <div class="topbar">
  <div class="brand">ZEN <span>/ LIVING SYSTEM</span></div>
  <div class="chip"><span id="liveDot" class="dot"></span><span id="liveText">CONNECTING</span></div>
  <div class="chip"><span id="healthDot" class="dot"></span><span id="healthText">HEALTH</span></div>
  <div class="top-spacer"></div>
  <div class="chip" id="modeChip">LIVING</div>
  <div class="chip" id="host">zen-agent-server</div>
  <div class="chip">OBSERVATION ONLY</div>
 </div>
 <div id="stage">
  <div id="world">
   <svg id="flow"></svg>
   <div class="zone-label" style="left:9%;top:6%">INPUT / THINK</div>
   <div class="zone-label" style="left:47%;top:6%">WORK / EXECUTE</div>
   <div class="zone-label" style="left:82%;top:6%">DEPLOY</div>
   <div class="zone-divider"></div>
   <div id="taskToken" class="task-token"></div>
   <div id="healthMark" class="health-mark"><b></b><span>SYSTEM NOMINAL</span></div>
  </div>
  <button id="event-toggle">EVENTS</button>
  <aside id="inspect"><button class="close">×</button><div id="inspectBody"></div></aside>
 </div>
</div>
<script>
const world=document.getElementById('world'),flow=document.getElementById('flow');
const inspect=document.getElementById('inspect'),inspectBody=document.getElementById('inspectBody');
const providerIds=new Set(['gpt','claude','qwen']);
const tier={zen:'structural',approval:'structural',ma:'structural',compute:'infra',network:'infra',files:'infra',logs:'infra',lounge:'infra'};
const edges=[['research','zen'],['vision','zen'],['api','zen'],['network','zen'],['compute','zen'],['zen','openclaw'],['zen','coding'],['coding','github'],['coding','sandbox'],['github','approval'],['sandbox','approval'],['approval','ma'],['ma','files'],['ma','logs']];
let stations={},avatars={},lastState=null,lastHolder=null;
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function pct(v){const m=String(v||'').match(/([0-9.]+)/);return m?Number(m[1]):0}
function ratio(v){const m=String(v||'').match(/([0-9.]+)\s*\/\s*([0-9.]+)/);return m&&Number(m[2])?Number(m[1])/Number(m[2]):0}
function rate(v){const m=String(v||'').match(/([0-9.]+)\s*(B|KB|MB|GB)\/s/i);if(!m)return 0;return Number(m[1])*({B:1,KB:1024,MB:1048576,GB:1073741824}[m[2].toUpperCase()]||1)}
function stationClass(id){return 'station '+(tier[id]||'')}
function stationInner(id,s){
 let extra='';
 if(id==='api')extra='<div class="provider-rack"><div class="provider gpt" data-p="gpt">GPT</div><div class="provider claude" data-p="claude">CLAUDE</div><div class="provider qwen" data-p="qwen">QWEN</div></div>';
 if(id==='compute')extra='<div class="compute-grid">'+Array.from({length:24},()=>'<i></i>').join('')+'</div><div class="telemetry-row"><span>CPU</span><span data-k="CPU">--</span></div><div class="telemetry-row"><span>TEMP</span><span data-k="CPU Temp">--</span><span class="fan-ring"></span></div><div class="gpu-slot">GPU: N/A / NO SENSOR</div>';
 if(id==='network')extra='<div class="net-tracks"><div class="track"><i class="particle rx"></i></div><div class="track"><i class="particle tx"></i></div></div><div class="telemetry-row"><span data-k="Net IF">--</span><span data-k="Tailscale">--</span></div>';
 if(id==='files')extra='<div class="storage-bar"></div><div class="telemetry-row"><span>DISK</span><span data-k="Disk /">--</span></div>';
 return '<span class="edge"></span><div class="label">'+esc(s.name)+'</div><div class="sub"></div>'+extra
}
function ensureStation(id,s){
 if(stations[id])return stations[id];
 const el=document.createElement('div');el.id=id;el.className=stationClass(id);el.dataset.id=id;el.style.left=s.x+'%';el.style.top=s.y+'%';el.innerHTML=stationInner(id,s);
 el.onclick=()=>showStation(id);world.appendChild(el);stations[id]=el;return el
}
function ensureAvatar(a,index){
 if(avatars[a.id])return avatars[a.id];
 const el=document.createElement('div');el.className='avatar';el.dataset.id=a.id;if(a.id==='zen'||a.id==='ops')el.classList.add('command');
 el.innerHTML='<span class="core"></span><span class="name">'+esc(a.name)+'</span>';el.onclick=()=>showAgent(a.id);world.appendChild(el);avatars[a.id]=el;return el
}
function point(id){const s=lastState?.stations?.[id];if(!s)return null;return [s.x,s.y]}
function drawFlow(){
 const w=world.clientWidth,h=world.clientHeight;flow.setAttribute('viewBox','0 0 '+w+' '+h);flow.innerHTML='';
 edges.forEach(([a,b])=>{const p=point(a),q=point(b);if(!p||!q)return;const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('x1',p[0]*w/100);line.setAttribute('y1',p[1]*h/100);line.setAttribute('x2',q[0]*w/100);line.setAttribute('y2',q[1]*h/100);line.setAttribute('class','flow-line '+(a==='approval'||b==='approval'?'gate':''));flow.appendChild(line)})
 const hline=document.createElementNS('http://www.w3.org/2000/svg','line');hline.id='handoffLine';hline.setAttribute('class','handoff-line');flow.appendChild(hline)
}
function stateClass(a){const s=String(a.status||'').toUpperCase();if(s==='ERROR'||s==='FAILED')return'error';if(s==='WAITING')return'waiting';if(s==='STUCK')return'stuck';if(s==='WORKING')return'working';return'idle'}
function setStationState(id,cls){const el=stations[id];if(!el)return;el.classList.remove('active','waiting','error','stuck');if(cls==='working')el.classList.add('active');if(cls==='waiting')el.classList.add('waiting');if(cls==='error')el.classList.add('error');if(cls==='stuck')el.classList.add('stuck')}
function holderFrom(s){
 const priority=['zen','ops','research','coding','git','vision','openclaw'];
 const active=priority.map(id=>s.agents.find(a=>a.id===id)).find(a=>a&&['WORKING','WAITING','ERROR','STUCK'].includes(String(a.status).toUpperCase()));
 return active||null
}
function moveAvatar(a,index){
 if(providerIds.has(a.id))return;
 const el=ensureAvatar(a,index),st=lastState.stations[a.station]||lastState.stations.lounge;
 let x=st.x,y=st.y;
 if(String(a.status).toUpperCase()==='IDLE'&&a.station==='lounge'){x+=((index%4)-1.5)*1.7;y+=Math.floor(index/4)*2.1}
 el.style.left=x+'%';el.style.top=y+'%';el.className='avatar '+(a.id==='zen'||a.id==='ops'?'command ':'')+stateClass(a);
 const label=el.querySelector('.name');label.textContent=a.name+(String(a.status).toUpperCase()!=='IDLE'?' · '+a.status:'')
}
function updateTask(s){
 const token=document.getElementById('taskToken'),holder=holderFrom(s);if(!holder){token.className='task-token';lastHolder=null;return}
 const st=s.stations[holder.station]||s.stations.zen;token.textContent=(holder.task||s.task?.summary||'Active task').slice(0,42);token.style.left=(st.x+3.5)+'%';token.style.top=(st.y-4)+'%';token.className='task-token show '+stateClass(holder);
 if(lastHolder&&lastHolder!==holder.station){const p=s.stations[lastHolder],q=st,l=document.getElementById('handoffLine');if(p&&q&&l){const w=world.clientWidth,h=world.clientHeight;l.setAttribute('x1',p.x*w/100);l.setAttribute('y1',p.y*h/100);l.setAttribute('x2',q.x*w/100);l.setAttribute('y2',q.y*h/100);l.classList.remove('show');void l.getBoundingClientRect();l.classList.add('show')}}
 lastHolder=holder.station
}
function updateProviders(s){
 ['gpt','claude','qwen'].forEach(id=>{const a=s.agents.find(x=>x.id===id),el=stations.api?.querySelector('[data-p="'+id+'"]');if(el)el.classList.toggle('active',!!a&&String(a.status).toUpperCase()==='WORKING')})
}
function updateTelemetry(s){
 const sys=s.system||{},cpu=pct(sys.CPU),temp=pct(sys['CPU Temp']),mem=ratio(sys.Memory),disk=ratio(sys['Disk /']),rx=rate(sys['Net RX']),tx=rate(sys['Net TX']);
 const comp=stations.compute;if(comp){comp.querySelectorAll('.compute-grid i').forEach((n,i)=>n.classList.toggle('on',i<Math.round(cpu/100*24)));comp.querySelectorAll('[data-k]').forEach(n=>{const k=n.dataset.k;n.textContent=sys[k]??'N/A'});const fan=comp.querySelector('.fan-ring'),rpm=pct(sys.Fan);fan.style.animationPlayState=rpm>0?'running':'paused';fan.style.animationDuration=Math.max(.35,2.4-rpm/3000)+'s';if(temp>78)comp.classList.add('error')}
 const net=stations.network;if(net){net.querySelectorAll('[data-k]').forEach(n=>{n.textContent=sys[n.dataset.k]??'N/A'});const r=net.querySelector('.rx'),t=net.querySelector('.tx'),rs=Math.min(1,Math.log10(rx+1)/7),ts=Math.min(1,Math.log10(tx+1)/7);r.style.opacity=rs>0?.2+rs*.8:0;t.style.opacity=ts>0?.2+ts*.8:0;r.style.animationDuration=(2.2-rs*1.5)+'s';t.style.animationDuration=(2.2-ts*1.5)+'s'}
 const store=stations.files;if(store){store.querySelector('[data-k]').textContent=sys['Disk /']??'N/A';store.querySelector('.storage-bar').style.height=(Math.max(0,Math.min(1,disk))*100)+'%'}
}
function globalHealth(s){
 const sys=s.system||{},critical=['ZEN Ops','OpenClaw','Tailscale'];const bad=critical.some(k=>!['active','ready','up'].includes(String(sys[k]||'').toLowerCase()));
 const dot=document.getElementById('healthDot'),txt=document.getElementById('healthText'),mark=document.getElementById('healthMark');dot.className='dot '+(bad?'bad':'live');txt.textContent=bad?'DEGRADED':'NOMINAL';world.classList.toggle('health-bad',bad);world.classList.toggle('health-ok',!bad);mark.classList.toggle('bad',bad);mark.querySelector('span').textContent=bad?'SYSTEM DEGRADED':'SYSTEM NOMINAL'
}
function showStation(id){
 const s=lastState,sys=s.system||{},st=s.stations[id];let rows=[];
 if(id==='compute')rows=[['CPU',sys.CPU],['CPU TEMP',sys['CPU Temp']],['FAN',sys.Fan],['MEMORY',sys.Memory],['LOAD',sys.Load],['UPTIME',sys.Uptime],['GPU',sys.GPU],['GPU USE',sys['GPU Use']],['GPU TEMP',sys['GPU Temp']]];
 else if(id==='network')rows=[['INTERFACE',sys['Net IF']],['RX',sys['Net RX']],['TX',sys['Net TX']],['TAILSCALE',sys.Tailscale],['OPENCLAW',sys.OpenClaw],['RDC',sys.RDC]];
 else if(id==='files')rows=[['DISK',sys['Disk /']]];
 else{const here=s.agents.filter(a=>a.station===id&&!providerIds.has(a.id));rows=[['STATE',here.some(a=>a.status==='ERROR')?'ERROR':here.some(a=>a.status==='WORKING')?'ACTIVE':'IDLE'],['AGENTS',here.map(a=>a.name).join(', ')||'—']]}
 inspectBody.innerHTML='<h3>'+esc(st?.name||id)+'</h3>'+rows.map(r=>'<div class="inspect-line"><span>'+esc(r[0])+'</span><b>'+esc(r[1]??'N/A')+'</b></div>').join('');inspect.classList.add('open')
}
function showAgent(id){const a=lastState.agents.find(x=>x.id===id);if(!a)return;inspectBody.innerHTML='<h3>'+esc(a.name)+'</h3><div class="inspect-line"><span>STATE</span><b>'+esc(a.status)+'</b></div><div class="inspect-line"><span>STATION</span><b>'+esc(lastState.stations[a.station]?.name||a.station)+'</b></div><div class="inspect-line"><span>TASK</span><b>'+esc(a.task||'—')+'</b></div>';inspect.classList.add('open')}
function showEvents(){const ev=(lastState?.events||[]).slice().reverse();inspectBody.innerHTML='<h3>Event Stream</h3>'+ev.map(e=>'<div class="event '+((e.status==='failed'||e.type==='ERROR')?'err':'')+'"><strong>'+esc(e.time||'')+' '+esc(e.type||'')+'</strong>'+esc(e.summary||'')+'</div>').join('');inspect.classList.add('open')}
document.querySelector('#inspect .close').onclick=()=>inspect.classList.remove('open');document.getElementById('event-toggle').onclick=showEvents;
function applyMode(s){const mode=String(s.mode||'living').toLowerCase();document.body.className='mode-'+mode;document.getElementById('modeChip').textContent=mode.toUpperCase()}
function render(s){
 lastState=s;document.getElementById('liveDot').className='dot live';document.getElementById('liveText').textContent='LIVE';document.getElementById('host').textContent=s.host||'zen-agent-server';applyMode(s);
 Object.entries(s.stations||{}).forEach(([id,st])=>ensureStation(id,st));drawFlow();
 Object.keys(stations).forEach(id=>setStationState(id,'idle'));
 (s.agents||[]).forEach((a,i)=>{if(providerIds.has(a.id))return;moveAvatar(a,i);setStationState(a.station,stateClass(a))});
 updateProviders(s);updateTelemetry(s);updateTask(s);globalHealth(s)
}
async function tick(){try{const r=await fetch('/api/state?ts='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);render(await r.json())}catch(e){document.getElementById('liveDot').className='dot bad';document.getElementById('liveText').textContent='DISCONNECTED'}}
window.addEventListener('resize',()=>lastState&&drawFlow());tick();setInterval(tick,1000);
</script>
</body>
</html>"""\n\ndef sh(argv: list[str], timeout: float = 1.5) -> str:
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


_CPU_SAMPLE: tuple[int, int] | None = None
_NET_SAMPLE: dict[str, tuple[float, int, int]] = {}
_GPU_MODEL: str | None = None


def cpu_usage_summary() -> str:
    global _CPU_SAMPLE
    try:
        fields = [int(x) for x in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
        idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
        total = sum(fields)
        previous = _CPU_SAMPLE
        _CPU_SAMPLE = (total, idle)
        if previous is None:
            return "warming"
        total_delta = total - previous[0]
        idle_delta = idle - previous[1]
        if total_delta <= 0:
            return "0%"
        busy = max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))
        return f"{busy:.0f}%"
    except Exception:
        return "unknown"


def cpu_temp_summary() -> str:
    try:
        preferred: list[float] = []
        fallback: list[float] = []
        for zone in Path("/sys/class/thermal").glob("thermal_zone*"):
            try:
                name = (zone / "type").read_text().strip().lower()
                raw = float((zone / "temp").read_text().strip())
                value = raw / 1000.0 if abs(raw) > 1000 else raw
                if -20 <= value <= 130:
                    fallback.append(value)
                    if any(key in name for key in ("x86_pkg_temp", "coretemp", "package")):
                        preferred.append(value)
            except Exception:
                continue
        values = preferred or fallback
        return f"{max(values):.0f}°C" if values else "N/A"
    except Exception:
        return "N/A"


def fan_summary() -> str:
    try:
        for hwmon in Path("/sys/class/hwmon").glob("hwmon*"):
            try:
                name = (hwmon / "name").read_text().strip().lower()
            except Exception:
                continue
            if "applesmc" not in name:
                continue
            values: list[int] = []
            for path in hwmon.glob("fan*_input"):
                try:
                    values.append(int(float(path.read_text().strip())))
                except Exception:
                    pass
            if values:
                return f"{max(values)} RPM"
    except Exception:
        pass

    output = sh(["sensors"], timeout=1.0)
    match = re.search(r"Exhaust\s*:\s*([0-9]+)\s*RPM", output, re.IGNORECASE)
    if match:
        return f"{int(match.group(1))} RPM"
    return "N/A"


def gpu_model_summary() -> str:
    global _GPU_MODEL
    if _GPU_MODEL is not None:
        return _GPU_MODEL
    output = sh(["lspci"], timeout=1.0)
    for line in output.splitlines():
        low = line.lower()
        if "vga compatible controller" in low or "3d controller" in low or "display controller" in low:
            value = line.split(":", 2)[-1].strip() if ":" in line else line.strip()
            _GPU_MODEL = value[:42] or "unknown"
            return _GPU_MODEL
    _GPU_MODEL = "unknown"
    return _GPU_MODEL


def gpu_usage_summary() -> str:
    for path in Path("/sys/class/drm").glob("card*/device/gpu_busy_percent"):
        try:
            return f"{float(path.read_text().strip()):.0f}%"
        except Exception:
            continue
    return "N/A"


def gpu_temp_summary() -> str:
    for path in Path("/sys/class/drm").glob("card*/device/hwmon/hwmon*/temp*_input"):
        try:
            raw = float(path.read_text().strip())
            value = raw / 1000.0 if abs(raw) > 1000 else raw
            if -20 <= value <= 130:
                return f"{value:.0f}°C"
        except Exception:
            continue
    return "N/A"


def disk_summary() -> str:
    try:
        st = os.statvfs("/")
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bavail
        used = total - free
        return f"{used / (1024**3):.0f}/{total / (1024**3):.0f} GiB"
    except Exception:
        return "unknown"


def uptime_summary() -> str:
    try:
        seconds = float(Path("/proc/uptime").read_text().split()[0])
        days, rem = divmod(int(seconds), 86400)
        hours, rem = divmod(rem, 3600)
        minutes = rem // 60
        if days:
            return f"{days}d {hours}h"
        return f"{hours}h {minutes}m"
    except Exception:
        return "unknown"


def default_interface() -> str:
    try:
        lines = Path("/proc/net/route").read_text().splitlines()[1:]
        for line in lines:
            fields = line.split()
            if len(fields) < 4:
                continue
            interface, destination, _, flags = fields[:4]
            if destination != "00000000":
                continue
            try:
                if int(flags, 16) & 0x2:
                    return interface
            except ValueError:
                continue
    except Exception:
        pass
    return "unknown"


def _network_bytes(interface: str) -> tuple[int, int] | None:
    try:
        for line in Path("/proc/net/dev").read_text().splitlines():
            if ":" not in line:
                continue
            name, data = line.split(":", 1)
            if name.strip() != interface:
                continue
            fields = data.split()
            return int(fields[0]), int(fields[8])
    except Exception:
        pass
    return None


def rate_summary(value: float) -> str:
    units = ("B/s", "KB/s", "MB/s", "GB/s")
    index = 0
    value = max(0.0, value)
    while value >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    return f"{value:.1f} {units[index]}"


def network_summary() -> tuple[str, str, str]:
    interface = default_interface()
    values = _network_bytes(interface)
    if interface == "unknown" or values is None:
        return interface, "N/A", "N/A"
    now = time.monotonic()
    previous = _NET_SAMPLE.get(interface)
    _NET_SAMPLE[interface] = (now, values[0], values[1])
    if previous is None or now <= previous[0]:
        return interface, "warming", "warming"
    elapsed = now - previous[0]
    rx = (values[0] - previous[1]) / elapsed
    tx = (values[1] - previous[2]) / elapsed
    return interface, rate_summary(rx), rate_summary(tx)

def build_state() -> dict[str, Any]:
    latest = read_json(OPS_PUBLIC / "latest.json")
    proc = process_snapshot()
    status = str(latest.get("status") or "idle").lower()
    meta = latest.get("meta") if isinstance(latest.get("meta"), dict) else {}
    summary = str(meta.get("summary") or latest.get("job_id") or "No active task")
    tools = [str(x) for x in meta.get("tools", [])] if isinstance(meta.get("tools"), list) else []
    text = " ".join([summary, " ".join(tools), str(latest.get("kind") or "")])
    running = status == "running"
    waiting = status in {"waiting", "waiting_for_approval", "needs_approval", "needs-approval"}
    failed = status in {"failed", "error", "timeout", "rejected"}
    zen_status = "WAITING" if waiting else ("WORKING" if running else ("ERROR" if failed else "IDLE"))

    agents: list[dict[str, str]] = []
    zen_station = "approval" if waiting else (station_for(text, status) if running or failed else "lounge")
    agents.append({"id":"zen","name":"ZEN Agent","status":zen_status,"station":zen_station,"task":summary if running or waiting or failed else ""})
    ops_status = "WAITING" if waiting else ("WORKING" if running else ("ERROR" if failed else "IDLE"))
    agents.append({"id":"ops","name":"ZEN Ops","status":ops_status,"station":"approval" if waiting else (station_for(text,status) if running or failed else "zen"),"task":summary if running or waiting or failed else ""})
    agents.append({"id":"openclaw","name":"OpenClaw","status":"IDLE" if port_open(18789) else "ERROR","station":"openclaw" if port_open(18789) else "logs","task":"Gateway active" if port_open(18789) else "Gateway unavailable"})

    codex = any(x in proc for x in (" codex ", "codex exec", "@openai/codex", "codex-linux"))
    agents.append({"id":"coding","name":"Coding Agent","status":"WORKING" if codex else "IDLE","station":"coding" if codex else "lounge","task":"Code task visible in process table" if codex else ""})

    research = running and any(x in text.lower() for x in ("web","browser","research","search","crawl"))
    agents.append({"id":"research","name":"Research Agent","status":"WORKING" if research else "IDLE","station":"research" if research else "lounge","task":summary if research else ""})

    git_active = running and any(x in text.lower() for x in ("git","github","commit","push"))
    agents.append({"id":"git","name":"Git Worker","status":"WORKING" if git_active else "IDLE","station":"github" if git_active else "lounge","task":summary if git_active else ""})

    vision_active = running and any(x in text.lower() for x in ("vision","image","video","gdtf","mvr"))
    agents.append({"id":"vision","name":"Vision Agent","status":"WORKING" if vision_active else "IDLE","station":"vision" if vision_active else "lounge","task":summary if vision_active else ""})

    # Provider avatars require explicit task/runtime metadata. Do not infer
    # provider activity from the resident ChatGPT GUI process name.
    provider_text = text.lower()
    for aid, name, keys in (
        ("gpt","GPT Provider",("openai","gpt")),
        ("qwen","Qwen Provider",("qwen",)),
        ("claude","Claude Provider",("claude",)),
    ):
        active = running and any(k in provider_text for k in keys)
        agents.append({"id":aid,"name":name,"status":"WORKING" if active else "IDLE","station":"api" if active else "lounge","task":summary if active else ""})

    net_if, net_rx, net_tx = network_summary()
    system = {
        "CPU": cpu_usage_summary(),
        "CPU Temp": cpu_temp_summary(),
        "Fan": fan_summary(),
        "GPU": gpu_model_summary(),
        "GPU Use": gpu_usage_summary(),
        "GPU Temp": gpu_temp_summary(),
        "Memory": mem_summary(),
        "Disk /": disk_summary(),
        "Net IF": net_if,
        "Net RX": net_rx,
        "Net TX": net_tx,
        "Uptime": uptime_summary(),
        "Load": load_summary(),
        "ZEN Ops": service("zen-ops-worker"),
        "OpenClaw": "active" if port_open(18789) else "down",
        "Tailscale": service("tailscaled"),
        "RDC": service("desktop-commander-remote"),
        "ChatGPT GUI": service("zen-chatgpt-desktop"),
    }
    mode_path = Path("/var/lib/zenui/control-room-mode")
    try:
        mode = mode_path.read_text(encoding="utf-8").strip().lower()
    except Exception:
        mode = "living"
    if mode not in {"living", "control", "diagnostic"}:
        mode = "living"

    task = {
        "id": str(latest.get("job_id") or ""),
        "summary": summary if running or waiting or failed else "",
        "status": status,
        "station": zen_station,
        "tools": tools,
    }
    return {
        "schema":"zen.living_visualizer.state.v0.2",
        "host": socket.gethostname(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "task": task,
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
            try:
                payload = build_state()
                code = 200
            except Exception as exc:
                payload = {
                    "schema": "zen.living_visualizer.error.v0.1",
                    "status": "error",
                    "error": type(exc).__name__,
                    "message": str(exc)[:240],
                    "authority": "OBSERVATION_ONLY",
                }
                code = 500
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_bytes(code, "application/json; charset=utf-8", body)
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
