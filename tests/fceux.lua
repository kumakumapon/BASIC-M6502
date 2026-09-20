-- Independent NES-core verification. ASCII is injected at INCHR, so keyboard
-- hardware is NOT covered here. The real line editor, BASIC and PPU still run.
local transcript = ""
local ready = false
local phase, position, caseStart = 1, 1, 1
local active = false
local frames = 0
local done = false
local waitFrames = 0
local lastInputFrame = 0
local interruptSent = false
emu.speedmode("maximum")

local function writeFile(name, value)
    local f = assert(io.open(OUTPUT_DIR .. "/" .. name, "wb"))
    f:write(value)
    f:close()
end
local function finish(ok, message)
    if done then return end
    done = true
    writeFile("fceux-transcript.txt", transcript)
    writeFile("fceux-result.txt", (ok and "PASS" or "FAIL") .. "\n" .. message .. "\n")
    gui.savescreenshotas(OUTPUT_DIR .. "/fceux.png")
    emu.exit()
end

memory.registerexec(SYM.B_OUTCH, function()
    transcript = transcript .. string.char(memory.getregister("a") % 128)
end)
memory.registerexec(SYM.B_INLIN, function() ready = true end)
memory.registerexec(SYM.keyboard_result, function()
    local sp = memory.getregister("s")
    local caller = memory.readbyte(0x100 + (sp+1)%256) + 256*memory.readbyte(0x100 + (sp+2)%256)
    local value = 0
    if active and caller == SYM.B_INCHR+2 and position <= #CASES[phase].text then
        value = CASES[phase].text:byte(position)
        position = position + 1
        lastInputFrame = frames
    elseif active and CASES[phase].interrupt and not interruptSent and position > #CASES[phase].text and frames-lastInputFrame>30 then
        value = 3
        interruptSent = true
    end
    memory.writebyte(0x327,value)
end)

while not done do
    emu.frameadvance()
    frames = frames + 1
    if frames > 10000 then finish(false,"Timeout in case " .. phase) end
    if phase > #CASES then
        waitFrames = waitFrames + 1
        if waitFrames == 20 then finish(true,"All " .. #CASES .. " interpreter cases passed") end
    elseif not active and ready then
        active = true
        ready = false
        interruptSent = false
        caseStart = #transcript + 1
    elseif active and position > #CASES[phase].text and ready then
        local output = transcript:sub(caseStart)
        for _, expected in ipairs(CASES[phase].expect) do
            if not output:find(expected,1,true) then finish(false,"Case " .. phase .. " missing " .. expected) end
        end
        for _, rejected in ipairs(CASES[phase].reject) do
            if output:find(rejected,1,true) then finish(false,"Case " .. phase .. " unexpected " .. rejected) end
        end
        active = false
        phase = phase + 1
        position = 1
    end
end
