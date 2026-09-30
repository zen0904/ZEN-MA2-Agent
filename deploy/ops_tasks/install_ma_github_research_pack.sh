#!/usr/bin/env bash
set -euo pipefail

ROOT=/opt/zen/tools/ma-github
VENV=/opt/zen/venvs/ma-interop
mkdir -p "$ROOT" /opt/zen/venvs

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-venv lua5.4 >/dev/null

clone_or_update() {
  local repo="$1"
  local name="${repo##*/}"
  local dst="$ROOT/$name"
  if [[ -d "$dst/.git" ]]; then
    local branch
    branch="$(git -C "$dst" rev-parse --abbrev-ref HEAD)"
    git -C "$dst" fetch -q --depth 1 origin "$branch"
    git -C "$dst" reset -q --hard "origin/$branch"
  else
    git clone -q --depth 1 "https://github.com/$repo.git" "$dst"
  fi
  printf '%-46s %s\n' "$repo" "$(git -C "$dst" rev-parse --short HEAD)"
}

repos=(
  "chienchuanw/gma2-mcp"
  "thisis-romar/ma2-onPC-MCP"
  "DD-cLD/The3-MCP"
  "Pahegi/ma3-mcp"
  "open-stage/python-gdtf"
  "open-stage/python-mvr"
  "mvrdevelopment/spec"
  "mvrdevelopment/libMVRgdtf"
  "smartoo-dev/grandma3-position-phasers"
  "smartoo-dev/grandma3-dimmer-phasers"
  "smartoo-dev/grandma3-color-phasers"
  "smartoo-dev/grandma3-preset-banks"
  "smartoo-dev/grandma2-preset-banks"
  "Naostage/grandma2-autozoom-plugin"
  "DJFPaul/grandMA2-Chataigne-Module"
  "yastefan/grandMA3-Chataigne-Module"
  "bitfocus/companion-module-malighting-grandma2"
  "bitfocus/companion-module-malighting-grandma3"
  "Tozsers/ma3-marker-import"
  "damianvandoom/reapma3"
  "kinglevel/TimecodeBPMConvertMA3"
  "LeoKuenne/GrandMA2-ExportTimecode"
  "oje-studio/ma2-tc-cut"
  "ma3-pro-plugins/grandma3-ts-types"
  "ma3-pro-plugins/ma3-ts-plugin-template"
  "ma3-pro-plugins/ma3-pro-plugins-lib"
  "gabe927/gma3-subfixture-layout"
  "MoBrot/grandMA3-LayoutToSelectionGrid"
)

manifest="$ROOT/MANIFEST.tsv"
: > "$manifest"
for repo in "${repos[@]}"; do
  name="${repo##*/}"
  clone_or_update "$repo" | tee -a "$manifest"
done

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip setuptools wheel
"$VENV/bin/python" -m pip install -q --upgrade pygdtf pymvr

echo "=== PYTHON INTEROP ==="
"$VENV/bin/python" - <<'PY'
import importlib.metadata as md
import pygdtf, pymvr
print("PYGDTF_IMPORT=PASS")
print("PYGDTF_VERSION=" + md.version("pygdtf"))
print("PYMVR_IMPORT=PASS")
print("PYMVR_VERSION=" + md.version("pymvr"))
PY

echo "=== GMA2 MCP OFFLINE INSTALL ==="
GMA2_VENV=/opt/zen/venvs/gma2-mcp-reference
if [[ ! -x "$GMA2_VENV/bin/python" ]]; then
  python3 -m venv "$GMA2_VENV"
fi
"$GMA2_VENV/bin/python" -m pip install -q --upgrade pip setuptools wheel
"$GMA2_VENV/bin/python" -m pip install -q -e "$ROOT/gma2-mcp"
"$GMA2_VENV/bin/python" - <<'PY'
import src.response_parser
import src.execution
import src.profile_resolver
import src.introspection
print("GMA2_MCP_CORE_IMPORTS=PASS")
PY

echo "=== THE3 MANIFEST VERIFY ==="
if [[ -f "$ROOT/The3-MCP/tools/make_manifest.py" ]]; then
  python3 "$ROOT/The3-MCP/tools/make_manifest.py" --verify
else
  echo "THE3_MANIFEST_VERIFY=SKIP_NO_TOOL"
fi

echo "=== LUA ==="
lua5.4 -v 2>&1 | head -n 1

echo "=== STORAGE ==="
du -sh "$ROOT" "$VENV" "$GMA2_VENV" 2>/dev/null || true

echo "=== SAFETY ==="
echo "SERVICES_STARTED=0"
echo "OPENCLAW_REGISTRATIONS=0"
echo "MA2_WRITES=0"
echo "MA3_WRITES=0"
echo "RAW_MCP_AUTHORITY_GRANTED=0"
