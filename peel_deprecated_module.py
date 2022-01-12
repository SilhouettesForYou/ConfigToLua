import os
import re
import shutil

from git import Repo
from luaparser import ast
from luaparser.astnodes import Varargs
from luaparser.builder import SyntaxException
from pathlib import Path
from rich import print
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)


class PeelDeprecatedModule:

    class FunctionVisitor(ast.ASTVisitor):

        def __init__(self) -> None:
            super().__init__()
            self.function_names = {}
            self.enum_names = []

        def visit_Function(self, node):
            if isinstance(node.name, ast.Name) and isinstance(node.args, ast.List):
                self.function_names[str(node.name.id)] = node.args

        def visit_Assign(self, node):
            for target in node.targets:
                # if isinstance(target, ast.Name):
                #     print(target.id, target.first_token.column)
                if isinstance(target, ast.Name) and target.first_token.column == 0:
                    self.enum_names.append(target.id)

        def get(self):
            return self.function_names, self.enum_names


    def __init__(self):
        self.SCRIPT_DIR = './script/'
        self.DECLARED_GLOBAL = 'DeclaredGlobal.lua'
        self.root_modules = {}
        self.modules_pattern = re.compile('module\("\w+(\.\w+){0,1}", package.seeall\)')
        self.name_pattern = re.compile('"\w+(\.\w+){0,1}"')
        self.class_pattern = re.compile('\w+\s*=\s*class\("\w+"(, \w+){0,1}\)')
        self.declared_pattern = re.compile('declareGlobal\("\w+", \w+(\.\w+){0,1}\)')

        self.special_files = {
            'array' : [
                {
                    'lineno' : 1,
                    'syntax' : '-- module("Common", package.seeall)'
                },
                {
                    'lineno' : 8,
                    'syntax' : 'Common.array = {}'
                }
            ],
            'Main' : [
                {
                    'lineno' : 13,
                    'syntax' : 'require "Common/define"\nrequire "DeclaredGlobal"'
                }
            ]
        }

    
    def set_config(self, **args):
        if '--copy' in args:
            self.copy_flag = True
        else:
            self.copy_flag = False


    def search_pattern(self, content, pattern, sub_pattern=None):
        result = pattern.search(content)
        if result and result.group():
            line = result.group()
            if sub_pattern:
                name = sub_pattern.search(line).group()
                name = name[1:-1]
                return line, name
            return line, None
        return None, None


    def write_content(self, content, path):
        with open(path, 'w', encoding='utf-8') as w:
            w.write(content)

    
    def clear_repo(self, script_dir):
        print('git checkout .')
        self.remote_dir = script_dir
        splits = self.remote_dir.split('\\')
        self.repo = Repo('\\'.join(splits[:-3]))
        if self.repo.is_dirty(): self.repo.index.checkout(force=True)


    def _compute_len(self, root_dir):
        num = 0
        for _, _, fs in os.walk(root_dir):
            for f in fs:
                if f.endswith('.lua'):
                    num += 1
        return num

    def _index_of(self, l, v):
        for i in range(len(l)):
            if l[i].strip() == v.strip():
                return i
        return None


    def add_scope(self, lines, scope):
        def _add_scope(old_syntax, new_syntax):
            index = self._index_of(lines, old_syntax)
            if index:
                lines[index] = new_syntax
            else:
            # try:
            #     index = lines.index(old_syntax + '\n')
            #     lines[index] = new_syntax
            # except ValueError as e:
            #     print(lines[20], old_syntax)
            #     print(''.join(lines).find(old_syntax))
                print('Syntax not found in [italic magenta]{}[/italic magenta]\nOld Syntax: [italic red]{}[/italic red]\nNew SynTax: [italic yellow]{}[/italic yellow]'.format(scope, old_syntax, new_syntax))

        src = ''.join(lines)
        try:
            tree = ast.parse(src)
            visitor = self.FunctionVisitor()
            visitor.visit(tree)
            
            funcs, enums = visitor.get()
            if len(funcs) != 0 or len(enums) != 1:
                lines.append('\n\n')
            for func, args_list in funcs.items():
                args_pattern = ['...' if isinstance(v, ast.Varargs) else v.id for v in args_list]
                function_pattern = re.compile('function\s*{}\({}\).*'.format(func, ',\s*'.join(args_pattern)))
                args_pattern = re.compile('\(.*\)')
                function_syntax, args_list = self.search_pattern(src, function_pattern, args_pattern)
                if function_syntax:
                    # print(function_syntax)
                    # _add_scope(function_syntax, 'function {}.{}({})\n'.format(scope, func, args_list))
                    _add_scope(function_syntax, 'local function {}({})\n'.format(func, args_list))
                    lines.append('{}.{} = {}\n'.format(scope, func, func))

            for enum in enums:
                enum_pattern = re.compile(r'[^local "]\b{}\b\s*[^=<>~]=[^=].*'.format(enum))
                enum_syntax, _ = self.search_pattern(src, enum_pattern)
                if enum_syntax:
                    # print(enum_syntax, re.compile('\n{').search(enum_syntax))
                    if re.compile('\n{').search(enum_syntax):
                        enum_syntax = enum_syntax.split('\n')[0]
                    # _add_scope(enum_syntax, '{}.{}\n'.format(scope, enum_syntax.strip()))
                    _add_scope(enum_syntax, 'local {}\n'.format(enum_syntax.strip()))
                    lines.append('{}.{} = {}\n'.format(scope, enum, enum))

        except SyntaxException as e:
            print(scope)

        return ''.join(lines)


    def _peel(self):
        with open('.config', 'r') as _f:
            lines = _f.readlines()
            dir_config = lines[3].strip()
            _dir = dir_config.split('#')[1]
            self.clear_repo(_dir)
            progress = Progress(
                TimeElapsedColumn(),
                BarColumn(),
                TextColumn('{task.description}')
            )
            task_id = progress.add_task("", total=self._compute_len(_dir))
            with progress:
                for path, dirs, fs in os.walk(_dir):
                    for __dir in dirs:
                        script_dir = Path(os.path.join(self.SCRIPT_DIR, path[len(_dir) + 1:])).as_posix()
                        script_dir = Path(os.path.join(script_dir, __dir)).as_posix()
                        if not os.path.exists(script_dir) and not script_dir.startswith('.'):
                            os.mkdir(script_dir)
                    for f in fs:
                        if f.endswith('.lua'):
                            if f != 'Color.lua': continue
                            script_dir = Path(os.path.join(self.SCRIPT_DIR, path[len(_dir) + 1:])).as_posix()
                            if not os.path.exists(script_dir) and not script_dir.startswith('.'):
                                os.mkdir(script_dir)
                            with open(os.path.join(path, f), 'r', encoding='utf-8') as file:
                                descr = '[bold #FFC900]Commented Code: {}...'.format(f)
                                progress.update(task_id, description=descr)
                                lines = [l for l in file]
                                content = ''.join(lines)
                                _path = script_dir + '/' + f

                                def annotation_module(old_syntax, new_syntax):
                                    try:
                                        index = lines.index(old_syntax + '\n')
                                        lines[index] = new_syntax
                                    except ValueError as e:
                                        print(f)
                                
                                def process_special_files(name):
                                    if name in self.special_files:
                                        for v in self.special_files[name]:
                                            lines[v['lineno'] - 1] = v['syntax'] + '\n'
                                        self.write_content(''.join(lines), _path)
                                        return True
                                    return False

                                if process_special_files(f[:-4]):
                                   continue
                                        
                                ## I search pattern with function `module``
                                module_syntax, module_name = self.search_pattern(content, self.modules_pattern, self.name_pattern)
                                if module_syntax and module_name:
                                    if module_name not in self.root_modules:
                                        self.root_modules[module_name] = 0
                                    self.root_modules[module_name] += 1
                                    ## II search pattern with `declare global`
                                    declare_syntax, declare_name = self.search_pattern(content, self.declared_pattern, self.name_pattern)
                                    if declare_syntax and declare_name:
                                        pass
                                    ## III search pattern with `class`
                                    class_syntax, class_name = self.search_pattern(content, self.class_pattern, self.name_pattern)
                                    if class_syntax and class_name:
                                        declare_global_syntax = 'local {}\n{}.{} = {}\n'.format(class_syntax, module_name, class_name, class_name)
                                        annotation_module(module_syntax, '-- {}\n'.format(module_syntax))
                                        annotation_module(class_syntax, declare_global_syntax)
                                        self.write_content(''.join(lines), _path)
                                    else:
                                        ## IV not exist declaration `class`
                                        annotation_module(module_syntax, '-- {}\n'.format(module_syntax))
                                        self.write_content(self.add_scope(lines, module_name), _path)
                                progress.update(task_id, advance=1)
                progress.update(task_id, description='[bold green]process done!')


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
                lines.append('\n{} = {{}}\nmakeGlobal({})'.format(res[0], res[0]))
            if res and len(res) == 2:
                lines.append('{}.{} = {{}}\nmakeGlobal({}.{})'.format(res[0], res[1], res[0], res[1]))

        self.write_content('\n'.join(lines), os.path.join(self.SCRIPT_DIR, self.DECLARED_GLOBAL))


    def copy_to_remote(self):
        if self.copy_flag:
            shutil.copytree(self.SCRIPT_DIR, self.remote_dir, dirs_exist_ok=True)


    def peel(self):
        self._peel()
        self.write_declared_global()
        self.copy_to_remote()
                      
        

PeelDeprecatedModule = PeelDeprecatedModule()

__all__ = ['PeelDeprecatedModule']