-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Adds the nonplanar_top test coupons to the current plate.

info = {
    id = "add_coupons",
    type = "project.plugin",
    title = "Add nonplanar test coupons",
    menu = "Nonplanar top/Add test coupons",
    params = {
        {
            name = "coupon",
            label = "Coupon",
            type = "combobox",
            allowed_values = {"All three", "Dome 50 mm", "Ramp 2 deg", "Wave 80 mm"},
            default = "All three"
        },
        {name = "set_top_layers", label = "Make sure this plate has at least 5 top layers / 0.7 mm", type = "bool", default = true}
    }
}

-- file, corner position in the "All three" layout (spaced so the shroud clears the neighbours)
local COUPONS = {
    ["Dome 50 mm"] = {file = "assets/coupon_dome_50mm.stl", x = 0, y = 9.5},
    ["Ramp 2 deg"] = {file = "assets/coupon_ramp_2deg.stl", x = 75, y = 0},
    ["Wave 80 mm"] = {file = "assets/coupon_wave_80mm.stl", x = 65, y = 42.5}
}
local ORDER = {"Dome 50 mm", "Ramp 2 deg", "Wave 80 mm"}

function execute(opts)
    if opts.coupon == "All three" then
        -- one object with three parts keeps the spacing; PrusaSlicer centres it on the plate
        local first = COUPONS[ORDER[1]]
        local others = {}
        for i = 2, #ORDER do
            local c = COUPONS[ORDER[i]]
            others[#others + 1] = {
                mesh = api.load_stl(c.file),
                type = VolumeType.Solid,
                translate = {x = c.x, y = c.y}
            }
        end
        api.project:add_object {
            mesh = api.load_stl(first.file),
            translate = {x = first.x, y = first.y},
            other_volumes = others
        }
    else
        local c = COUPONS[opts.coupon]
        if c == nil then
            error("unknown coupon: " .. tostring(opts.coupon))
        end
        api.project:add_object {mesh = api.load_stl(c.file)}
    end

    if opts.set_top_layers then
        local print_settings = api.project:current_bed():print_presets()
        local function at_least(key, minimum)
            local ok, current = pcall(function() return print_settings:value(key) end)
            if not ok or type(current) ~= "number" or current < minimum then
                print_settings:set(key, minimum)
            end
        end
        at_least("top_solid_layers", 5)
        at_least("top_solid_min_thickness", 0.7)
    end
end
