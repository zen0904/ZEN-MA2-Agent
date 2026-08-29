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
    else
        feedback(request_id, "ERROR", "UNKNOWN_COMMAND")
    end
end

return main
