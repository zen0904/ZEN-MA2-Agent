-- Portable copy of gma2/plugins/ZEN_AGENT.lua.
-- Read-only grandMA2 3.9.x state adapter: Echo-only, no selection/programmer
-- mutation and no Store/Update/Delete/Clone/Patch commands.

local function quote(value)
    value = tostring(value or ""):gsub("\\", "\\\\"):gsub('"', '\\"'):gsub("\n", "\\n"):gsub("\r", "\\r")
    return '"' .. value .. '"'
end
local function emit(resource, payload) gma.echo("ZEN_STATE|" .. resource .. "|" .. payload) end
local function unsupported(resource, detail) gma.echo("ZEN_STATE_ERROR|" .. resource .. "|" .. detail) end
local function safely(fn, ...) if type(fn) ~= "function" then return nil end local ok, value = pcall(fn, ...); if ok then return value end return nil end
local function handle(path) return safely(gma.show.getobj.handle, path) end
local function name(object) return safely(gma.show.getobj.name, object) or safely(gma.show.getobj.label, object) or "" end
local function number(object) return tonumber(safely(gma.show.getobj.number, object)) end
local function property(object, wanted)
    local amount = tonumber(safely(gma.show.property.amount, object) or 0) or 0
    for index = 0, amount - 1 do
        local key = tostring(safely(gma.show.property.name, object, index) or ""):lower():gsub("%s+", "")
        if key == wanted then return safely(gma.show.property.get, object, index) end
    end
    return nil
end
local function group_membership(group_no)
    local group = handle("Group " .. group_no)
    if not group then unsupported("group_membership", "Group " .. group_no .. " was not found"); return end
    local fixtures, amount = {}, tonumber(safely(gma.show.getobj.amount, group) or 0) or 0
    for index = 0, amount - 1 do local child = safely(gma.show.getobj.child, group, index); local fixture_no = child and number(child); if fixture_no and fixture_no > 0 then fixtures[#fixtures + 1] = tostring(fixture_no) end end
    emit("group_membership", "{\"group_no\":" .. group_no .. ",\"name\":" .. quote(name(group)) .. ",\"fixtures\":[" .. table.concat(fixtures, ",") .. "]}")
end
local function layout(layout_no)
    local pool = handle("Layout " .. layout_no)
    if not pool then unsupported("layouts", "Layout " .. layout_no .. " was not found"); return end
    local items, amount = {}, tonumber(safely(gma.show.getobj.amount, pool) or 0) or 0
    for index = 0, amount - 1 do
        local child = safely(gma.show.getobj.child, pool, index); local reference = tostring(property(child, "object") or name(child)); local object_no, kind = reference:match("[Ff]ixture%s+(%d+)"), nil
        if object_no then kind = "fixture" else object_no = reference:match("[Gg]roup%s+(%d+)"); if object_no then kind = "group" end end
        local x, y = tonumber(property(child, "posx") or property(child, "x")), tonumber(property(child, "posy") or property(child, "y"))
        if kind and object_no and x and y then
            local item = "{\"type\":" .. quote(kind) .. ",\"" .. kind .. "\":" .. object_no .. ",\"x\":" .. x .. ",\"y\":" .. y; local width, height, rotation = tonumber(property(child, "width")), tonumber(property(child, "height")), tonumber(property(child, "rotation"))
            if width then item = item .. ",\"width\":" .. width end; if height then item = item .. ",\"height\":" .. height end; if rotation then item = item .. ",\"rotation\":" .. rotation end; items[#items + 1] = item .. "}"
        end
    end
    emit("layouts", "{\"layout\":" .. layout_no .. ",\"name\":" .. quote(name(pool)) .. ",\"items\":[" .. table.concat(items, ",") .. "]}")
end
-- grandMA2 passes the quoted command-line argument to this returned function.
local function main(argument)
    local request, argument_no = tostring(argument or ""):match("^([a-z_]+)%s*(%d*)%s*$")
    if request == "group_membership" and tonumber(argument_no) then group_membership(tonumber(argument_no))
    elseif request == "layouts" and tonumber(argument_no) then layout(tonumber(argument_no))
    elseif request == "selection" then unsupported("selection", "safe fixture-id enumeration is unavailable in this adapter")
    elseif request == "programmer" then unsupported("programmer", "safe active-value summary is unavailable in this adapter")
    else unsupported(request or "unknown", "unsupported read-only ZEN_AGENT request") end
end
return main
