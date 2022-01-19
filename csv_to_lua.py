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
from rich.progress import track
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
# from compress_lua_table import CompressLuaTable as compress


class CSVToLua:

    class bcolors:
        OK = '\033[92m' #GREEN
        WARNING = '\033[93m' #YELLOW
        FAIL = '\033[91m' #RED
        RESET = '\033[0m' #RESET COLOR


    class TableTypeEnum:
        TYPES = {
            'NONE' : -1,
            'CHAR' : 0,
            'VECTOR_CHAR' : 100,
            'SEQUENCE_CHAR' : 200,
            'VECTOR_SEQUENCE_CHAR' : 300,
            'VECTOR_VECTOR_CHAR' : 400,
            'BOOL' : 1,
            'VECTOR_BOOL' : 101,
            'SEQUENCE_BOOL' : 201,
            'VECTOR_SEQUENCE_BOOL' : 301,
            'VECTOR_VECTOR_BOOL' : 401,
            'INT' : 2,
            'VECTOR_INT' : 102,
            'SEQUENCE_INT' : 202,
            'VECTOR_SEQUENCE_INT' : 302,
            'VECTOR_VECTOR_INT' : 402,
            'UINT' : 3,
            'VECTOR_UINT' : 103,
            'SEQUENCE_UINT' : 203,
            'VECTOR_SEQUENCE_UINT' : 303,
            'VECTOR_VECTOR_UINT' : 403,
            'FLOAT' : 4,
            'VECTOR_FLOAT' : 104,
            'SEQUENCE_FLOAT' : 204,
            'VECTOR_SEQUENCE_FLOAT' : 304,
            'VECTOR_VECTOR_FLOAT' : 404,
            'DOUBLE' : 5,
            'VECTOR_DOUBLE' : 105,
            'SEQUENCE_DOUBLE' : 205,
            'VECTOR_SEQUENCE_DOUBLE' : 305,
            'VECTOR_VECTOR_DOUBLE' : 405,
            'LONGLONG' : 6,
            'VECTOR_LONGLONG' : 106,
            'SEQUENCE_LONGLONG' : 206,
            'VECTOR_SEQUENCE_LONGLONG' : 306,
            'VECTOR_VECTOR_LONGLONG' : 406,
            'STRING' : 7,
            'VECTOR_STRING' : 107,
            'SEQUENCE_STRING' : 207,
            'VECTOR_SEQUENCE_STRING' : 307,
            'VECTOR_VECTOR_STRING' : 407,
        }
    

    def __init__(self):
        self.JSON = 'Configs'
        self.TABLE = 'CSV'
        self.LUA = './table-{0}/'
        self.REPEAT_KEY_PREFIX = '__rt'
        self.split_num = 1000
        self.template_function = ';(function(){}\nend)()'
        self.string_index = 0
        self.global_string = {}
        self.write_flag = 1
        self.require_names = []
        self.types = {}
        self.heads = {}


    def setConfig(self, **args):
        
        self.pos = 'client'
        self.pos_id = 'ClientPosID'
        self.is_need_key = False
        self.is_need_index = False
        self.is_save_string = False
        self.is_multi_thread = False
        self.is_require = False

        if 'for' in args:
            self.pos = args['for']
            if not os.path.exists(self.LUA.format(self.pos)):
                os.mkdir(self.LUA.format(self.pos))
            if self.pos == 'server': self.pos_id = 'ServerPosID'
            elif self.pos == 'client': self.pos_id = 'ClientPosID'

        self.is_need_key = 'key' in args
        self.is_need_index = 'index' in args

        if 'string' in args:
            self.is_save_string = True
            if args['string'] and args['string'] == 'only': self.write_flag &= 2
            elif args['string'] and args['string'] == 'all': self.write_flag &= 1

        if 'require' in args:
            self.is_require = True
            if args['require'] and args['require'] == 'only': self.write_flag &= 2
            elif args['require'] and args['require'] == 'all': self.write_flag &= 1

        self.is_multi_thread = 'thread' in args
        
        with open('.config', 'r') as f:
            lines = f.readlines()
            dir_config = lines[0].strip()
            self._dir = dir_config.split('#')[1]
            self.json_dir = os.path.join(dir_config.split('#')[1], self.JSON)


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
            if (cast == float or cast == int) and str(__v).strip() == '':
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
        """
        compile sequence length, type and default
        """
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
        if not str: return ''
        if re.match('Sequence<[a-z]*, [1-9]\d*>$', str):
            return self.arg_type('s', str)
        elif re.match('vector<[a-z]*>$', str):
            return self.arg_type('v', str)
        elif re.match('vector<vector<[a-z]*>>$', str):
            return self.arg_type('vv', str)
        elif re.match('vector<(Sequence|vector)<[a-z]*, [1-9]\d*>>$', str):
            return self.arg_type('vs', str)
        return str

    
    def filter_string(self, str):
        if str == '': return 'blank'
        return str.translate({34 : '\\"'})


    def iter_csv_recursive(self, d, name, types = None):
        """
        parse customized data structure. e.g. vector<Sequence<int>>, ...
        """
        t = {}
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.iter_csv_recursive(v, name, types)
            else:
                _type = types[k]['FieldTypeName'] if types else self.types[name][k]['FieldTypeName']
                _match = self.regex_type(_type)
                if _type == 'string':
                    text = self.check_default(v, str, _type)
                    t[k] = text
                    if self.is_save_string: self.global_string[self.generate_index()] = self.filter_string(text)
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
            # if isinstance(obj, float): s += f'{obj:f}'
            # else: s += str(obj)
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


    def type_map_compile(self, _type):
        patterns = re.compile('[a-zA-Z]+').findall(_type.lower())
        for k, v in self.TableTypeEnum.TYPES.items():
            split = k.split('_')
            if len(patterns) == len(split) and len(re.compile('|'.join(patterns)).findall(k.lower())) == len(split):
                size = re.compile('[1-9]\d*').findall(_type)
                return v, int(size[0]) if size else 0
        return -1


    def get_primary_index(self, name):
        _name = self._extract_name(name)
        self.primary_index = {'idx' : -1, 'key' : None}
        for k, v in self.types[_name].items():
            ## record primary index
            if self.types[_name][k]['IndexType'] == 1:
                self.primary_index = {'idx' : self.types[_name][k][self.pos_id], 'key' : k}
                return


    def compress_lua(self, obj, name, types = None):
        s = 'local t = {}\n'

        i = 1
        for _, value in obj.items():
            line = '  t[{}]={{'.format(i - 1)
            # add splitted function for <issue#luajit2.1限制了一个function中constant的数量为65535>
            # [LuaJIT and large tables](http://lua-users.org/lists/lua-l/2010-03/msg00237.html)
            if i % self.split_num == 1:
                line = ';(function()\n' + line
            
            for k, items in value.items():
                v = self.encode(items)
                if self.is_need_key:
                    if v != '':
                        line += '{}={},'.format(k, v)
                elif self.is_need_index:
                    if len(v) != 0: line += '[{}]={},'.format(types[k]['Pos'] if types else self.types[name][k][self.pos_id], v)
                else:
                    if len(v) != 0: line += '{},'.format(v)
            line = line[:-1] + '}\n'

            # add splitted function for <issue#luajit2.1限制了一个function中constant的数量为65535>
            if i % self.split_num == 0 and i != 1:
                line += 'end)()\n'# + line

            s += line
            i += 1

        s = s[:-2] + '\n' if s[-2] == ',' else s
        if len(obj) != 0 and (i - 1) % self.split_num != 0: s += 'end)()\n'

        # define default table
        s += '\n\nlocal __default_table = {'
        # index = 1
        _heads = types.keys() if types else sorted(self.heads[name].items(), key = lambda item : item[0])
        for key in _heads:
            _type = types[key]['FieldTypeName'] if types else self.types[name][key[1]]['FieldTypeName']
            # s += '{}={},'.format(key, index)
            default_value = self.base_type(_type)
            s += '{}={},'.format(key if types else key[1], default_value if default_value != '' else '\"\"')
            # index += 1
        s = (s[:-1] if s[-1] == ',' else s) + '}\n' ### generate empty tabel possibly

        # define table type enum for server
        if (self.pos == 'server' or self.pos == 'client' and not types):
            s += '\n\nlocal head = {\n'
            for key in sorted(self.heads[name].items(), key = lambda item : item[0]):
                fields = self.types[name][key[1]]
                _pos = fields[self.pos_id]
                enum, size = self.type_map_compile(fields['FieldTypeName'])
                s += '  [{}]={{ need_local = {}, seq_size = {}, field_type = {} }},\n'.format(_pos, str(fields['NeedLocal']).lower(), size, enum)
                
            s = (s[:-2] + '\n' if s[-2] == ',' else s) + '}\n' ### generate empty tabel possibly


        # add postfix
        s += '\ndo\n'
        s += '\tlocal base = {__index = __default_table, __newindex = function() error(\"Attempt to modify read-only table\") end}\n'
        s += '\tfor k, v in pairs(t) do\n'
        s += '\t\tsetmetatable(v, base)\n'
        s += '\tend\n'
        # s += '\tbase.__metatable = false\n'
        s += 'end\n'
        if (self.pos == 'server' or self.pos == 'client') and not types:
            s += 'local {} = {{head = head, data = t, bin_pos = {}, total_line_size = {}, col_size = {}}}'.format(
                name, self.primary_index['idx'], len(obj), len(self.heads[name]))
        else:
            s += 'local {} = t'.format(name)
        s += '\nreturn {}\n'.format(name)

        return s


    def save_global_string(self):
        def revert_dict(d):
            result = {}
            for k in d:
                if d[k] not in result:
                    result[d[k]] = set()
                result[d[k]].add(k)
            return {k: result[k] if len(result[k]) > 1 else result[k].pop() for k in result}
            
        tab = 4 * ' '
        reversed_globel_string = revert_dict(self.global_string)
        with open(self.LUA.format(self.pos) + 'GlobalString.lua', 'w', encoding='utf-8') as w:
            ## count repeat items
            w.write('local {} = {{\n'.format(self.REPEAT_KEY_PREFIX))
            lines = []
            repeats = {}
            index = 1
            for v, indices in reversed_globel_string.items():
                if isinstance(indices, set) and len(indices) > 1:
                    repeats[v] = index
                    lines.append('{}"{}"'.format(tab, v))
                    index += 1
            w.write(',\n'.join(lines))
            w.write('\n}\n')

            ## all of strings
            w.write('local str = {\n')
            lines = []
            for idx, s in self.global_string.items():
                if s in repeats:
                    lines.append('{}{}[{}]'.format(tab, self.REPEAT_KEY_PREFIX, repeats[s]))
                else:
                    lines.append('{}"{}"'.format(tab, s))
            w.write(',\n'.join(lines))
            w.write('\n}\nreturn str')


    def get_global_string(self):
        return self.global_string

    
    def save_require(self):
        with open(self.LUA.format(self.pos) + 'init.lua', 'w') as w:
            w.write('local ServerTable = {}\n')
            for name in self.require_names:
                w.write('ServerTable.{} = require \"{}\"\n'.format(name[:-4], name[:-4]))
            w.write('return ServerTable')

    
    def _extract_name(self, name):
        return name if len(name.split('/')) == 1 else name.split('/')[1]


    def csv_to_lua(self):
        works = os.listdir(self.json_dir)
        self._load_heads(works)
            
        self.progress = Progress(
            TimeElapsedColumn(),
            BarColumn(),
            TextColumn('{task.description}')
        )
        # TODO: process with multi-process
        self.task_id = self.progress.add_task("", total=len(works))
        with self.progress:
            if self.is_multi_thread:
                with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
                    futures = [executor.submit(self._csv_to_lua, file=work) for work in works]
                    for future in concurrent.futures.as_completed(futures):
                        # if future.result() is not None:
                        #     print(future.result())
                        pass
            else:
                for work in works:
                    self._csv_to_lua(work)

            if self.is_save_string: self.save_global_string()
            if self.is_require: self.save_require()

            self.progress.update(self.task_id, description='[bold green]process done!')


    def _load_heads(self, works):
        def _load_fields(_data, _name=None):
            if _data is None: return
            name = _name if _name is not None else _data['MainTableName']
            self.types[name] = {}
            self.heads[name] = {}
            for field in _data['Fields']:
                # config for server or client
                if self.pos == 'server' and field['ForServer'] or self.pos == 'client' and field['ForClient']:
                    self.types[name][field['FieldName']] = field
                    self.heads[name][field[self.pos_id]]= field['FieldName']

        for f in works:
            with open(os.path.join(self.json_dir, f), 'rb') as file:
                data = json.load(file)
                _load_fields(data)
                children = data['Children']
                if children:
                    for child in children:
                        if child: _load_fields(data, child['MainTableName'])

    
    def get_heads(self):
        return self.types, self.heads


    def _csv_to_lua(self, file):
        # if file[:-5] != 'BuffEffectTable': return
        descr = '[bold #FFC900](processing {}...)'.format(file[:-5])
        self.progress.update(self.task_id, description=descr)
        self.progress.update(self.task_id, advance=1)

        with open(os.path.join(self.json_dir, file), 'rb') as file:
            data = json.load(file)
            def process(data):
                if data is None: return
                def extract_table(name, key):
                    # header adaptation
                    data = pd.read_csv(os.path.join(self._dir, self.TABLE, name)).drop([0])
                    columns = list(set(data.columns.tolist()) - set(self.heads[key].values()))
                    data = data.drop(columns=columns)
                    data = data.dropna(axis=0, how='all')
                    _heads = sorted(self.heads[key].items(), key = lambda item : item[0])
                    data = data[[x[1] for x in _heads]]
                    return data

                def process_one_table(name, data):
                    file_path = self.LUA.format(self.pos) + os.path.basename(name).replace('.csv', '.lua')
                    if os.path.exists(file_path) and self.write_flag & 1:
                        os.remove(file_path)

                    # sort table if server
                    self.get_primary_index(name[:-4])
                    if self.pos == 'server':
                        try:
                            _index = self.primary_index['key']
                            if _index and not data.empty:
                                _type = self.types[self._extract_name(name[:-4])][_index]['FieldTypeName']
                                data[_index] = data[_index].astype(int if _type in ['int', 'uint', 'long long'] else object)
                                data.sort_values(_index, inplace=True)
                        except Exception as e:
                            print(f'{self.bcolors.FAIL} error while sort table: ' + name + f'{self.bcolors.RESET}')

                    lua_raw_data = data.to_dict('index')
                    table = self.iter_csv_recursive(lua_raw_data, self._extract_name(name[:-4]))
                    try:
                        # print(f'processing {self.bcolors.OK}' + name + f'{self.bcolors.RESET} ...')
                        name = self._extract_name(name)
                        self.require_names.append(name)
                        if self.write_flag & 1:
                            with open(file_path, 'w', encoding='utf-8') as w:
                                w.write(self.compress_lua(table, name[:-4]))
                    except Exception as e:
                        print(f'{self.bcolors.FAIL} error while compress lua: ' + name + f'{self.bcolors.RESET}')
                        traceback.print_exc()

                # process combined table
                if len(data['TableLocations']) > 1:
                    t = pd.concat([extract_table(v['ExcelPath'], data['MainTableName']) for v in data['TableLocations']], ignore_index=True)
                    t.index += 1
                    process_one_table(data['MainTableName'] + '.csv', t)
                else:
                    for item in data['TableLocations']:
                        name = item['ExcelPath']
                        process_one_table(name, extract_table(name, data['MainTableName']))
                    
            process(data)
            process(data['Children'][0] if data['Children'] else None) # process child table


CSVToLua = CSVToLua()

__all__ = ['CSVToLua']