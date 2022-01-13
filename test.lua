function _load(src)
    print(src)
    return require(src)
end

-- local t = _load('table-server.ItemAchievingTypeTable')
-- print(#t)

-- local t = {}
-- t.a = 1
-- t.b = 2

-- local d = {}

-- setmetatable(d, {__index = t})
-- print(d.a)