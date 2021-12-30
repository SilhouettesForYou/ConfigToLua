import os
import re

from colors import bcolors
from CppHeaderParser import CppHeader, CppParseError


class PkgToCpp:
    def __init__(self):
        self.tab = 4 * ' '
        self.double_tab = 8 * ' '
        self.annotation = '/*{}*/\n'

        self.cpp_file = 'lua_register.cpp'
        self.template_file_annotation = self.tab + '// {}\n'
        self.template_classes_annotation = self.tab + '// classes\n'
        self.template_variables_annotation = self.tab + '// variables\n'
        self.template_methods_annotation = self.tab + '// methods\n'
        self.template_enums_annotation = self.tab + '// enums\n'
        self.template_unregister_annotation = self.tab + '// unregister {}\n'

        self.template_namespace = self.tab + 'sol::table {} = l.create_named_table(\"{}\");\n'
        self.template_namespace_unused = self.tab + '// sol::table {} = l.create_named_table(\"{}\"); // place holder\n'
        self.template_classes = self.tab + 'auto {}_proxy = {}.new_usertype<{}::{}>(\"{}\");\n'
        self.template_methods_properties = self.tab + '{}_proxy[\"{}\"] = &{}::{}::{};\n'
        self.template_enum = self.tab + '{}.new_enum(\"{}\",\n{}\n' + self.tab + ');\n'
        self.template_enum_member = self.double_tab + '\"{}\", {}::{}::{}, \n'

        self.template_unregister_namespace = self.tab + 'sol::table {} = l[\"{}\"];\n'
        self.template_unregister_namespace_unused = self.tab + '// sol::table {} = l[\"{}\"]; // place holder\n'
        self.template_unregister_syntax = self.tab + 'sol::usertype<{}::{}> {}_proxy = {}[\"{}\"];\n' + 4 * ' ' + '{}_proxy.unregister();\n' 

        self.tempalte_include = '#include \"lua_register.h\"\n{}\n'
        self.tempalte_include_item = '#include {}\n'
        self.template_register = 'void LuaRegister::RegisterLuaFunctions(sol::state& l)\n{{\n{}\n}}\n'
        self.template_unregister = 'void LuaRegister::UnregisterLuaFunctions(sol::state& l)\n{{\n{}\n}}\n'

        self.unused_namespaces = {}
        self.unused_classes = {}
    

    def filter_include(self, lines):
        res = ''
        for line in lines:
            if line.strip().startswith('$'): res += line.replace('$', '')
            else: res += line
        return res


    def pascal_to_snake(self, camel: str):
        snake = re.sub(r'(?P<key>[A-Z]+)', r'_\g<key>',camel)
        return snake.lower().strip('_')

    
    def remove_annotation(self, annotation, template):
        if annotation == template: return ''
        return annotation

    def parse_cpp(self, name, header):
        includes = set(header.includes)
        namespaces = set()
        classes = {}

        # register
        output_file = self.template_file_annotation.format(name)
        output_classes = self.template_classes_annotation
        output_variables = self.template_variables_annotation
        output_methods = self.template_methods_annotation
        output_enums = self.template_enums_annotation

        ## variables & methods
        for class_name in header.classes.keys():
            # print(header.classes[class_name])
            namespace = header.classes[class_name]['namespace']
            if namespace == '' or namespace == 'std': continue
            namespaces.add(namespace)
            classes[class_name] = namespace
            
            if len(header.classes[class_name]['methods']['private']) == 0 and len(header.classes[class_name]['properties']['public']) == 0 and len(header.classes[class_name]['properties']['private']) == 0:
                self.unused_classes[class_name] = True

            for method in header.classes[class_name]['methods']['private']:
                output_methods += self.template_methods_properties.format(self.pascal_to_snake(class_name), method['name'], namespace, class_name, method['name'])

            for property in header.classes[class_name]['properties']['public']:
                output_variables += self.template_methods_properties.format(self.pascal_to_snake(class_name), property['name'], namespace, class_name, property['name'])

            for property in header.classes[class_name]['properties']['private']:
                output_variables += self.template_methods_properties.format(self.pascal_to_snake(class_name), property['name'], namespace, class_name, property['name'])

        ## namespace
        # for namespace in namespaces:
            # output_namespaces += self.template_namespace.format(self.pascal_to_snake(namespace), namespace)

        ## classes
        for class_, namespace in classes.items():
            syntax = self.template_classes.format(self.pascal_to_snake(class_), self.pascal_to_snake(namespace), namespace, class_, class_)
            if class_ in self.unused_classes: output_classes += self.tab + self.annotation.format(syntax[4:-1])
            else: output_classes += syntax

        ## enums
        for enum in header.enums:
            s = ''
            enum_str = self.template_enum_member
            namespace = enum['namespace'][:-2]
            if namespace == '': continue
            namespaces.add(namespace)
            if len(enum['values']) != 0:
                for variable in enum['values']:
                    s += enum_str.format(variable['name'], namespace, enum['name'], variable['name'])
                output_enums += self.template_enum.format(self.pascal_to_snake(namespace), enum['name'], s[:-3])
            else:
                self.unused_namespaces[namespace] = True

        # unregister
        output_unregister = self.template_unregister_annotation.format(name)
        ## classes
        for class_, namespace in classes.items():
            syntax = self.template_unregister_syntax.format(
                namespace,
                class_,
                self.pascal_to_snake(class_),
                self.pascal_to_snake(namespace),
                class_,
                self.pascal_to_snake(class_)
            )
            if class_ in self.unused_classes: output_unregister += self.tab + self.annotation.format(syntax[4:-1])
            else: output_unregister += syntax
        
        output_classes = self.remove_annotation(output_classes, self.template_classes_annotation)
        output_variables = self.remove_annotation(output_variables, self.template_variables_annotation)
        output_methods = self.remove_annotation(output_methods, self.template_methods_annotation)
        output_enums = self.remove_annotation(output_enums, self.template_enums_annotation)

        return output_file + output_classes + output_methods + output_variables + output_enums, output_unregister, includes, namespaces


    def generate_includes(self):
        res = ''
        for include in self.includes:
            res += self.tempalte_include_item.format(include)
        return self.tempalte_include.format(res)

    
    def generate_register_namespace(self):
        res = ''
        for namespace in self.namespaces:
            if namespace in self.unused_namespaces: res += self.template_namespace_unused.format(self.pascal_to_snake(namespace), namespace)
            else: res += self.template_namespace.format(self.pascal_to_snake(namespace), namespace)
        return res

    def generate_unregister_namespace(self):
        res = ''
        for namespace in self.namespaces:
            if namespace in self.unused_namespaces: res += self.template_unregister_namespace_unused.format(self.pascal_to_snake(namespace), namespace)
            else: res += self.template_unregister_namespace.format(self.pascal_to_snake(namespace), namespace)
        return res

    
    def pkg_to_cpp(self):
        with open('.config', 'r') as f:
            lines = f.readlines()
            dir_config = lines[2].strip()
            _dir = dir_config.split('#')[1]
            self.includes = set()
            self.namespaces = set()
            register = ''
            unregister = []
            for file in os.listdir(_dir):
                if file.endswith('.pkg'):
                    # if file != 'buff_def.pkg': continue
                    with open(os.path.join(_dir, file), 'r', encoding='utf-8') as pkg:
                        content = self.filter_include(pkg.readlines())
                        try:
                            cpp_header = CppHeader(content, argType='string', encoding='utf-8')
                            _register, _unregister, _includes, _namespaces = self.parse_cpp(file, cpp_header)
                            register += _register
                            unregister.append(_unregister)
                            self.includes = self.includes | _includes
                            self.namespaces = self.namespaces | _namespaces
                        except CppParseError as e:
                            # print(e)
                            print(f'{bcolors.FAIL}' + file + f'{bcolors.RESET}')

            with open(self.cpp_file, 'w') as w:
                w.write(self.generate_includes())
                w.write(self.template_register.format(self.generate_register_namespace() + register))
                w.write(self.template_unregister.format(self.generate_unregister_namespace() + ''.join(unregister[::-1])))

PkgToCpp = PkgToCpp()

__all__ = ['PkgToCpp']