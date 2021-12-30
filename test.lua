function _load(src)
    return require(src)
end

local t = _load('Table-client.AwardPackTable')
print(#t)

local sequence = setmetatable({}, {
    __index = function()
        return 'sequence'
    end
})

local vector = setmetatable({}, {
    __index = function(t, k)
        if k == 'vector' then
            return true
        elseif k == 'sequence' then
            return false
        end
    end
})

-- for k, v in pairs(t) do
--     for _, _v in pairs(v.Target) do
--         print(#_v)
--     end
-- end

-- local a = {
--     _v = 0,
--     size = 0,
--     {
--         1,
--         2,
--         3,
--         _s = 0,
--         size = 3,
--     },
--     {
--         4,
--         5,
--         6,
--     }
-- }
-- setmetatable(a, vector)
-- print(a.vector)
-- print(#a)
-- for _, v in pairs(a) do
--     -- print(v.vector)
--     for _, _v in pairs(v) do
--         -- print(_v)
--     end
-- end