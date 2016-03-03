from utils import indent

class Function:
    def __init__(self, name, ret='void', args=[], body=''):
        self.name = name
        self.ret = ret
        self.args = args
        self.body = body

    def signature(self, include_defaults=True):
        getdef = lambda a: ' = %s' % a.default if include_defaults and a.default else ''
        arglist = ', '.join('{} {}{}'.format(a.ctype, a.name, getdef(a)) for a in self.args)
        return '{} {}({})'.format(self.ret, self.name, arglist)

    def declaration(self, include_defaults=True):
        return '{};\n'.format(self.signature(include_defaults))

    def definition(self, include_defaults=False):
        return '{}\n{{\n{}\n}}\n'.format(self.signature(include_defaults), indent(self.body))

