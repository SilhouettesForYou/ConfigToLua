function _load(src)
    print(src)
    return require(src)
end

local t = _load('table-client.GlobalString')
print(#t)
