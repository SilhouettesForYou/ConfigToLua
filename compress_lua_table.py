import os
import sys
import codecs


###################################################################
##
##  config
##

REPEAT_KEY_PREFIX = "__rt"
DEFAULT_TABLE_NAME = "__default_table"
LOCAL_TABLE_MAX = 20000


###################################################################
##
##  tools
##
class CompressLuaTable:
    def convert_dict_lua_file(self, file_handler, lua_dict, deep):
        """Convert dict to lua file
            Output dict in file by lua table format.
            Special process value string '__rt'
            Args:
                file_handler: file handler
                lua_dict: dict
                deep: int
        """

        prefix_tab = "\t" * deep
        for key, value in sorted(lua_dict.items()):
            if isinstance(key, int):
                file_handler.write("%s[%s] = " % (prefix_tab, key))
            elif isinstance(key, str):
               file_handler.write("%s%s = " % (prefix_tab, key))
            else:
                print('ERROR!  Wrong key type!')
                raise SystemExit

            if isinstance(value, dict):
                file_handler.write("{\n")
                self.convert_dict_lua_file(file_handler, value, deep + 1)
                file_handler.write("%s},\n" % (prefix_tab))
            elif isinstance(value, str):
                if value.find("__rt") != -1:
                    file_handler.write("%s,\n" % (value))
                else:
                    file_handler.write("\'%s\',\n" % (value))
            elif isinstance(value, bool):
                file_handler.write("%s,\n" % (str(value).lower()))
            elif value is None:
                file_handler.write("nil,\n")
            else:
                file_handler.write("%s,\n" % (value))

    def count_dict_deep(self, dict_temp):
        deep = 0
        for item in dict_temp.values():
            if isinstance(item, dict):
                temp_deep = self.count_dict_deep(item)
                if temp_deep > deep:
                    deep = temp_deep

        return deep + 1

    def calc_weight(self, obj1):
        dict1 = eval(obj1[0])
        times1 = obj1[1]

        deep1 = self.count_dict_deep(dict1)
        ans = deep1 + 1/times1

        return ans

    def get_dict_str(self, dict):
        dict_str = '{'
        for key, value in sorted(dict.items()):
            if isinstance(key, str):
                dict_str = dict_str + '\'' + key + '\': '
            else:
                dict_str = dict_str + str(key) + ':'

            if isinstance(value, str):
                dict_str = dict_str + '\'' + value + '\', '
            else:
                dict_str = dict_str + str(value) + ','
        dict_str = dict_str + '}'

        return dict_str

    def get_final_frequency_item(self, dict_frequency):
        """Get final frequency item
            
            Different python version have different process for same frequency.
            At first, get most freqency items then sort keys to find out final most frequency item
            
            Args:
                dict_frequency: dict
            Returns:
                string: final most frequency item
        """

        most_frequency_items = {}
        most_frequency = -1
        for key, value in sorted(dict_frequency.items(), key=lambda item:item[1], reverse=True):
            if most_frequency == -1:
                most_frequency = value
                most_frequency_items[key] = value
            elif most_frequency == value:
                most_frequency_items[key] = value
        return sorted(most_frequency_items.items(), key=lambda item:str(item[0]))[0][0]

    def count_table_frequency(self, unit_dict, dict_frequency):
        """Count table frequency
            
            Count table frequency and record as {table string: times}
            Args:
                unit_dict: dict, need analyse data
                dict_frequency: dict, the record's set
        """

        unit_str = self.get_dict_str(unit_dict)
        if unit_str in dict_frequency:
            dict_frequency[unit_str] = dict_frequency[unit_str] + 1
        else:
            dict_frequency[unit_str] = 1

        # traversing sub dict
        for item in unit_dict.values():
            if isinstance(item, dict):
                self.count_table_frequency(item, dict_frequency)


    def count_table_value_frequency(self, key, value, item_frequency):
        """Count table value frequency
            Count every excel column element appear times.
            Record as {
                        key1 : {element1 : times, element2: times, ...}
                        key2 : {element1 : times, element2: times, ...}
                        ...
                        }
            Args:
                key: string
                value: string or dict
                item_frequency: dict, the record's set
        """

        if isinstance(value, dict):
            value = str(value)

        if key in item_frequency.keys():
            if value in item_frequency[key].keys():
                item_frequency[key][value] = item_frequency[key][value] + 1
            else:
                item_frequency[key][value] = 1
        else:
            item_frequency[key] = {}
            item_frequency[key][value] = 1


    def traverse_table(self, excel_dict, dict_frequency, item_frequency):
        """Traverse table.
            
            Analyse lua table.
            Args:
                excel_dict: dict
                dict_frequency: dict
                item_frequency: dict
        """

        for key in sorted(excel_dict):
            if isinstance(excel_dict[key], dict):
                self.count_table_frequency(excel_dict[key], dict_frequency)

                for k, v in sorted(excel_dict[key].items()):
                    self.count_table_value_frequency(k, v, item_frequency)


    def check_repeat_dict(self, item_dict, repeat_dict):
        """Check repeat dict
            
            Check repeat dict and return the repeat index, if not exist in repeat dict return -1.
            Args:
                item_dict: dict
                repeat_dict: dict
            Returns:
                int
        """

        for repeat_item in repeat_dict.keys():
            item = eval(repeat_item)
            if item == item_dict:
                return repeat_dict[repeat_item]    
        return -1


    def replace_repeat_dict(self, item_dict, repeat_dict, cur_index = -1):
        """Replace repeat dict
            Check if element exist in repeat dict and replace by designation string.
        
            Args:
                item_dict: dict
                repeat_dict: dict
        """

        cur_index = -1

        for key, value in item_dict.items():
            if isinstance(value, dict):
                index = self.check_repeat_dict(value, repeat_dict)
                if index != -1 and (index < cur_index or cur_index == -1):
                    if index > LOCAL_TABLE_MAX:
                        item_dict[key] = REPEAT_KEY_PREFIX + '[' + str(index - LOCAL_TABLE_MAX) + ']'
                    else:
                        item_dict[key] = REPEAT_KEY_PREFIX + str(index)
                else:
                    self.replace_repeat_dict(value, repeat_dict, cur_index)



    def output_file(self, table_name, file_path, repeat_dict, final_dict, default_dict):
        """Output file
            Args:
                table_name: string
                file_path: path
                repeat_dict: dict
                final_dict: dict
                default_dict: dict
        """

        file_handler = codecs.open(file_path, 'a', encoding='utf-8')

        # output repeat dict
        for dictStr, index in sorted(repeat_dict.items(), key=lambda item:item[1]):
            # replace repeat item by repeat_dict 
            repeat_dict_item = eval(dictStr)
            self.replace_repeat_dict(repeat_dict_item, repeat_dict, index)

            if index <= LOCAL_TABLE_MAX:
                # file_handler.write("local %s = {\n" % (REPEAT_KEY_PREFIX + str(index)))
                file_handler.write("local %s = {\n" % (REPEAT_KEY_PREFIX + str(index)))
                self.convert_dict_lua_file(file_handler, repeat_dict_item, 1)
                file_handler.write("}\n")
            else:
                if index == (LOCAL_TABLE_MAX + 1):
                    file_handler.write("\nlocal __rt = createtable and createtable(%d, 0) or {}\n" % (len(repeat_dict)-LOCAL_TABLE_MAX))
                
                file_handler.write("__rt[%d] = {\n" % (index - LOCAL_TABLE_MAX))
                self.convert_dict_lua_file(file_handler, repeat_dict_item, 1)
                file_handler.write("}\n")       

        # output final dict
        self.replace_repeat_dict(final_dict, repeat_dict)
        file_handler.write("\nlocal %s = {\n" % (table_name))
        self.convert_dict_lua_file(file_handler, final_dict, 1)
        file_handler.write("}\n")

        # output default dict
        self.replace_repeat_dict(default_dict, repeat_dict)
        file_handler.write("\nlocal %s = {\n" % (DEFAULT_TABLE_NAME))
        self.convert_dict_lua_file(file_handler, default_dict, 1)
        file_handler.write("}\n")

        # set metatable and read-only
        file_handler.write("\ndo\n")
        file_handler.write("\tlocal base = {__index = %s, __newindex = function() error(\"Attempt to modify read-only table\") end}\n" % (DEFAULT_TABLE_NAME))
        file_handler.write("\tfor k, v in pairs(%s) do\n" % (table_name))
        file_handler.write("\t\tsetmetatable(v, base)\n")
        file_handler.write("\tend\n")
        file_handler.write("\tbase.__metatable = false\n")
        file_handler.write("end\n")

        file_handler.write("\nreturn %s\n" % (table_name))
        file_handler.close()
        

    ###################################################################
    ##
    ##  structure method
    ##

    def structure_repeat_dict(self, dict_frequency):
        """Structure frequency dict
            Select frequency > 1 element to structure dict.
            Args:
                dict_frequency: dict
            Returns:
                dict; {dict's string : repeat index}
        """

        repeat_frequency_dict = {}
        for key, value in sorted(dict_frequency.items(), key=lambda x:self.calc_weight(x)):
            if value > 1:
                if value not in repeat_frequency_dict.keys():
                    repeat_frequency_dict[value] = []
                repeat_frequency_dict[value].append(key)

        repeat_dict = {}
        repeat_index = 1
        for frequency, keys in sorted(repeat_frequency_dict.items(), key=lambda item:item[0], reverse=True):
            for key in sorted(keys):
                repeat_dict[key] = repeat_index
                repeat_index = repeat_index + 1

        return repeat_dict


    def structure_default_dict(self, excel_dict, all_item_frequency):
        """Structure default dict
            
            Args:
                excel_dict: dict
                all_item_frequency: dict
            Returns:
                dict; {key : most frequently value}
        """

        excel_item = {}
        for key, item in sorted(excel_dict.items()):
            excel_item = item
            break

        default_dict = {}
        for key, value in sorted(excel_item.items()):
            item_frequency = self.get_final_frequency_item(all_item_frequency[key])
            if isinstance(value, dict) and item_frequency is not None and item_frequency.strip() != '':
                default_dict[key] = eval(item_frequency)
            else:
                default_dict[key] = item_frequency

        return default_dict


    def structure_final_dict(self, excel_dict, default_dict):
        """Structure final dict
            
            Structure final dict by default_dict and excel_dict.
            Args:
                excel_dict: dict
                default_dict: dict
            Returns:
                dict
        """

        final_dict = {}
        for key, value in sorted(excel_dict.items()):
            final_dict[key] = {}

            if isinstance(value, dict):
                for k, v in sorted(value.items()):
                    if default_dict[k] != v:
                        final_dict[key][k] = v
            else:
                final_dict[key] = value

        return final_dict


    def process_file(self, table, name, path):
        dict_frequency_statistics = {}
        all_item_frequency_statistics = {}

        # analyse dict
        self.traverse_table(table, dict_frequency_statistics, all_item_frequency_statistics)

        # get repeat dict
        repeat_dict = self.structure_repeat_dict(dict_frequency_statistics)

        # get default dict
        default_dict = self.structure_default_dict(table, all_item_frequency_statistics)

        # structure final dict
        final_dict = self.structure_final_dict(table, default_dict)

        self.output_file(name, path, repeat_dict, final_dict, default_dict)


CompressLuaTable = CompressLuaTable()

__all__ = ['CompressLuaTable']