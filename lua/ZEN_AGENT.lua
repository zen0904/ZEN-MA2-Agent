-- Temporary grandMA2 3.9 Plugin Pool mailbox smoke test.
-- It has no show-control side effects.

local function main()
    local request = gma.user.getvar("ZEN_AGENT_REQUEST")
    gma.echo("ZEN_SMOKE_ECHO")
    gma.feedback("ZEN_SMOKE_FEEDBACK")
    gma.echo("ZEN_REQUEST|" .. tostring(request))
    gma.feedback("ZEN_REQUEST|" .. tostring(request))
    -- Consume the one-shot mailbox so an old request cannot run again.
    gma.user.setvar("ZEN_AGENT_REQUEST", "")
end

return main
