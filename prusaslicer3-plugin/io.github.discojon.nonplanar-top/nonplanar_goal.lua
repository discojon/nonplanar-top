-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Print goal: the slicing settings nonplanar_top needs.
-- The conversion itself is done by the nonplanar_top post-processing script; PrusaSlicer 3
-- plugins cannot change G-code yet.

info = {
    id = "nonplanar_goal",
    type = "print.print_mode",
    title = "Nonplanar top surfaces",
    params = {
        {name = "top_layers", label = "Minimum top solid layers", type = "int", default = 5},
        {name = "top_thickness", label = "Minimum top shell thickness [mm]", type = "float", default = 0.7}
    }
}

-- per-slot values come back as 1-based tables, others as scalars
local function largest(value)
    if type(value) == "table" then
        local m = nil
        for _, v in pairs(value) do
            if type(v) == "number" and (m == nil or v > m) then m = v end
        end
        return m or 0
    end
    return tonumber(value) or 0
end

function execute(opts)
    local config = api.config
    return {
        -- the stair-stepped top layers in smoothed areas are removed and reprinted as a skin,
        -- so the layers below have to be solid
        top_solid_layers = math.max(largest(config:value("top_solid_layers")), opts.top_layers),
        top_solid_min_thickness = math.max(largest(config:value("top_solid_min_thickness")), opts.top_thickness),
        -- ironing would run on the flat layer the skin then covers
        ironing = false
    }
end
