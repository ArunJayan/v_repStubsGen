from .command import Command
from .script_function import ScriptFunction
from .enum import Enum

class Plugin(object):
    def __init__(self, node):
        if node.tag != 'plugin':
            raise ValueError('expected <plugin>, got <%s>' % node.tag)
        self.name = node.attrib['name']
        self.commands = [Command(n) for n in node.findall('command')]
        self.script_functions = [ScriptFunction(n) for n in node.findall('script-function')]
        self.enums = [Enum(n) for n in node.findall('enum')]

