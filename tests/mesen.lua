-- The runner prepends SYM, OUTPUT_DIR and CASES. Keyboard electrical inputs are
-- injected; the ROM's scanner, ASCII translation, editor and interpreter execute.
local transcript = ""
local ready = false
local phase = 1
local position = 1
local tick = 0
local frame = 0
local keys = {}
local matrixRow, column, enabled = 0, 0, false
local nmiStart = nil
local maxNmi = 0
local rendering = false
local failure = nil
local caseStart = 1
local finishing = 0

local function writeFile(name, value)
    local f = assert(io.open(OUTPUT_DIR .. "/" .. name, "wb"))
    f:write(value)
    f:close()
end

local function finish(ok, message)
    writeFile("mesen-transcript.txt", transcript)
    writeFile("mesen.png", emu.takeScreenshot())
    writeFile("mesen-result.txt", (ok and "PASS" or "FAIL") .. "\n" .. message ..
        "\nMaximum NMI cycles: " .. maxNmi .. "\nFrames: " .. frame .. "\n")
    emu.stop(ok and 0 or 1)
end

emu.addMemoryCallback(function()
    local value = emu.getCpuState().a & 127
    transcript = transcript .. string.char(value)
end, emu.callbackType.exec, SYM.B_OUTCH)

emu.addMemoryCallback(function() ready = true end, emu.callbackType.exec, SYM.B_INLIN)
emu.addMemoryCallback(function() nmiStart = emu.getCpuCycleCount() end,
    emu.callbackType.exec, SYM.nmi)
emu.addMemoryCallback(function()
    if nmiStart then
        maxNmi = math.max(maxNmi, emu.getCpuCycleCount() - nmiStart + 13)
        nmiStart = nil
    end
end, emu.callbackType.exec, SYM.irq)
emu.addMemoryCallback(function(_,value) rendering = (value & 24) ~= 0 end,
    emu.callbackType.write, 0x2001)
emu.addMemoryCallback(function()
    if rendering and (not nmiStart or emu.getCpuCycleCount() - nmiStart > 2200) then
        failure = "PPU write outside the NMI VBlank budget"
    end
end, emu.callbackType.write, 0x2007)

emu.addMemoryCallback(function(_, value)
    local nextColumn = (value >> 1) & 1
    if nextColumn == 0 and column == 1 then matrixRow = (matrixRow + 1) % 10 end
    if (value & 1) ~= 0 then matrixRow = 0 end
    column = nextColumn
    enabled = (value & 4) ~= 0
end, emu.callbackType.write, 0x4016)

emu.addMemoryCallback(function()
    if not enabled then return 0 end
    local bits = 0
    for i = 0, 3 do
        if keys[matrixRow * 8 + column * 4 + i] then bits = bits | (1 << i) end
    end
    return ((~bits) << 1) & 0x1e
end, emu.callbackType.read, 0x4017)

emu.addEventCallback(function()
    frame = frame + 1
    if failure then finish(false, failure); return end
    if frame > 30000 then finish(false, "Timeout in case " .. phase); return end
    if phase > #CASES then
        finishing = finishing + 1
        if finishing == 20 then
            if maxNmi >= 2273 then finish(false, "NMI exceeded NTSC VBlank"); return end
            finish(true, "All " .. #CASES .. " keyboard/interpreter cases passed")
        end
        return
    end
    local case = CASES[phase]
    if not case.started then
        if not ready then return end
        case.started = true
        ready = false
        caseStart = #transcript + 1
    end
    if position <= #case.keys then
        tick = tick + 1
        keys = {}
        if tick <= 4 then
            for _, key in ipairs(case.keys[position]) do keys[key] = true end
        end
        if tick == 14 then tick = 0; position = position + 1 end
    elseif case.interrupt and not ready then
        tick = tick + 1
        if tick > 60 then keys = {[7] = true} end
    elseif ready then
        keys = {}
        local output = transcript:sub(caseStart)
        for _, expected in ipairs(case.expect) do
            if not output:find(expected, 1, true) then
                finish(false, "Case " .. phase .. " missing " .. expected)
                return
            end
        end
        for _, rejected in ipairs(case.reject) do
            if output:find(rejected, 1, true) then
                finish(false, "Case " .. phase .. " unexpected " .. rejected)
                return
            end
        end
        phase = phase + 1
        position = 1
        tick = 0
    end
end, emu.eventType.endFrame)
