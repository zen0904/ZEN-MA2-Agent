-- ZEN MA2 Agent read-only UserVar mailbox adapter for grandMA2 3.9.x.
-- It never selects fixtures, clears the programmer, or executes MA commands.

local last_request_id = nil

local function safely(fn, ...)
    if type(fn) ~= "function" then return nil end
    local ok, value = pcall(fn, ...)
    if ok then return value end
    return nil
end

local function handle(path) return safely(gma.show.getobj.handle, path) end
local function debug(topic, payload) gma.feedback("ZEN_DEBUG|" .. topic .. "|" .. tostring(payload)) end

local function feedback(request_id, frame, payload)
    local line = "ZEN_STATE|" .. request_id .. "|" .. frame
    if payload and payload ~= "" then line = line .. "|" .. payload end
    gma.feedback(line)
end

local function group_membership(request_id, group_no)
    local group = handle("Group " .. group_no)
    debug("GROUP_HANDLE", group)
    if not group then
        feedback(request_id, "ERROR", "GROUP_NOT_FOUND")
        return
    end
    local amount = tonumber(safely(gma.show.getobj.amount, group) or 0) or 0
    debug("CLASS", safely(gma.show.getobj.class, group))
    debug("AMOUNT", amount)
    -- grandMA2's bundled API Test enumerates properties with zero-based
    -- indexes from 0 through property.amount(handle) - 1.
    local property_amount = tonumber(safely(gma.show.property.amount, group) or 0) or 0
    debug("PROP_AMOUNT", property_amount)
    for property_index = 0, property_amount - 1 do
        local property_name = safely(gma.show.property.name, group, property_index)
        local property_value = safely(gma.show.property.get, group, property_index)
        debug("PROP", tostring(property_index) .. "|" .. tostring(property_name) .. "|" .. tostring(property_value))
    end
    -- Group membership is not stored in this object's child tree on MA2 3.9.
    -- Do not infer fixtures from any hierarchy or report an empty membership.
    feedback(request_id, "ERROR", "UNSUPPORTED_SAFE_ACCESS")
end

local function object_probe(request_id, argument)
    -- This allow-list is deliberately read-only.  A nil handle is a diagnostic
    -- result, not proof that an MA2 object type or CObject token does not exist.
    local object_kind, object_number = argument:match("^(Preset)%s+([1-9][0-9]*%.[1-9][0-9]*)$")
    if not object_kind then object_kind, object_number = argument:match("^(Executor)%s+([1-9][0-9]*%.[1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Group)%s+([1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Fixture)%s+([1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Subfixture)%s+([1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Macro)%s+([1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Sequence)%s+([1-9][0-9]*)$") end
    if not object_kind then object_kind, object_number = argument:match("^(Effect)%s+([1-9][0-9]*)$") end
    if not object_kind then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
        return
    end
    local path = object_kind .. " " .. object_number
    local object_handle = handle(path)
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|PATH|" .. path)
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|HANDLE|" .. tostring(object_handle))
    if not object_handle then
        feedback(request_id, "ERROR", "OBJECT_NOT_FOUND")
        return
    end
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|CLASS|" .. tostring(safely(gma.show.getobj.class, object_handle)))
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|NUMBER|" .. tostring(safely(gma.show.getobj.number, object_handle)))
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|NAME|" .. tostring(safely(gma.show.getobj.name, object_handle)))
    -- The documented getobj name is the only verified human-readable label accessor.
    gma.feedback("ZEN_LAYOUT_PROBE|" .. request_id .. "|LABEL|" .. tostring(safely(gma.show.getobj.name, object_handle)))
    feedback(request_id, "END", "object_probe")
end

local function layout_probe_feedback(request_id, node_path, field, value)
    gma.feedback("ZEN_LAYOUT_FIXTURE_PROBE|" .. request_id .. "|" .. node_path .. "|" .. field .. "|" .. tostring(value))
end

local function layout_probe_node(request_id, node, node_path, depth)
    local child_count = tonumber(safely(gma.show.getobj.amount, node) or 0) or 0
    layout_probe_feedback(request_id, node_path, "HANDLE", node)
    layout_probe_feedback(request_id, node_path, "CLASS", safely(gma.show.getobj.class, node))
    layout_probe_feedback(request_id, node_path, "NUMBER", safely(gma.show.getobj.number, node))
    layout_probe_feedback(request_id, node_path, "NAME", safely(gma.show.getobj.name, node))
    layout_probe_feedback(request_id, node_path, "PARENT", safely(gma.show.getobj.parent, node))
    layout_probe_feedback(request_id, node_path, "CHILD_COUNT", child_count)

    local property_count = math.min(tonumber(safely(gma.show.property.amount, node) or 0) or 0, 16)
    layout_probe_feedback(request_id, node_path, "PROPERTY_COUNT", property_count)
    for property_index = 0, property_count - 1 do
        local property_name = safely(gma.show.property.name, node, property_index)
        layout_probe_feedback(request_id, node_path, "PROPERTY", tostring(property_index) .. "|" .. tostring(property_name) .. "|" .. tostring(safely(gma.show.property.get, node, property_index)))
    end

    -- Two levels / twelve children per node keep the probe bounded even if the
    -- Layout object is attached to a larger MA2 object tree.
    if depth >= 2 then return end
    local child_limit = math.min(child_count, 12)
    for child_index = 0, child_limit - 1 do
        local child = safely(gma.show.getobj.child, node, child_index)
        if child then
            layout_probe_node(request_id, child, node_path .. "/" .. tostring(child_index), depth + 1)
        else
            layout_probe_feedback(request_id, node_path .. "/" .. tostring(child_index), "HANDLE", "nil")
        end
    end
end

local function layout_fixture_probe(request_id, layout_no)
    local path = "Layout " .. layout_no
    local layout = handle(path)
    layout_probe_feedback(request_id, "root", "PATH", path)
    if not layout then
        feedback(request_id, "ERROR", "LAYOUT_NOT_FOUND")
        return
    end
    layout_probe_node(request_id, layout, "root", 0)
    feedback(request_id, "END", "layout_fixture_probe")
end

local function preset_probe_feedback(request_id, node_path, field, value)
    gma.feedback("ZEN_PRESET_PROBE|" .. request_id .. "|" .. node_path .. "|" .. field .. "|" .. tostring(value))
end

local function preset_probe_node(request_id, node, node_path, depth)
    local child_count = tonumber(safely(gma.show.getobj.amount, node) or 0) or 0
    preset_probe_feedback(request_id, node_path, "HANDLE", node)
    preset_probe_feedback(request_id, node_path, "CLASS", safely(gma.show.getobj.class, node))
    preset_probe_feedback(request_id, node_path, "NUMBER", safely(gma.show.getobj.number, node))
    preset_probe_feedback(request_id, node_path, "NAME", safely(gma.show.getobj.name, node))
    preset_probe_feedback(request_id, node_path, "PARENT", safely(gma.show.getobj.parent, node))
    preset_probe_feedback(request_id, node_path, "CHILD_COUNT", child_count)
    local property_count = math.min(tonumber(safely(gma.show.property.amount, node) or 0) or 0, 32)
    preset_probe_feedback(request_id, node_path, "PROPERTY_COUNT", property_count)
    for property_index = 0, property_count - 1 do
        local property_name = safely(gma.show.property.name, node, property_index)
        preset_probe_feedback(request_id, node_path, "PROPERTY", tostring(property_index) .. "|" .. tostring(property_name) .. "|" .. tostring(safely(gma.show.property.get, node, property_index)))
    end
    -- Preset internals can be deeper than a Pool object; the limit protects
    -- command-line feedback and prevents arbitrary show-tree traversal.
    if depth >= 3 then return end
    for child_index = 0, math.min(child_count, 32) - 1 do
        local child = safely(gma.show.getobj.child, node, child_index)
        if child then
            preset_probe_node(request_id, child, node_path .. "/" .. tostring(child_index), depth + 1)
        else
            preset_probe_feedback(request_id, node_path .. "/" .. tostring(child_index), "HANDLE", "nil")
        end
    end
end

local function preset_probe(request_id, preset_ref)
    local path = "Preset " .. preset_ref
    local preset = handle(path)
    preset_probe_feedback(request_id, "root", "PATH", path)
    if not preset then
        feedback(request_id, "ERROR", "PRESET_NOT_FOUND")
        return
    end
    preset_probe_node(request_id, preset, "root", 0)
    feedback(request_id, "END", "preset_probe")
end

local function inspect_probe_feedback(request_id, scope, field, value)
    gma.feedback("ZEN_INSPECT_PROBE|" .. request_id .. "|" .. scope .. "|" .. field .. "|" .. tostring(value))
end

local function inspect_show_object(request_id, scope, path)
    local object_handle = handle(path)
    inspect_probe_feedback(request_id, scope, "API", "gma.show.getobj.handle")
    inspect_probe_feedback(request_id, scope, "PATH", path)
    inspect_probe_feedback(request_id, scope, "HANDLE", object_handle)
    if not object_handle then return end
    inspect_probe_feedback(request_id, scope, "CLASS", safely(gma.show.getobj.class, object_handle))
    inspect_probe_feedback(request_id, scope, "NUMBER", safely(gma.show.getobj.number, object_handle))
    inspect_probe_feedback(request_id, scope, "NAME", safely(gma.show.getobj.name, object_handle))
    inspect_probe_feedback(request_id, scope, "CHILD_COUNT", safely(gma.show.getobj.amount, object_handle))
    local property_count = math.min(tonumber(safely(gma.show.property.amount, object_handle) or 0) or 0, 16)
    inspect_probe_feedback(request_id, scope, "PROPERTY_COUNT", property_count)
    for property_index = 0, property_count - 1 do
        local property_name = safely(gma.show.property.name, object_handle, property_index)
        inspect_probe_feedback(request_id, scope, "PROPERTY", tostring(property_index) .. "|" .. tostring(property_name) .. "|" .. tostring(safely(gma.show.property.get, object_handle, property_index)))
    end
end

local function selection_probe(request_id)
    -- These API calls are documented read-only.  They do not expose a verified
    -- Selection member list, so their output is diagnostic evidence only.
    inspect_show_object(request_id, "selection", "Selection")
    inspect_probe_feedback(request_id, "selection", "API", "gma.user.getcmddest")
    inspect_probe_feedback(request_id, "selection", "CMD_DEST", safely(gma.user.getcmddest))
    inspect_probe_feedback(request_id, "selection", "API", "gma.user.getselectedexec")
    inspect_probe_feedback(request_id, "selection", "SELECTED_EXEC", safely(gma.user.getselectedexec))
    feedback(request_id, "BEGIN", "selection_probe")
    feedback(request_id, "END", "selection_probe")
end

local function programmer_probe(request_id)
    -- No command execution, fixture selection, Programmer mutation, or traversal is
    -- performed.  This records only the documented object/property API shape.
    inspect_show_object(request_id, "programmer", "Programmer")
    inspect_probe_feedback(request_id, "programmer", "API", "gma.user.getcmddest")
    inspect_probe_feedback(request_id, "programmer", "CMD_DEST", safely(gma.user.getcmddest))
    feedback(request_id, "BEGIN", "programmer_probe")
    feedback(request_id, "END", "programmer_probe")
end

local function main()
    local request = gma.user.getvar("ZEN_AGENT_REQUEST")
    gma.feedback("ZEN_DEBUG|REQUEST|" .. tostring(request))
    if request == nil or request == "" then
        feedback("none", "ERROR", "EMPTY_REQUEST")
        return
    end

    local normalized = tostring(request):match("^%s*(.-)%s*$")
    local visible_request_id = normalized:match("^(%S+)") or "none"
    local request_id, command, argument = normalized:match("^([A-Za-z0-9_-]+)%s+([a-z_]+)%s*(.-)%s*$")
    -- The request was safely copied into local variables before clearing the
    -- one-shot mailbox, which prevents it from running again after an error.
    gma.user.setvar("ZEN_AGENT_REQUEST", "")
    if not request_id or not command then
        feedback(visible_request_id, "ERROR", "MALFORMED_REQUEST")
        return
    end
    if last_request_id == request_id then
        feedback(request_id, "ERROR", "DUPLICATE_REQUEST")
        return
    end
    last_request_id = request_id

    if command == "group_membership" and argument == "" then
        feedback(request_id, "ERROR", "MALFORMED_REQUEST")
    elseif command == "group_membership" and argument:match("^[1-9][0-9]*$") then
        group_membership(request_id, tonumber(argument))
    elseif command == "group_membership" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    elseif command == "object_probe" then
        object_probe(request_id, argument)
    elseif command == "layout_fixture_probe" and argument:match("^[1-9][0-9]*$") then
        layout_fixture_probe(request_id, tonumber(argument))
    elseif command == "layout_fixture_probe" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    elseif command == "preset_probe" and argument:match("^[1-9][0-9]*%.[1-9][0-9]*$") then
        preset_probe(request_id, argument)
    elseif command == "preset_probe" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    elseif command == "selection_probe" and argument == "" then
        selection_probe(request_id)
    elseif command == "selection_probe" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    elseif command == "programmer_probe" and argument == "" then
        programmer_probe(request_id)
    elseif command == "programmer_probe" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    else
        feedback(request_id, "ERROR", "UNKNOWN_COMMAND")
    end
end

return main
