from sys import argv, exit
import re
from parse import parse

if len(argv) != 4:
    print('usage: {} <reference.xml> <out-xml-file> <out-txt-file>'.format(argv[0]))
    exit(1)

plugin = parse(argv[1])

functions = []
variables = []

with open(argv[2], 'w') as fxml, open(argv[3], 'w') as ftxt:
    for cmd in plugin.commands:
        if plugin.short_name:
            func = 'sim{}.{}'.format(plugin.short_name, cmd.name)
        else:
            func = '{}{}'.format(plugin.command_prefix, cmd.name)
        fxml.write('<KeyWord name="{}" func="yes">\n'.format(func))
        fxml.write('<Overload retVal="{}">\n'.format(','.join(cmd.help_out_args_v)))
        for p in cmd.help_in_args_v:
            fxml.write('<Param name="{}" />\n'.format(p))
        fxml.write('</Overload>\n')
        fxml.write('</KeyWord>\n')
        fxml.write('\n')
        functions.append(func)

    for enum in plugin.enums:
        for item in enum.items:
            if plugin.short_name:
                prefix = 'sim{}.{}.'.format(plugin.short_name, enum.name)
            else:
                prefix = enum.item_prefix
            fxml.write('<KeyWord name="{}{}" func="no"/>\n'.format(prefix, item))
            variables.append(prefix+item)
        fxml.write('\n')

    ftxt.write('{}\n\n{}\n'.format(' '.join(functions), ' '.join(variables)))

