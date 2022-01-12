import getopt
import sys

from xml_to_lua import XmlToLua as xml
from csv_to_lua import CSVToLua as csv
from pkg_to_cpp import PkgToCpp as p2c
from peel_deprecated_module import PeelDeprecatedModule as pdm

from rich.console import Console
from rich.markdown import Markdown


def usage():
    console = Console()
    with open('help.md', encoding='utf-8') as readme:
        markdown = Markdown(readme.read())
    console.print(markdown)


def main(argv):
    sys.setrecursionlimit(10000)
    args = argv[1:]
    try:
        opts, args = getopt.getopt(args, 'hxcaf:kpis:', ['help', 'xml', 'csv', 'all', 'for=', 'key', 'pkg', 'index', 'string=', 'peel', 'copy', 'require=', 'thread'])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
        
    args_for_csv = {}
    args_for_peel = {}
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(1)
        if o in ('-f', '--for'):
            args_for_csv['for'] = a
        elif o in ('-k', '--key'):
            args_for_csv['key'] = True
        elif o in ('-i', '--index'):
            args_for_csv['index'] = True
        elif o in ('-s', '--string'):
            args_for_csv['string'] = a
        elif o == '--require':
            args_for_csv[o[2:]] = a
        elif o == '--thread':
            args_for_csv[o[2:]] = True
        elif o in ('-x', '--xml'):
            xml.xml_to_lua()
        elif o in ('-c', '--csv'):
            csv.setConfig(**args_for_csv)
            csv.csv_to_lua()
        elif o in ('-p', '--pkg'):
            p2c.pkg_to_cpp()
        elif o == '--copy':
            args_for_peel[o] = True
        elif o == '--peel':
            pdm.set_config(**args_for_peel)
            pdm.peel()
        elif o in ('-a', '--all'):
            pass
        else:
            sys.exit(3)


if __name__ == "__main__":
    main(sys.argv)