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

local function feedback(request_id, frame, payload)
    local line = "ZEN_STATE|" .. request_id .. "|" .. frame
    if payload and payload ~= "" then line = line .. "|" .. payload end
    gma.feedback(line)
end

local function group_membership(request_id, group_no)
    local group = handle("Group " .. group_no)
    if not group then
        feedback(request_id, "ERROR", "GROUP_NOT_FOUND")
        return
    end
    feedback(request_id, "BEGIN", "group_membership|" .. group_no)
    local amount = tonumber(safely(gma.show.getobj.amount, group) or 0) or 0
    for index = 0, amount - 1 do
        local child = safely(gma.show.getobj.child, group, index)
        local fixture_no = child and number(child)
        if fixture_no and fixture_no > 0 then feedback(request_id, "MEMBER", tostring(fixture_no)) end
    end
    feedback(request_id, "END", "group_membership|" .. group_no)
end

local function main()
    local request = gma.user.getvar("ZEN_AGENT_REQUEST")
    gma.feedback("ZEN_DEBUG|REQUEST|" .. tostring(request))
    if request == nil or request == "" then
        feedback("none", "ERROR", "EMPTY_REQUEST")
        return
    end

    local request_id, command, argument = tostring(request):match("^([A-Za-z0-9_-]+)|([a-z_]+)|(.+)$")
    -- The request was safely copied into local variables before clearing the
    -- one-shot mailbox, which prevents it from running again after an error.
    gma.user.setvar("ZEN_AGENT_REQUEST", "")
    if not request_id or not command or not argument then
        feedback("none", "ERROR", "MALFORMED_REQUEST")
        return
    end
    if last_request_id == request_id then
        feedback(request_id, "ERROR", "DUPLICATE_REQUEST")
        return
    end
    last_request_id = request_id

    if command == "group_membership" and argument:match("^[1-9][0-9]*$") then
        group_membership(request_id, tonumber(argument))
    elseif command == "group_membership" then
        feedback(request_id, "ERROR", "MALFORMED_ARGUMENT")
    else
        feedback(request_id, "ERROR", "UNKNOWN_COMMAND")
    end
end

return main
