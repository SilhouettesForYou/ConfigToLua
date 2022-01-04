import getopt
import sys

from xml_to_lua import XmlToLua as xml
from csv_to_lua import CSVToLua as csv
from pkg_to_cpp import PkgToCpp as p2c


def usage():
    print('-x, --xml: convert .txt(.xml) to .lua')
    print('-c, --csv: convert .csv to .lua')
    print('-a, --all: convert all')
    print('-h: print help message.')


def main(argv):
    sys.setrecursionlimit(10000)
    args = argv[1:]
    try:
        opts, args = getopt.getopt(args, 'xcaf:kpis:', ['xml', 'csv', 'all', 'for=', 'key', 'pkg', 'index', 'string='])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for_server_or_client = 'client'
    is_key = False
    is_index = False
    is_string = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(1)
        if o in ('-f', '--for'):
            for_server_or_client = a
            csv.setConfig(for_server_or_client)
        elif o in ('-k', '--key'):
            is_key = True
        elif o in ('-i', '--index'):
            is_index = True
        elif o in ('-s', '--string'):
            is_string = True
            if a == 'only': csv.set_writ_flag(2)
            elif a == 'all': csv.set_writ_flag(1)
        elif o in ('-x', '--xml'):
            xml.xml_to_lua()
        elif o in ('-c', '--csv'):
            csv.setConfig(for_server_or_client, is_need_key=is_key, is_need_index=is_index, is_save_string=is_string)
            csv.csv_to_lua()
        elif o in ('-p', '--pkg'):
            p2c.pkg_to_cpp()
        elif o in ('-a', '--all'):
            xml.xml_to_lua()
            csv.setConfig(for_server_or_client, is_need_key=is_key, is_need_index=is_index, is_save_string=is_string)
            csv.csv_to_lua()
        else:
            sys.exit(3)


if __name__ == "__main__":
    main(sys.argv)