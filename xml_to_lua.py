import os
import xmltodict
import traceback
from slpp import slpp as lua
from compress_lua_table import CompressLuaTable as compress


class XmlToLua:

    class bcolors:
        OK = '\033[92m' #GREEN
        WARNING = '\033[93m' #YELLOW
        FAIL = '\033[91m' #RED
        RESET = '\033[0m' #RESET COLOR

    def __init__(self):
        self.EDITOR_DIR = './SkillData/'

    def is_int(self, n):
        try:
            int(n)
        except ValueError:
            return False
        return True

    def is_float(self, n):
        try:
            float(n)
        except ValueError:
            return False
        return True

    def is_boolean(self, n):
        if n == 'true' or n == 'false':
            return True
        return False

    def to_boolean(self, n):
        if n == 'true': return True
        elif n == 'false': return False

    def filter_key(self, k):
        return k == '@xmlns:xsd' or k == '@xmlns:xsi'

    def iter_xml_recursive(self, d):
        t = {}
        for k, v in d.items():
            if isinstance(v, dict):
                t[k] = self.iter_xml_recursive(v)
            elif isinstance(v, list):
                t[k] = self.iter_xml_recursive({i : v[i] for i in range(len(v))})
            else:
                if v is None:
                    t[k] = None
                elif self.is_int(v):
                    t[k] = int(v)
                elif self.is_float(v):
                    t[k] = float(v)
                elif self.is_boolean(v):
                    t[k] = self.to_boolean(v)
                elif not self.filter_key(k):
                    t[k] = v
                    # return
        return t


    def xml_to_lua(self):
        if not os.path.exists(self.EDITOR_DIR):
            os.mkdir(self.EDITOR_DIR)
        with open('.config', 'r') as _f:
            lines = _f.readlines()
            dir_config = lines[1].strip()
            dir = dir_config.split('#')[1]
            for path, _, fs in os.walk(dir):
                for f in fs:
                    if f.endswith('.txt'):
                        print(f'processing {self.bcolors.OK}' + os.path.join(path, f) + f'{self.bcolors.RESET}...')
                        # print(os.path.join(EDITOR_DIR + path[len(dir) + 1:], f.replace('.txt', '.lua')))
                        _dir = os.path.join(self.EDITOR_DIR + path[len(dir) + 1:])
                        if not os.path.exists(_dir):
                            os.mkdir(_dir)
                        with open(os.path.join(path, f), 'rb') as file:
                            try:
                                table = self.iter_xml_recursive(dict(xmltodict.parse(file)))
                                file_path = os.path.join(_dir, f.replace('.txt', '.lua'))
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                                name = f[:-4]
                                compress.process_file(table, name, file_path)
                            except Exception as e:
                                print(f'{self.bcolors.FAIL} error: ' + os.path.join(path, f) + f'{self.bcolors.RESET}')
                                traceback.print_exc()

XmlToLua = XmlToLua()

__all__ = ['XmlToLua']