import os
import re

from pathlib import Path
from rich.console import Console


class PeelDeprecatedModule:

    def __init__(self):
        self.SCRIPT_DIR = './script/'
        self.DECLARED_GLOBAL = 'DeclaredGlobal.lua'
        self.root_modules = {}
        self.modules_pattern = re.compile('^module\("\w+(\.\w+){0,1}", package.seeall\)')
        self.name_pattern = re.compile('"\w+(\.\w+){0,1}"')
        self.class_pattern = re.compile('\w+\s=\sclass\("\w+"(, \w+){0,1}\)')
        self.declared_pattern = re.compile('declareGlobal\("\w+", \w+(\.\w+){0,1}\)')

        self.console = Console()


    def search_pattern(self, pattern, content):
        result = pattern.search(content)
        if result and result.group():
            line = result.group()
            name = self.name_pattern.search(line).group()
            name = name[1:-1]
            return line, name
        return None, None


    def write_content(self, content, path):
        with open(path, 'w', encoding='utf-8') as w:
            w.write(content)


    def _peel(self):
        with open('.config', 'r') as _f:
            lines = _f.readlines()
            dir_config = lines[3].strip()
            _dir = dir_config.split('#')[1]
            for path, dirs, fs in os.walk(_dir):
                for __dir in dirs:
                    script_dir = Path(os.path.join(self.SCRIPT_DIR, path[len(_dir) + 1:])).as_posix()
                    script_dir = Path(os.path.join(script_dir, __dir)).as_posix()
                    if not os.path.exists(script_dir) and not script_dir.startswith('.'):
                        os.mkdir(script_dir)
                for f in fs:
                    if f.endswith('.lua'):
                        script_dir = Path(os.path.join(self.SCRIPT_DIR, path[len(_dir) + 1:])).as_posix()
                        if not os.path.exists(script_dir) and not script_dir.startswith('.'):
                            os.mkdir(script_dir)
                        with open(os.path.join(path, f), 'r', encoding='utf-8') as file:
                            lines = [l for l in file]
                            content = ''.join(lines)
                            _path = script_dir + '/' + f

                            def annotation_module(old_syntax, new_syntax):
                                try:
                                    index = lines.index(old_syntax + '\n')
                                    lines[index] = new_syntax
                                except ValueError as e:
                                    self.console.log(f)
                                    
                            ## I search pattern with function `module``
                            module_syntax, module_name = self.search_pattern(self.modules_pattern, content)
                            if module_syntax and module_name:
                                if module_name not in self.root_modules:
                                    self.root_modules[module_name] = 0
                                self.root_modules[module_name] += 1
                                ## II search pattern with `declare global`
                                declare_syntax, declare_name = self.search_pattern(self.declared_pattern, content)
                                if declare_syntax and declare_name:
                                    pass
                                ## III search pattern with `class`
                                class_syntax, class_name = self.search_pattern(self.class_pattern, content)
                                if class_syntax and class_name:
                                    declare_global_syntax = 'local {}\n{}.{} = {}'.format(class_syntax, module_name, class_name, class_name)
                                    annotation_module(module_syntax, '-- {}\n'.format(module_syntax))
                                    annotation_module(class_syntax, declare_global_syntax)
                                    self.write_content(''.join(lines), _path)
                                else:
                                    ## IV not exist declaration `class`
                                    annotation_module(module_syntax, '-- {}\n'.format(module_syntax))
                                    self.write_content(''.join(lines), _path)


    def get_modules(self):
            return self.root_modules


    def write_declared_global(self):
        lines = []

        lines.append('local __g = _G')
        lines.append('function makeGlobal(_name)')
        lines.append('    setmetatable(_name, {')
        lines.append('        __newindex = function(_, name, value)')
        lines.append('            rawset(__g, name, value)')
        lines.append('        end,')
        lines.append('')
        lines.append('        __index = function(_, name)')
        lines.append('            return rawget(__g, name)')
        lines.append('        end')
        lines.append('    })')
        lines.append('end')

        modules = dict(sorted(self.root_modules.items()))
        pattern = re.compile('(?P<key>\w+)')
        unique_module = set()
        for g, _ in modules.items():
            res = pattern.findall(g)
            if res and res[0] not in unique_module:
                unique_module.add(res[0])
                lines.append('\n{} = {{}}\nmakeGlobal("{}", {})'.format(res[0], res[0], res[0]))
            if res and len(res) == 2:
                lines.append('{}.{} = {{}}'.format(res[0], res[1]))  

        self.write_content('\n'.join(lines), os.path.join(self.SCRIPT_DIR, self.DECLARED_GLOBAL))


    def peel(self):
        self._peel()
        self.write_declared_global()
                      
        

PeelDeprecatedModule = PeelDeprecatedModule()

__all__ = ['PeelDeprecatedModule']