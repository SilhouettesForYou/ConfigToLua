import getopt
import sys

from xml_to_lua import XmlToLua as xml
from csv_to_lua import CSVToLua as csv


def usage():
    print('-x, --xml: convert .txt(.xml) to .lua')
    print('-c, --csv: convert .csv to .lua')
    print('-a, --all: convert all')
    print('-h: print help message.')


def main(argv):
    sys.setrecursionlimit(10000)
    args = argv[1:]
    try:
        opts, args = getopt.getopt(args, 'xcaf:k', ['xml', 'csv', 'all', 'for=', 'key'])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)
    for_server_or_client = 'client'
    is_key = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(1)
        if o in ('-f', '--for'):
            for_server_or_client = a
            csv.setConfig(for_server_or_client, is_key)
        elif o in ('-k', '--key'):
            is_key = True
            csv.setConfig(for_server_or_client, is_key)
        elif o in ('-x', '--xml'):
            xml.xml_to_lua()
        elif o in ('-c', '--csv'):
            csv.csv_to_lua()
        elif o in ('-a', '--all'):
            xml.xml_to_lua()
            csv.setConfig(for_server_or_client, is_key)
            csv.csv_to_lua()
        else:
            sys.exit(3)


if __name__ == "__main__":
    main(sys.argv)