import json
import pandas as pd
import math
import os
import traceback
import re
import concurrent.futures
# import subprocess
# from slpp import slpp as lua
from numbers import Number
# from compress_lua_table import CompressLuaTable as compress


class CSVToLua:

    class bcolors:
        OK = '\033[92m' #GREEN
        WARNING = '\033[93m' #YELLOW
        FAIL = '\033[91m' #RED
        RESET = '\033[0m' #RESET COLOR

    def __init__(self):
        self.JSON = 'Configs'
        self.TABLE = 'CSV'
        self.LUA = './table-{0}/'
        self.split_num = 1000
        self.template_function = ';(function(){}\nend)()'
        self.string_index = 0
        self.global_string = {}


    def setConfig(self, pos, is_need_key=False, is_need_index=False):
        self.pos = pos
        self.pos_id = 'ClientPosID'
        if self.pos == 'server': self.pos_id = 'ServerPosID'
        elif self.pos == 'client': self.pos_id = 'ClientPosID'
        if not os.path.exists(self.LUA.format(self.pos)):
            os.mkdir(self.LUA.format(self.pos))

        self.is_need_key = is_need_key
        self.is_need_index = is_need_index


    def generate_index(self):
        self.string_index += 1
        return self.string_index


    def check_default(self, _v, cast, _type):
        """
        set default value
        """
        def is_nan(__v):
            if type(__v) == float:
                return math.isnan(__v)
            if (cast == float or cast == int) and __v.strip() == '':
                return True
            return False
        def filter_escape(__v):
            if cast == str and type(__v) == str:
                # include `'`、`\`
                return __v.translate({39 : '\\\'', 92 : '\\\\'})
            return __v
        
        return self.base_type(_type) if is_nan(_v) else cast(filter_escape(_v))


    def sequence_to_dict(self, value, partten, length, cast, default):
        """
        parse `Sequence<T>`
        """
        array = {}

        sequence = value.split(partten)
        for i in range(length):
            try:
                array[i + 1] = cast(sequence[i])
            except Exception as e:
                array[i + 1] = default
            
        array[len(array) + 1] = '_size={}'.format(len(array))
        array[len(array) + 1] = '_t=\"s\"'
        return array
        return value


    def vector_to_list(self, value, partten, cast, func=None, *args):
        """
        parse `vector<T>`
        """
        l = {}
        if value is None or value == '\"\"' or value.strip() == '':
            l[1] = '_size=0'
            l[2] = '_t=\"v\"'
            return l
        
        sequence = value.split(partten)
        for i in range(len(sequence)):
            if func is not None:
                l[i + 1] = func(sequence[i], *args)
            elif sequence[i].strip() != '':
                l[i + 1] = cast(sequence[i])
                
        l[len(l) + 1] = '_size={}'.format(len(l))
        l[len(l) + 1] = '_t=\"v\"'
        return l


    def arg_type(self, index, _str):
        int_pattern = re.compile('[1-9]\d*|long long|uint|int').findall(_str)
        float_pattern = re.compile('[1-9]\d*|double|float').findall(_str)
        string_pattern = re.compile('[1-9]\d*|string').findall(_str)
        bool_pattern = re.compile('[1-9]\d*|bool').findall(_str)
        if len(int_pattern) == 2:
            return index, ['=', int(int_pattern[1]), int, 0]
        elif len(float_pattern) == 2:
            return index, ['=', int(float_pattern[1]), float, 0.0]
        elif len(string_pattern) == 2:
            return index, ['=', int(string_pattern[1]), str, '']
        elif len(bool_pattern) == 2:
            return index, ['=', int(bool_pattern[1]), bool, False]
        elif int_pattern: return index, int, 0
        elif float_pattern: return index, float, 0.0
        elif string_pattern: return index, str, ''
        elif bool_pattern: return index, bool, False
        return _str


    def regex_type(self, str):
        """
        regex customized data structure.
        """
        if re.match('Sequence<[a-z]*, [1-9]\d*>$', str):
            return self.arg_type('s', str)
        elif re.match('vector<[a-z]*>$', str):
            return self.arg_type('v', str)
        elif re.match('vector<vector<[a-z]*>>$', str):
            return self.arg_type('vv', str)
        elif re.match('vector<(Sequence|vector)<[a-z]*, [1-9]\d*>>$', str):
            return self.arg_type('vs', str)
        return str


    def iter_csv_recursive(self, d):
        """
        parse customized data structure. e.g. vector<Sequence<int>>, ...
        """
        t = {}
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.iter_csv_recursive(v)
            else:
                _type = self.types[k]['FieldTypeName']
                _match = self.regex_type(_type)
                if _type == 'string':
                    text = self.check_default(v, str, _type)
                    t[k] = text
                    # self.global_string[self.generate_index()] = text
                elif _type in ['int', 'uint', 'long long']:
                    t[k] = self.check_default(v, int, _type)
                elif _type in ['float', 'double']:
                    t[k] = self.check_default(v, float, _type)
                elif _type == 'bool':
                    t[k] = False if v == 0 or v == 'nan' else True
                elif _match:
                    if _match[0] == 's':
                        t[k] = self.sequence_to_dict(self.check_default(v, str, 'string'), *_match[1])
                    elif _match[0] == 'v':
                        t[k] = self.vector_to_list(self.check_default(v, str, 'string'), '|', _match[1])
                    elif _match[0] == 'vv':
                        t[k] = self.vector_to_list(self.check_default(v, str, 'string'), '|', None, self.vector_to_list, *['=', _match[1]])
                    elif _match[0] == 'vs':
                        t[k] = self.vector_to_list(self.check_default(v, str, 'string'), '|', None, self.sequence_to_dict, *_match[1])
                else:
                    print(f'`{self.bcolors.FAIL}' + _type + f'{self.bcolors.RESET}` is not processed!')
                    # return
        return t


    def encode(self, obj):
        s = ''
        if isinstance(obj, str):
            if re.match('_size=[0-9]\d*', obj) or re.match('_t=\"[s|v]\"', obj):
                s += obj
            else:
                s += '"{}"'.format(obj.replace(r'"', r'\"'))
        elif isinstance(obj, bool):
            s += str(obj).lower()
        elif obj is None:
            # pass
            # s += '{_size=0,_t="v"}'
            s += '{}'
        elif isinstance(obj, Number):
            s += str(obj)
        elif isinstance(obj, dict):
            s += "{"
            contents = [self.encode(v) for _, v in obj.items()]
            s += ','.join(contents)
            s += "}"
        return s

    
    def base_type(self, _type):
        if _type == 'string':
            return ''
        elif _type in ['int', 'uint', 'long long']:
            return 0
        elif _type in ['float', 'double']:
            return 0.0
        elif _type == 'bool':
            return 'false'
        else:
            _match = self.regex_type(_type)
            if _match:
                if _match[0] == 'v' or _match[0] == 's': return '{}'
                elif _match[0] == 'vv' or _match[0] == 'vs': return '{{}}'
        return '{}'


    def compress_lua(self, obj, name):
        s = 'local t = {}\n'

        for index, value in obj.items():
            line = '  t[{}]={{'.format(index)
            # add splitted function for <issue#luajit2.1限制了一个function中constant的数量为65535>
            # [LuaJIT and large tables](http://lua-users.org/lists/lua-l/2010-03/msg00237.html)
            if index % self.split_num == 1:
                line = ';(function()\n' + line
            
            for k, items in value.items():
                v = self.encode(items)
                if self.is_need_key:
                    if v != '':
                        line += '{}={},'.format(k, v)
                elif self.is_need_index:
                    if len(v) != 0: line += '[{}]={},'.format(self.types[k][self.pos_id], v)
                else:
                    if len(v) != 0: line += '{},'.format(v)
            line = line[:-1] + '}\n'

            # add splitted function for <issue#luajit2.1限制了一个function中constant的数量为65535>
            if index % self.split_num == 0 and index != 1:
                line += 'end)()\n'# + line

            s += line

        s = s[:-2] + '\n' if s[-2] == ',' else s
        if len(obj) != 0: s += 'end)()\n'

        # define default table
        s += '\n\nlocal __default_table = {'
        index = 1
        for key in sorted(self.heads.items(), key = lambda item : item[0]):
            _type = self.types[key[1]]['FieldTypeName']
            # s += '{}={},'.format(key, index)
            default_value = self.base_type(_type)
            s += '{}={},'.format(key[1], default_value if default_value != '' else '\"\"')
            index += 1
        s = (s[:-1] if s[-1] == ',' else s) + '}\n'

        # add postfix
        s += '\ndo\n'
        s += '\tlocal base = {__index = __default_table, __newindex = function() error(\"Attempt to modify read-only table\") end}\n'
        s += '\tfor k, v in pairs(t) do\n'
        s += '\t\tsetmetatable(v, base)\n'
        s += '\tend\n'
        s += '\tbase.__metatable = false\n'
        s += 'end\n'
        s += 'local {} = t'.format(name)
        s += '\nreturn {}\n'.format(name)

        return s

    def save_global_string(self):
        with open(self.LUA.format(self.pos) + 'GlobalString.lua', 'w', encoding='utf-8') as w:
            w.write('str = {}\n')
            lines = []
            for idx, s in self.global_string.items():
                lines.append('str[{}] = "{}"'.format(idx, s))
            w.write('\n'.join(lines))
            w.write('\nreturn str')


    def csv_to_lua(self):
        with open('.config', 'r') as f:
            lines = f.readlines()
            dir_config = lines[0].strip()
            self._dir = dir_config.split('#')[1]
            self.json_dir = os.path.join(dir_config.split('#')[1], self.JSON)
            works = os.listdir(self.json_dir)
            
            # thread attemption
            # with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            #     futures = [executor.submit(self._csv_to_lua, file=work) for work in works]
            #     for future in concurrent.futures.as_completed(futures):
            #         print(future.result())
            for work in works:
                self._csv_to_lua(work)


    def _csv_to_lua(self, file):
        with open(os.path.join(self.json_dir, file), 'rb') as file:

            data = json.load(file)
            def process(data):
                self.types = {}
                self.heads = {}
                if data is None: return
                # load variable type
                # if data['MainTableName'] != 'OrnamentBarterTable': return
                for field in data['Fields']:
                    # config for server or client
                    if self.pos == 'server' and field['ForServer'] or self.pos == 'client' and field['ForClient']:
                        self.types[field['FieldName']] = field
                        self.heads[field[self.pos_id]]= field['FieldName']

                for item in data['TableLocations']:
                    name = item['ExcelPath']
                            
                    file_path = self.LUA.format(self.pos) + os.path.basename(name).replace('.csv', '.lua')
                    if os.path.exists(file_path):
                        # continue
                        os.remove(file_path)
                            
                    # header adaptation
                    data = pd.read_csv(os.path.join(self._dir, self.TABLE, name)).drop([0])
                    columns = list(set(data.columns.tolist()) - set(self.heads.values()))
                    data = data.drop(columns=columns)
                    data = data.dropna(axis=0, how='all')
                    _heads = sorted(self.heads.items(), key = lambda item : item[0])
                    data = data[[x[1] for x in _heads]]
                    
                    lua_raw_data = data.to_dict('index')
                    table = self.iter_csv_recursive(lua_raw_data)
                    try:
                        print(f'processing {self.bcolors.OK}' + name + f'{self.bcolors.RESET} ...')
                        if len(name.split('/')) == 2: name = name.split('/')[1]
                        with open(file_path, 'w', encoding='utf-8') as w:
                            w.write(self.compress_lua(table, name[:-4]))
                        # self.save_global_string()
                    except Exception as e:
                        print(f'{self.bcolors.FAIL} error: ' + name + f'{self.bcolors.RESET}')
                        traceback.print_exc()
            process(data)
            process(data['Children'][0] if data['Children'] else None) # process child table
                

CSVToLua = CSVToLua()

__all__ = ['CSVToLua']