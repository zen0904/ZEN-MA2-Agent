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
local function number(object) return tonumber(safely(gma.show.getobj.number, object)) end
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
    if amount < 1 then
        feedback(request_id, "ERROR", "UNSUPPORTED_SAFE_ACCESS")
        return
    end
    for index = 0, amount - 1 do
        local child = safely(gma.show.getobj.child, group, index)
        local child_class = child and safely(gma.show.getobj.class, child)
        local child_number = child and number(child)
        local child_name = child and safely(gma.show.getobj.name, child)
        debug("CHILD", tostring(index) .. "|" .. tostring(child_class) .. "|" .. tostring(child_number) .. "|" .. tostring(child_name))
    end
    -- The Group object's child schema is console/show dependent. Until a
    -- fixture-class mapping is confirmed from this diagnostic output, do not
    -- mistake arbitrary children for fixtures or report an empty membership.
    feedback(request_id, "ERROR", "UNSUPPORTED_SAFE_ACCESS")
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
    else
        feedback(request_id, "ERROR", "UNKNOWN_COMMAND")
    end
end

return main
